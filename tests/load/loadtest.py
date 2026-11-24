"""HTTP load test for the AgriSense API (asyncio + httpx, no extra dependencies).

    python tests/load/loadtest.py --base http://127.0.0.1:8159 --out load.json

Point it at a THROWAWAY instance (own database, OTP off): it registers a test user and saves
hundreds of predictions. Phases:
  1. baseline   - each endpoint alone, one request at a time (latency with no queueing)
  2. throughput - each endpoint alone, 8 concurrent clients, no pauses (requests per second it can serve)
  3. step       - mixed farmer traffic, users with a 1 s pause between requests, 10 -> 200 users in steps
  4. spike      - 5 users, a sudden jump to 150 users, then back to 5 (does it recover?)
The mixed workload follows how the app is used: page data and lookups most often, model calls less,
leaf photos least. The chat assistant is left out (it calls an outside paid API).
"""
import argparse
import asyncio
import json
import random
import time

import httpx

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:8159")
ap.add_argument("--out", default="load.json")
ap.add_argument("--steps", default="10,25,50,100,150,200")
ap.add_argument("--step-seconds", type=int, default=30)
ap.add_argument("--quick", action="store_true", help="short dry run to check the script")
A = ap.parse_args()
rng = random.Random(11)
H = {"X-Client": "android"}


def pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * q))] * 1000, 1)


def summary(rec, seconds):
    lat = [r[1] for r in rec if r[2]]
    errs = sum(1 for r in rec if not r[2])
    return {"requests": len(rec), "errors": errs, "error_rate": round(errs / len(rec), 4) if rec else 0,
            "rps": round(len(rec) / max(seconds, 1e-6), 2), "p50_ms": pct(lat, .5), "p95_ms": pct(lat, .95),
            "p99_ms": pct(lat, .99), "max_ms": pct(lat, 1.0)}


async def setup(c):
    r = await c.post("/api/auth/register", headers=H, json={"name": "Load Test", "email": f"load{int(time.time())}@agrisense.test",
                                                          "password": "Farm12345", "state": "Bihar", "district": "Patna"})
    r.raise_for_status()
    H["Authorization"] = f"Bearer {r.json()['token']}"
    crop = [(await c.get("/api/samples/crop", headers=H)).json()["values"] for _ in range(40)]
    yld = []
    for _ in range(25):
        s = (await c.get("/api/samples/yield", headers=H)).json()
        yld.append({k: s[k] for k in ("state", "district", "crop", "season", "year", "area_ha")})
    leaves = []
    for _ in range(6):
        s = (await c.get("/api/samples/leaf", headers=H)).json()
        leaves.append((await c.get(s["url"], headers=H)).content)
    return crop, yld, leaves


def make_requests(crop, yld, leaves):
    def crop_req(c):
        return c.post("/api/crop/recommend", headers=H, json=rng.choice(crop))

    def fert_req(c):
        v = rng.choice(crop)
        return c.post("/api/fertiliser", headers=H, json={"basis": "crop_profile", "crop": "rice", "N": v["N"], "P": v["P"], "K": v["K"]})

    def yield_req(c):
        return c.post("/api/yield/predict", headers=H, json=rng.choice(yld))

    def leaf_req(c):
        return c.post("/api/disease", headers=H, files={"image": ("leaf.jpg", rng.choice(leaves), "image/jpeg")})

    def me_req(c):
        return c.get("/api/me", headers=H)

    def overview_req(c):
        return c.get("/api/overview", headers=H)

    def history_req(c):
        return c.get("/api/predictions", headers=H)

    single = {"GET /api/me": me_req, "GET /api/overview": overview_req, "GET /api/predictions": history_req,
              "POST /api/crop/recommend": crop_req, "POST /api/fertiliser": fert_req,
              "POST /api/yield/predict": yield_req, "POST /api/disease": leaf_req}
    mix = [(me_req, 20), (overview_req, 15), (history_req, 10), (crop_req, 20), (fert_req, 20), (yield_req, 10), (leaf_req, 5)]
    return single, mix


async def call(c, fn, rec):
    t0 = time.perf_counter()
    try:
        r = await fn(c)
        ok = r.status_code < 400
    except Exception:
        ok = False
    rec.append((time.time(), time.perf_counter() - t0, ok))


async def run_users(c, pick, users, seconds, think, rec, stop_at=None):
    end = time.time() + seconds

    async def user():
        await asyncio.sleep(rng.random() * (think or 0.05))  # do not start all users in the same instant
        while time.time() < end:
            await call(c, pick(), rec)
            if think:
                await asyncio.sleep(think * (0.5 + rng.random()))
    await asyncio.gather(*(user() for _ in range(users)))


async def main():
    limits = httpx.Limits(max_connections=400, max_keepalive_connections=400)
    async with httpx.AsyncClient(base_url=A.base, timeout=60, limits=limits) as c:
        crop, yld, leaves = await setup(c)
        single, mix = make_requests(crop, yld, leaves)
        weights = [w for _, w in mix]
        pick_mix = lambda: rng.choices([f for f, _ in mix], weights)[0]
        out = {"base": A.base, "started": time.strftime("%Y-%m-%d %H:%M:%S"), "mix": {f.__name__: w for f, w in mix}}

        out["baseline"] = {}
        for name, fn in single.items():
            rec = []
            n = 3 if A.quick else 15 if "disease" in name else 40
            t0 = time.perf_counter()
            for _ in range(n):
                await call(c, fn, rec)
            out["baseline"][name] = summary(rec, time.perf_counter() - t0)
            print("baseline", name, out["baseline"][name], flush=True)

        out["throughput"] = {}
        for name, fn in single.items():
            rec = []
            tp = 3 if A.quick else 20
            await run_users(c, lambda fn=fn: (lambda c: fn(c)), 8, tp, 0, rec)
            out["throughput"][name] = summary(rec, tp)
            print("throughput", name, out["throughput"][name], flush=True)

        out["step"], out["step_timeline"] = [], []
        for users in [int(x) for x in A.steps.split(",")]:
            rec = []
            t0 = time.time()
            await run_users(c, pick_mix, users, A.step_seconds, 1.0, rec)
            s = {"users": users, "t_start": t0, "t_end": time.time(), **summary(rec, A.step_seconds)}
            out["step"].append(s)
            print("step", s, flush=True)
            if s["error_rate"] > 0.05 or (s["p95_ms"] or 0) > 10000:
                print("stopping: server saturated", flush=True)
                break
            await asyncio.sleep(5)

        rec = []
        t0 = time.time()
        a, b, d = (3, 5, 3) if A.quick else (15, 30, 25)
        await run_users(c, pick_mix, 5, a, 1.0, rec)
        await run_users(c, pick_mix, 150, b, 1.0, rec)
        await run_users(c, pick_mix, 5, d, 1.0, rec)
        out["spike"] = {"t0": t0, "phases": [["5 users", 0, a], ["150 users", a, a + b], ["5 users", a + b, a + b + d]],
                        "events": [(round(t - t0, 3), round(l * 1000, 1), ok) for t, l, ok in rec]}
        print("spike done", len(rec), flush=True)
        out["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(A.out, "w") as fh:
        json.dump(out, fh)


asyncio.run(main())

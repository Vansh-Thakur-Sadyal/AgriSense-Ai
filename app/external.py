"""External data: Open-Meteo (live forecast + geocoding), NASA POWER (historical gridded daily),
ISRIC SoilGrids v2 (modelled soil properties). Everything is cached and labelled with its source."""
import datetime as dt

import httpx

from . import db

UA = {"User-Agent": "AgriSense-AI/1.0 (university project)"}
WMO = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
       66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
       80: "Rain showers", 81: "Rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
       96: "Thunderstorm with hail", 99: "Thunderstorm with hail"}


def _get(url, params, timeout=20):
    with httpx.Client(timeout=timeout, headers=UA) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        return r.json()


def geocode(q):
    key = f"geo:{q.lower()}"
    if (hit := db.cache_get(key)) is not None:
        return hit
    j = _get("https://geocoding-api.open-meteo.com/v1/search",
             {"name": q, "count": 6, "language": "en", "countryCode": "IN"})
    out = [{"name": r["name"], "admin1": r.get("admin1"), "admin2": r.get("admin2"),
            "lat": r["latitude"], "lon": r["longitude"]} for r in j.get("results", [])]
    db.cache_put(key, out, 30 * 86400)
    return out


def forecast(lat, lon):
    key = f"fc:{lat:.3f},{lon:.3f}"
    if (hit := db.cache_get(key)) is not None:
        return hit
    j = _get("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 7,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "precipitation_probability_max,sunrise,sunset,shortwave_radiation_sum"})
    cur = j["current"]
    d = j["daily"]
    days = [{"date": d["time"][i], "code": d["weather_code"][i], "condition": WMO.get(d["weather_code"][i], "-"),
             "tmax": d["temperature_2m_max"][i], "tmin": d["temperature_2m_min"][i],
             "rain_mm": d["precipitation_sum"][i], "rain_prob": d["precipitation_probability_max"][i],
             "radiation_mj": d["shortwave_radiation_sum"][i]} for i in range(len(d["time"]))]
    out = {"source": "Open-Meteo forecast (live)", "fetched": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z",
           "current": {"temp": cur["temperature_2m"], "humidity": cur["relative_humidity_2m"],
                       "rain_mm": cur["precipitation"], "code": cur["weather_code"],
                       "condition": WMO.get(cur["weather_code"], "-"), "wind_kmh": cur["wind_speed_10m"],
                       "wind_dir": cur["wind_direction_10m"], "time": cur["time"]},
           "sunrise": d["sunrise"][0][-5:], "sunset": d["sunset"][0][-5:], "days": days,
           "timezone": j.get("timezone")}
    db.cache_put(key, out, 1800)
    return out


def alerts(fc):
    """Plain threshold alerts derived from the live forecast. Thresholds are stated in the text."""
    out = []
    for d in fc["days"][:3]:
        if (d["rain_mm"] or 0) >= 20:
            out.append({"level": "warning", "date": d["date"],
                        "text": f"Heavy rain forecast ({d['rain_mm']} mm, >= 20 mm): hold irrigation and fertiliser top-dressing."})
        if (d["tmax"] or 0) >= 40:
            out.append({"level": "warning", "date": d["date"],
                        "text": f"Heat: max {d['tmax']} degC (>= 40): irrigate in the evening, watch for wilting."})
        if (d["tmin"] if d["tmin"] is not None else 99) <= 4:
            out.append({"level": "warning", "date": d["date"],
                        "text": f"Frost risk: min {d['tmin']} degC (<= 4): light irrigation and cover nurseries."})
    return out


POWER_PARAMS = {"T2M": "temp_mean", "T2M_MAX": "temp_max", "T2M_MIN": "temp_min", "RH2M": "humidity",
                "PRECTOTCORR": "rain_mm", "ALLSKY_SFC_SW_DWN": "radiation_mj"}


def nasa_power(lat, lon, start: dt.date, end: dt.date):
    key = f"power:{lat:.2f},{lon:.2f}:{start}:{end}"
    if (hit := db.cache_get(key)) is not None:
        return hit
    j = _get("https://power.larc.nasa.gov/api/temporal/daily/point", {
        "parameters": ",".join(POWER_PARAMS), "community": "AG", "latitude": lat, "longitude": lon,
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON"}, timeout=60)
    p = j["properties"]["parameter"]
    dates = sorted(p["T2M"].keys())
    rows = []
    for d in dates:
        r = {"date": f"{d[:4]}-{d[4:6]}-{d[6:]}"}
        for src, name in POWER_PARAMS.items():
            v = p[src].get(d)
            r[name] = None if v is None or v <= -998 else v
        rows.append(r)
    out = {"source": "NASA POWER daily gridded estimates (MERRA-2 / CERES), ~0.5 deg grid - historical, not live",
           "attribution": "Data obtained from the NASA Langley Research Center (LaRC) POWER Project funded "
                          "through the NASA Earth Science/Applied Science Program.",
           "rows": rows}
    db.cache_put(key, out, 7 * 86400)
    return out


SOIL_PROPS = ["phh2o", "nitrogen", "soc", "clay", "sand", "silt", "bdod", "cec", "wv0033", "wv1500"]
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]
SOIL_LABEL = {"phh2o": ("Soil pH (H2O)", ""), "nitrogen": ("Total nitrogen", "g/kg"),
              "soc": ("Soil organic carbon", "g/kg"), "clay": ("Clay", "%"), "sand": ("Sand", "%"),
              "silt": ("Silt", "%"), "bdod": ("Bulk density", "g/cm3"), "cec": ("CEC", "cmol(c)/kg"),
              "wv0033": ("Water at field capacity (33 kPa)", "vol %"),
              "wv1500": ("Water at wilting point (1500 kPa)", "vol %")}
# SoilGrids mapped units -> conventional units
SOIL_DIV = {"phh2o": 10, "nitrogen": 100, "soc": 10, "clay": 10, "sand": 10, "silt": 10, "bdod": 100,
            "cec": 10, "wv0033": 10, "wv1500": 10}


def _wcs_point(client, prop, depth, stat, lat, lon):
    """One SoilGrids value from the ISRIC WCS (mapped integer units). A ~2 km window is read and the
    median of valid cells taken, because the reprojected tiles have empty edge cells."""
    import io as _io

    import numpy as np
    from PIL import Image
    d = 0.01
    url = (f"https://maps.isric.org/mapserv?map=/map/{prop}.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
           f"&COVERAGEID={prop}_{depth}_{stat}&FORMAT=image/tiff&SUBSET=long({lon - d},{lon + d})"
           f"&SUBSET=lat({lat - d},{lat + d})&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326"
           f"&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326")
    for attempt in range(3):
        try:
            r = client.get(url)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/tiff"):
                a = np.array(Image.open(_io.BytesIO(r.content))).astype(float).ravel()
                a = a[(a > 0) & (a < 32000)]
                return float(np.median(a)) if a.size else None
        except Exception:
            pass
    return None


def _soilgrids_wcs(lat, lon):
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(p, d, s) for p in SOIL_PROPS for d in DEPTHS for s in ("mean", "Q0.05", "Q0.95")]
    with httpx.Client(timeout=30, headers=UA) as c, ThreadPoolExecutor(10) as ex:
        vals = dict(zip(jobs, ex.map(lambda j: _wcs_point(c, j[0], j[1], j[2], lat, lon), jobs)))
    layers = [{"name": p, "unit_measure": {"d_factor": SOIL_DIV[p]},
               "depths": [{"label": d, "values": {"mean": vals[(p, d, "mean")], "Q0.05": vals[(p, d, "Q0.05")],
                                                   "Q0.95": vals[(p, d, "Q0.95")]}} for d in DEPTHS]}
              for p in SOIL_PROPS]
    return {"properties": {"layers": layers}}


def soilgrids(lat, lon):
    key = f"soil:{lat:.3f},{lon:.3f}"
    if (hit := db.cache_get(key)) is not None:
        return hit
    # The SoilGrids REST endpoint is frequently 503, slow (40 s+) or returns nulls; the ISRIC WCS
    # serves the same 250 m maps quickly, so it is the only path used.
    j = _soilgrids_wcs(lat, lon)
    via = "ISRIC WCS"
    props = {}
    any_value = False
    for layer in j["properties"]["layers"]:
        name = layer["name"]
        div = SOIL_DIV.get(name, layer["unit_measure"].get("d_factor", 1))
        label, unit = SOIL_LABEL.get(name, (name, layer["unit_measure"].get("target_units", "")))
        depths = []
        for d in layer["depths"]:
            v = d["values"]
            conv = lambda x: None if x is None else round(x / div, 2)
            if v.get("mean") is not None:
                any_value = True
            depths.append({"depth": d["label"], "mean": conv(v.get("mean")), "q05": conv(v.get("Q0.05")),
                           "q95": conv(v.get("Q0.95")),
                           "uncertainty": None if v.get("uncertainty") is None else round(v["uncertainty"] / 10, 2)})
        props[name] = {"label": label, "unit": unit, "depths": depths}
    out = {"source": f"ISRIC SoilGrids 2.0, 250 m modelled estimates (via {via})",
           "warning": "Modelled spatial estimates, not a laboratory soil test.",
           "has_data": any_value, "lat": lat, "lon": lon, "properties": props}
    db.cache_put(key, out, 30 * 86400)
    return out

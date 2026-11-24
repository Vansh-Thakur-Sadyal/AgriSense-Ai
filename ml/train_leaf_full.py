"""Leaf disease model on ALL supplied leaf data (non-augmented + augmented sets), CUDA.

The augmented set (61,486 files) = the 55,448 originals + 6,038 synthetic copies that topped the
small classes up to 1,000. File names do not say which photo a copy came from, so:

  1. Byte-hash every augmented file; files identical to an original are originals.
  2. The rest are synthetic. Each is linked to its SOURCE photo by nearest neighbour (cosine) on
     the current model's penultimate features, within its class.
  3. EVALUATION run: the usual stratified 70/15/15 split of the originals. Synthetic copies join
     training only when their source photo is in training, so no copy of a val/test photo leaks.
     Temperature + threshold fitted on val, test touched once.
  4. FINAL run: same recipe and epoch count on everything (61,486 images). This is the deployed
     model; its quality figures are the evaluation run's (there is no data left to test it on),
     and it reuses that run's temperature and threshold. The card says so.

Writes into ml/staging/ (copied to app/models only after review).
Run:  .venv/Scripts/python ml/train_leaf_full.py --epochs 8
"""
import argparse
import hashlib
import json
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, f1_score, recall_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader
from torchvision import models, transforms

from train_leaf import Leaves, ece, evaluate, fit_temperature, SIZE, MEAN, STD

ROOT = Path(__file__).resolve().parents[1]
ORIG = ROOT / "data" / "raw" / "leaf" / "Plant_leave_diseases_dataset_without_augmentation"
AUG = ROOT / "data" / "raw" / "leaf" / "Plant_leave_diseases_dataset_with_augmentation"
PREV = ROOT / "app" / "models" / "leaf_best.pt"
OUT = ROOT / "ml" / "staging"
EXT = {".jpg", ".jpeg", ".png"}


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def build_model(n, dev):
    m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, n)
    return m.to(dev).to(memory_format=torch.channels_last)


def features(model, paths, tf, dev, kw):
    """Penultimate (pooled) features, L2-normalised."""
    dl = DataLoader(Leaves([(p, 0) for p in paths], tf), **kw)
    out = []
    model.eval()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        for x, _ in dl:
            f = model.avgpool(model.features(x.to(dev))).flatten(1).float()
            out.append(nn.functional.normalize(f, dim=1).cpu())
    return torch.cat(out)


def train(model, items, tf, epochs, dev, kw, dl_va=None, ckpt=None, tag=""):
    dl = DataLoader(Leaves(items, tf), shuffle=True, drop_last=True, **kw)
    n = model.classifier[1].out_features
    counts = np.bincount([y for _, y in items], minlength=n)
    w = torch.tensor((counts.sum() / (n * counts)) ** 0.5, dtype=torch.float32, device=dev)
    crit = nn.CrossEntropyLoss(weight=w, label_smoothing=0.05)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-3, total_steps=epochs * len(dl), pct_start=0.15)
    scaler = torch.amp.GradScaler()
    best, hist = -1.0, []
    for ep in range(epochs):
        model.train()
        t0, run = time.time(), 0.0
        for x, y in dl:
            x = x.to(dev, non_blocking=True).to(memory_format=torch.channels_last)
            y = y.to(dev, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16):
                loss = crit(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(opt); scaler.update(); sched.step()
            run += loss.item()
        h = {"run": tag, "epoch": ep + 1, "train_loss": round(run / len(dl), 4),
             "seconds": round(time.time() - t0, 1), "gpu": torch.cuda.get_device_name(0)}
        if dl_va is not None:
            lg, ys = evaluate(model, dl_va, dev)
            pred = lg.argmax(1)
            h["val_acc"] = round(float((pred == ys).float().mean()), 4)
            h["val_macro_recall"] = round(float(recall_score(ys, pred, average="macro")), 4)
            if h["val_macro_recall"] > best:
                best = h["val_macro_recall"]
                torch.save(model.state_dict(), ckpt)
        hist.append(h)
        print(h, flush=True)
    if ckpt is not None and dl_va is None:
        torch.save(model.state_dict(), ckpt)
    return hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=96)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--min-precision", type=float, default=0.999)
    ap.add_argument("--floor", type=float, default=0.60)
    a = ap.parse_args()
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    dev = "cuda"
    OUT.mkdir(parents=True, exist_ok=True)
    kw = dict(batch_size=a.batch, num_workers=a.workers, pin_memory=True, persistent_workers=True)
    eval_tf = transforms.Compose([transforms.Resize((SIZE, SIZE)), transforms.ToTensor(),
                                  transforms.Normalize(MEAN, STD)])
    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(SIZE, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(), transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20), transforms.ColorJitter(0.3, 0.3, 0.3, 0.03),
        transforms.ToTensor(), transforms.Normalize(MEAN, STD)])

    classes = sorted(d.name for d in ORIG.iterdir() if d.is_dir())
    assert classes == sorted(d.name for d in AUG.iterdir() if d.is_dir()), "class folders differ"
    cid = {c: i for i, c in enumerate(classes)}
    orig = [(str(p), cid[c]) for c in classes for p in sorted((ORIG / c).iterdir()) if p.suffix.lower() in EXT]
    aug = [(str(p), cid[c]) for c in classes for p in sorted((AUG / c).iterdir()) if p.suffix.lower() in EXT]

    # 1. originals vs synthetic, by content hash
    t0 = time.time()
    orig_hash = {md5(p): p for p, _ in orig}
    synthetic = [(p, y) for p, y in aug if md5(p) not in orig_hash]
    dup_aug = len(aug) - len(synthetic)
    print(f"originals {len(orig)} | augmented files {len(aug)} = {dup_aug} identical to an original "
          f"+ {len(synthetic)} synthetic ({time.time() - t0:.0f}s)", flush=True)

    # 2. link each synthetic image to its source photo (same class, nearest neighbour)
    prev = build_model(len(classes), dev)
    prev.load_state_dict(torch.load(PREV))
    syn_classes = sorted({y for _, y in synthetic})
    source, sims = {}, []
    for y in syn_classes:
        cands = [p for p, yy in orig if yy == y]
        syn = [p for p, yy in synthetic if yy == y]
        fc = features(prev, cands, eval_tf, dev, kw)
        fs = features(prev, syn, eval_tf, dev, kw)
        s, j = (fs @ fc.T).max(1)
        for p, jj, ss in zip(syn, j.tolist(), s.tolist()):
            source[p] = cands[jj]
            sims.append(ss)
    sims = np.array(sims)
    linking = {"classes_topped_up": [classes[y] for y in syn_classes],
               "synthetic_per_class": {classes[y]: n for y, n in sorted(Counter(y for _, y in synthetic).items())},
               "cosine_similarity_to_source": {q: round(float(np.quantile(sims, v)), 4) for q, v in
                                               [("min", 0), ("p05", 0.05), ("median", 0.5), ("max", 1)]}}
    print("linking", linking["cosine_similarity_to_source"], flush=True)
    del prev
    torch.cuda.empty_cache()

    # 3. evaluation run
    labels = [y for _, y in orig]
    tr, rest = train_test_split(orig, test_size=0.30, stratify=labels, random_state=42)
    va, te = train_test_split(rest, test_size=0.50, stratify=[y for _, y in rest], random_state=42)
    tr_set = {p for p, _ in tr}
    syn_tr = [(p, y) for p, y in synthetic if source[p] in tr_set]
    syn_held = len(synthetic) - len(syn_tr)
    print(f"eval split: train {len(tr)} originals + {len(syn_tr)} synthetic "
          f"({syn_held} synthetic dropped: source photo is in val/test) | val {len(va)} test {len(te)}", flush=True)
    dl_va = DataLoader(Leaves(va, eval_tf), **kw)
    dl_te = DataLoader(Leaves(te, eval_tf), **kw)
    model = build_model(len(classes), dev)
    hist_eval = train(model, tr + syn_tr, train_tf, a.epochs, dev, kw, dl_va, OUT / "leaf_eval.pt", "evaluation")
    model.load_state_dict(torch.load(OUT / "leaf_eval.pt"))
    lg_va, ys_va = evaluate(model, dl_va, dev)
    T = fit_temperature(lg_va, ys_va)
    conf_v, pred_v = torch.softmax(lg_va / T, 1).max(1)
    threshold = 0.99
    for th in np.arange(0.30, 0.995, 0.01):
        m = conf_v >= th
        if m.sum() > 0 and float((pred_v[m] == ys_va[m]).float().mean()) >= a.min_precision:
            threshold = round(float(th), 2)
            break
    threshold = max(threshold, a.floor)
    lg_te, ys_te = evaluate(model, dl_te, dev)
    pt = torch.softmax(lg_te / T, 1)
    conf_t, pred_t = pt.max(1)
    answered = conf_t >= threshold
    test = {
        "accuracy": round(float((pred_t == ys_te).float().mean()), 4),
        "macro_recall": round(float(recall_score(ys_te, pred_t, average="macro")), 4),
        "macro_f1": round(float(f1_score(ys_te, pred_t, average="macro")), 4),
        "ece_before_T": round(ece(torch.softmax(lg_te, 1), ys_te), 4),
        "ece_after_T": round(ece(pt, ys_te), 4),
        "answered_fraction": round(float(answered.float().mean()), 4),
        "accuracy_when_answered": round(float((pred_t[answered] == ys_te[answered]).float().mean()), 4),
    }
    per_class = recall_score(ys_te, pred_t, average=None)
    cm = confusion_matrix(ys_te, pred_t).tolist()
    print("TEST", test, flush=True)
    del model
    torch.cuda.empty_cache()

    # 4. final run on everything
    everything = orig + synthetic
    print(f"final fit on all {len(everything)} images", flush=True)
    model = build_model(len(classes), dev)
    hist_final = train(model, everything, train_tf, a.epochs, dev, kw, None, OUT / "leaf_best.pt", "final (all data)")

    model.eval().float().cpu()
    torch.onnx.export(model, torch.randn(1, 3, SIZE, SIZE), str(OUT / "leaf_disease.onnx"),
                      input_names=["image"], output_names=["logits"],
                      dynamic_axes={"image": {0: "n"}, "logits": {0: "n"}}, external_data=False)
    card = {
        "name": "Plant leaf disease detection",
        "architecture": "EfficientNet-B0 (torchvision, ImageNet-1k init), fine-tuned on CUDA "
                        f"({torch.cuda.get_device_name(0)}, mixed precision)",
        "dataset": "Data for Identification of Plant Leaf Diseases Using a 9-layer Deep CNN (Mendeley; "
                   "PlantVillage-derived): non-augmented set (55,448) + augmented set (61,486 files, of which "
                   f"{len(synthetic)} are synthetic copies)",
        "classes": classes,
        "deployed_fit": {"images": len(everything), "originals": len(orig), "synthetic": len(synthetic),
                         "epochs": a.epochs, "note": "refit on ALL data after evaluation; no data was left "
                         "to test this exact model, so quality figures are from the evaluation run"},
        "augmented_set": {"files": len(aug), "identical_to_an_original": dup_aug, "synthetic": len(synthetic),
                          **linking},
        "split": {"train": len(tr), "train_synthetic": len(syn_tr), "synthetic_dropped_leak_guard": syn_held,
                  "val": len(va), "test": len(te), "seed": 42, "stratified": True},
        "input": {"size": SIZE, "mean": MEAN, "std": STD, "resize": "bilinear to 224x224"},
        "temperature": round(T, 4),
        "threshold": threshold,
        "threshold_rule": f"lowest confidence with validation accuracy-when-answered >= {a.min_precision}, "
                          f"floored at {a.floor} because lab-image validation cannot measure field-photo risk; "
                          "fitted on the evaluation run and carried to the final fit",
        "history": hist_eval + hist_final,
        "test": test,
        "per_class_recall": {c: round(float(r), 4) for c, r in zip(classes, per_class)},
        "confusion_matrix": cm,
        "limitations": "PlantVillage images are single leaves on plain lab backgrounds. Field photos with "
                       "soil, several leaves or other crops are out of distribution and accuracy there "
                       "is NOT measured by this test split.",
        "trained_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    (OUT / "leaf_disease.json").write_text(json.dumps(card, indent=1))
    print("done", flush=True)


if __name__ == "__main__":
    main()

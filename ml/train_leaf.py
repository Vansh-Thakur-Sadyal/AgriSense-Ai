"""Plant leaf disease classifier (EfficientNet-B0, ImageNet init) on the PlantVillage-derived
"9-layer deep CNN" dataset, non-augmented version: 55,448 images, 39 classes including
Background_without_leaves.

Stratified 70/15/15 split (seed 42). Model selected on validation macro recall. Temperature
scaling and the confidence threshold are fitted on validation; the test split is touched once.
Exports a self-contained ONNX file plus a model card that the app reads.

Run:  .venv/Scripts/python ml/train_leaf.py --epochs 8
"""
import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import confusion_matrix, f1_score, recall_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "leaf" / "Plant_leave_diseases_dataset_without_augmentation"
OUT = ROOT / "app" / "models"
SIZE = 224
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


class Leaves(Dataset):
    def __init__(self, items, tf):
        self.items, self.tf = items, tf

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        p, y = self.items[i]
        return self.tf(Image.open(p).convert("RGB")), y


def evaluate(model, loader, dev):
    model.eval()
    logits, ys = [], []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        for x, y in loader:
            logits.append(model(x.to(dev, non_blocking=True)).float().cpu())
            ys.append(y)
    return torch.cat(logits), torch.cat(ys)


def fit_temperature(logits, ys):
    t = torch.ones(1, requires_grad=True)
    opt = torch.optim.LBFGS([t], lr=0.05, max_iter=200)
    nll = nn.CrossEntropyLoss()

    def closure():
        opt.zero_grad()
        loss = nll(logits / t.clamp(min=0.05), ys)
        loss.backward()
        return loss
    opt.step(closure)
    return float(t.clamp(min=0.05).item())


def ece(probs, ys, bins=15):
    conf, pred = probs.max(1)
    acc = (pred == ys).float()
    edges = torch.linspace(0, 1, bins + 1)
    e = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            e += m.float().mean().item() * abs(acc[m].mean().item() - conf[m].mean().item())
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=96)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--min-precision", type=float, default=0.98)
    ap.add_argument("--floor", type=float, default=0.60,
                    help="minimum threshold: lab-image validation cannot measure field-photo risk")
    ap.add_argument("--skip-train", action="store_true",
                    help="reuse app/models/leaf_best.pt; epoch history read from ml/leaf_history.txt")
    a = ap.parse_args()
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    dev = "cuda"
    OUT.mkdir(parents=True, exist_ok=True)

    classes = sorted(d.name for d in DATA.iterdir() if d.is_dir())
    items = [(str(p), i) for i, c in enumerate(classes) for p in sorted((DATA / c).iterdir())
             if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    labels = [y for _, y in items]
    tr, rest = train_test_split(items, test_size=0.30, stratify=labels, random_state=42)
    va, te = train_test_split(rest, test_size=0.50, stratify=[y for _, y in rest], random_state=42)
    print(f"{len(classes)} classes | train {len(tr)} val {len(va)} test {len(te)}")

    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(SIZE, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(), transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(0.3, 0.3, 0.3, 0.03),
        transforms.ToTensor(), transforms.Normalize(MEAN, STD)])
    # Serving does exactly this with PIL + numpy: resize to 224x224 bilinear, scale, normalise.
    eval_tf = transforms.Compose([transforms.Resize((SIZE, SIZE)), transforms.ToTensor(),
                                  transforms.Normalize(MEAN, STD)])
    kw = dict(batch_size=a.batch, num_workers=a.workers, pin_memory=True, persistent_workers=True)
    dl_tr = DataLoader(Leaves(tr, train_tf), shuffle=True, drop_last=True, **kw)
    dl_va = DataLoader(Leaves(va, eval_tf), **kw)
    dl_te = DataLoader(Leaves(te, eval_tf), **kw)

    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
    model.to(dev).to(memory_format=torch.channels_last)

    # Class-weighted loss: the largest class is 36x the smallest (Orange HLB 5,507 vs Potato healthy 152).
    counts = np.bincount([y for _, y in tr], minlength=len(classes))
    w = torch.tensor((counts.sum() / (len(classes) * counts)) ** 0.5, dtype=torch.float32, device=dev)
    crit = nn.CrossEntropyLoss(weight=w, label_smoothing=0.05)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=1e-3, total_steps=max(1, a.epochs) * len(dl_tr),
                                                pct_start=0.15)
    scaler = torch.amp.GradScaler()
    best, history = -1.0, []
    if a.skip_train:
        import ast
        history = [ast.literal_eval(l) for l in (ROOT / "ml" / "leaf_history.txt").read_text().splitlines() if l.strip()]
    for ep in range(0 if a.skip_train else a.epochs):
        model.train()
        t0, run = time.time(), 0.0
        for x, y in dl_tr:
            x = x.to(dev, non_blocking=True).to(memory_format=torch.channels_last)
            y = y.to(dev, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16):
                loss = crit(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(opt); scaler.update(); sched.step()
            run += loss.item()
        lg, ys = evaluate(model, dl_va, dev)
        pred = lg.argmax(1)
        acc = float((pred == ys).float().mean())
        mrec = float(recall_score(ys, pred, average="macro"))
        history.append({"epoch": ep + 1, "train_loss": round(run / len(dl_tr), 4), "val_acc": round(acc, 4),
                        "val_macro_recall": round(mrec, 4), "seconds": round(time.time() - t0, 1)})
        print(history[-1], flush=True)
        if mrec > best:
            best = mrec
            torch.save(model.state_dict(), OUT / "leaf_best.pt")

    model.load_state_dict(torch.load(OUT / "leaf_best.pt"))
    lg_va, ys_va = evaluate(model, dl_va, dev)
    T = fit_temperature(lg_va, ys_va)
    pv = torch.softmax(lg_va / T, 1)
    conf_v, pred_v = pv.max(1)
    # Lowest threshold whose accuracy-when-answered clears min-precision on VALIDATION.
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
    per_class = recall_score(ys_te, pred_t, average=None)
    test = {
        "accuracy": round(float((pred_t == ys_te).float().mean()), 4),
        "macro_recall": round(float(recall_score(ys_te, pred_t, average="macro")), 4),
        "macro_f1": round(float(f1_score(ys_te, pred_t, average="macro")), 4),
        "ece_before_T": round(ece(torch.softmax(lg_te, 1), ys_te), 4),
        "ece_after_T": round(ece(pt, ys_te), 4),
        "answered_fraction": round(float(answered.float().mean()), 4),
        "accuracy_when_answered": round(float((pred_t[answered] == ys_te[answered]).float().mean()), 4),
    }
    print(test)

    model.eval().float().cpu()
    dummy = torch.randn(1, 3, SIZE, SIZE)
    torch.onnx.export(model, dummy, str(OUT / "leaf_disease.onnx"), input_names=["image"],
                      output_names=["logits"], dynamic_axes={"image": {0: "n"}, "logits": {0: "n"}},
                      external_data=False)
    card = {
        "name": "Plant leaf disease detection",
        "architecture": "EfficientNet-B0 (torchvision, ImageNet-1k init), fine-tuned",
        "dataset": "Data for Identification of Plant Leaf Diseases Using a 9-layer Deep CNN "
                   "(Mendeley; PlantVillage-derived), non-augmented, 55,448 images",
        "classes": classes,
        "split": {"train": len(tr), "val": len(va), "test": len(te), "seed": 42, "stratified": True},
        "input": {"size": SIZE, "mean": MEAN, "std": STD, "resize": "bilinear to 224x224"},
        "temperature": round(T, 4),
        "threshold": threshold,
        "threshold_rule": f"lowest confidence with validation accuracy-when-answered >= {a.min_precision}, "
                          f"floored at {a.floor} because lab-image validation cannot measure field-photo risk",
        "history": history,
        "test": test,
        "per_class_recall": {c: round(float(r), 4) for c, r in zip(classes, per_class)},
        "confusion_matrix": confusion_matrix(ys_te, pred_t).tolist(),
        "limitations": "PlantVillage images are single leaves on plain lab backgrounds. Field photos with "
                       "soil, several leaves or other crops are out of distribution and accuracy there "
                       "is NOT measured by this test split.",
        "trained_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    (OUT / "leaf_disease.json").write_text(json.dumps(card, indent=1))
    print("done")


if __name__ == "__main__":
    main()

"""Two diagrams for the AI/ML report: the decision chain and the ML pipeline (matplotlib, PNG)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "submission"))
import diagrams as D  # noqa: E402

OUT = HERE / "out" / "figs"
OUT.mkdir(parents=True, exist_ok=True)
NL = chr(10)


def save(f, name):
    f.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    D.plt.close(f)


def chain():
    f, ax = D._canvas(9.6, 3.2, 100, 33)
    y, h, w = 20, 8.5, 17
    steps = [("Soil sample", f"N, P, K, temperature,{NL}humidity, pH, rainfall"),
             ("Crop model", f"Random Forest,{NL}22 crops"),
             ("Shortfall", f"compare N, P, K with{NL}the crop's typical level"),
             ("Fertiliser model", f"Logistic Regression{NL}on the need vector"),
             ("Result", f"fertiliser name, grade,{NL}confidence, reasons")]
    xs = [1, 21, 41, 61, 81]
    for (t, s), x in zip(steps, xs):
        D.box(ax, x, y, w, h, t, s, fc=D.MINT if t in ("Crop model", "Fertiliser model") else "white", fs=8.2)
    for a, b in zip(xs, xs[1:]):
        D.arrow(ax, a + w + 0.4, y + h / 2, b - 0.4, y + h / 2)
    D.box(ax, 41, 3, w, 8, "Rule check", f"nothing short ->{NL}no fertiliser needed", ec=D.ORANGE, fs=8.2)
    D.arrow(ax, 49.5, y - 0.3, 49.5, 11.4)
    D.box(ax, 61, 3, w, 8, "Supply filter", f"choice must supply{NL}every short nutrient", ec=D.ORANGE, fs=8.2)
    D.arrow(ax, 69.5, y - 0.3, 69.5, 11.4)
    D.box(ax, 81, 3, w, 8, "Assistant", f"Mistral LLM explains{NL}on request, no doses", ec=D.BLUE, fs=8.2)
    D.arrow(ax, 89.5, y - 0.3, 89.5, 11.4, ls="--")
    D.box(ax, 1, 3, 37, 8, "Leaf photo -> EfficientNet-B0", f"39 classes, calibrated confidence;{NL}below 0.95 the photo is sent for review",
          ec=D.GREEN, fs=8.2)
    save(f, "ai_chain.png")


def pipeline():
    f, ax = D._canvas(9.6, 2.2, 100, 22)
    steps = [("Raw data", f"CSV files,{NL}leaf images"), ("Clean", f"units, outliers,{NL}duplicates"),
             ("Split", f"stratified / temporal,{NL}leak guard"), ("Train and compare", f"several models,{NL}cross-validation"),
             ("Evaluate", f"held-out test,{NL}baselines"), ("Refit and serve", f"all data, model card,{NL}FastAPI + ONNX")]
    w, x0, gap = 14.2, 1, 2.5
    for i, (t, s) in enumerate(steps):
        x = x0 + i * (w + gap)
        D.box(ax, x, 7, w, 9, t, s, fc=D.MINT if t.startswith("Train") else "white", fs=8)
        if i:
            D.arrow(ax, x - gap + 0.3, 11.5, x - 0.3, 11.5)
    ax.text(50, 2.5, "Every metric in this report is written to a model card (JSON) by the training script and read from there.",
            ha="center", fontsize=7.2, color="#444")
    save(f, "ml_pipeline.png")


if __name__ == "__main__":
    chain()
    pipeline()
    print("ok")

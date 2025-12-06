import json
from pathlib import Path
from typing import Dict, Any, List

import matplotlib.pyplot as plt


def _round2(x: float) -> float:
    return float(f"{x:.2f}")


def load_model_info(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def plot_model_info(model_info_path: str, output_path: str = None) -> str:
    info_path = Path(model_info_path)
    data = load_model_info(info_path)

    report = data.get("report", {})
    skip_keys = {"accuracy", "macro avg", "weighted avg"}
    
    # Respect saved label ordering (ensures classes like "serious" are plotted)
    labels: List[str] = [
        label for label in data.get("labels", []) if label in report and label not in skip_keys
    ]
    if not labels:
        labels = [label for label in report.keys() if label not in skip_keys]

    metrics = ["precision", "recall", "f1-score"]

    # Prepare data keeping two decimals
    values = {
        m: [
            _round2(float(report.get(lbl, {}).get(m, 0.0))) for lbl in labels
        ]
        for m in metrics
    }

    accuracy = _round2(float(report.get("accuracy", 0.0)))

    num_labels = len(labels)
    x = list(range(num_labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.bar([i - width for i in x], values["precision"], width=width, label="Precision")
    ax.bar(x, values["recall"], width=width, label="Recall")
    ax.bar([i + width for i in x], values["f1-score"], width=width, label="F1-score")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title(
        f"Model: {data.get('model_type', 'unknown')} | Accuracy: {accuracy:.2f}"
    )
    ax.legend(loc="best")

    # Annotate bars with values
    for container in ax.containers:
        for bar in container:
            height = bar.get_height()
            ax.annotate(
                f"{height:.2f}",
                (bar.get_x() + bar.get_width() / 2, height),
                ha="center",
                va="bottom",
                fontsize=8,
            )

    fig.tight_layout()

    if output_path is None:
        out_dir = info_path.parent
        output_path = str(out_dir / "model_metrics.png")

    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


if __name__ == "__main__":
    # Default locations within the repo
    default_model_info = Path(__file__).resolve().parent / "outputs" / "model_info.json"
    default_output = Path(__file__).resolve().parent / "outputs" / "model_metrics.png"
    path = plot_model_info(str(default_model_info), str(default_output))
    print(f"Saved plot to: {path}")



from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = PROJECT_ROOT / "benchmarks" / "results_snapshot_v1.json"
DEFAULT_OUTPUT_DIR = Path("sh2026_outputs") / "figures"


def load_reportable_rows(snapshot_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return [row for row in payload.get("rows", []) if row.get("status") == "reportable"]


def select_rows(
    rows: Iterable[dict[str, Any]], *, dataset: str, task: str
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("dataset") == dataset and row.get("task") == task
    ]


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "dataset",
        "task",
        "method",
        "precision",
        "recall",
        "f1",
        "status",
        "source_document",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in rows)


def write_f1_chart(rows: list[dict[str, Any]], title: str, output_path: Path) -> None:
    if not rows:
        raise ValueError(f"No reportable rows available for chart: {title}")

    import matplotlib.pyplot as plt

    methods = [str(row["method"]) for row in rows]
    scores = [float(row["f1"]) for row in rows]

    width = max(7.0, 1.35 * len(methods))
    fig, ax = plt.subplots(figsize=(width, 5.2))
    bars = ax.bar(range(len(methods)), scores)
    ax.set_title(title)
    ax.set_ylabel("F1")
    ax.set_ylim(0.0, 1.05)
    ax.set_xticks(range(len(methods)), methods, rotation=22, ha="right")
    ax.grid(axis="y", alpha=0.2)

    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            min(score + 0.025, 1.025),
            f"{score:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def build(snapshot_path: Path, output_dir: Path) -> list[Path]:
    rows = load_reportable_rows(snapshot_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    csv_path = output_dir / "reportable_results_v1.csv"
    write_csv(rows, csv_path)
    written.append(csv_path)

    charts = [
        (
            "Synthetic holdout v1",
            "TOPONYM",
            "Synthetic controlled holdout: TOPONYM exact-span F1",
            "synthetic_toponym_f1.png",
        ),
        (
            "Synthetic holdout v1",
            "Journey",
            "Synthetic controlled holdout: journey detection F1",
            "synthetic_journey_f1.png",
        ),
        (
            "CLDW external validation",
            "TOPONYM",
            "CLDW source-derived validation: TOPONYM exact-span F1",
            "cldw_toponym_f1.png",
        ),
    ]

    for dataset, task, title, filename in charts:
        selected = select_rows(rows, dataset=dataset, task=task)
        output_path = output_dir / filename
        write_f1_chart(selected, title, output_path)
        written.append(output_path)

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build keynote-safe SH2026 figures from the provenance-backed results snapshot."
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help="Path to results_snapshot_v1.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated CSV/PNG outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for path in build(args.snapshot, args.output_dir):
        print(path)


if __name__ == "__main__":
    main()

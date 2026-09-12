from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import pandas as pd

from spatio_textual.gold import assert_valid_gold, load_gold_jsonl
from spatio_textual.journey_benchmark import aggregate_journey_benchmark_rows, journey_benchmark_row
from spatio_textual.journey_transformer import (
    ID2LABEL,
    LABEL2ID,
    TransformerJourneyExtractor,
    align_token_labels,
    development_record_splits,
    journey_training_instances,
)

DEFAULT_BASE_MODEL = "distilbert/distilbert-base-cased"
DEV_SHA256 = "a5b89a40d0d0f7be1b3994852fa041c262ee56535d9ef400e50558d00666421b"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train the SH2026 non-generative transformer journey event baseline")
    p.add_argument("input", type=Path, help="Frozen journey development JSONL")
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/journey_transformer_dev"))
    p.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    p.add_argument("--revision", default=None, help="Pinned base-model revision; omit only for the initial development-resolution run")
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--learning-rate", type=float, default=5e-5)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument("--expected-sha256", default=DEV_SHA256)
    return p.parse_args()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


class RoleDataset:
    def __init__(self, instances: list[dict[str, Any]], tokenizer, max_length: int):
        self.rows = instances
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        row = self.rows[idx]
        encoded = self.tokenizer(
            row["text"],
            truncation=True,
            max_length=self.max_length,
            return_offsets_mapping=True,
        )
        offsets = encoded.pop("offset_mapping")
        encoded["labels"] = align_token_labels(offsets, row.get("roles", []))
        return encoded


def evaluate_token_roles(model, loader, torch) -> dict[str, Any]:
    model.eval()
    tp = fp = fn = 0
    correct_non_o = total_non_o_ref = total_non_o_pred = 0
    with torch.no_grad():
        for batch in loader:
            labels = batch.pop("labels")
            logits = model(**batch).logits
            predicted = logits.argmax(dim=-1)
            for pred_row, ref_row in zip(predicted.tolist(), labels.tolist()):
                for pred, ref in zip(pred_row, ref_row):
                    if ref == -100:
                        continue
                    ref_non_o = ref != LABEL2ID["O"]
                    pred_non_o = pred != LABEL2ID["O"]
                    if ref_non_o:
                        total_non_o_ref += 1
                    if pred_non_o:
                        total_non_o_pred += 1
                    if ref_non_o and pred == ref:
                        correct_non_o += 1
                    if pred_non_o and ref_non_o and pred == ref:
                        tp += 1
                    elif pred_non_o and pred != ref:
                        fp += 1
                    if ref_non_o and pred != ref:
                        fn += 1
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {
        "token_role_precision": round(p, 6),
        "token_role_recall": round(r, 6),
        "token_role_f1": round(f1, 6),
        "reference_non_o_tokens": total_non_o_ref,
        "predicted_non_o_tokens": total_non_o_pred,
        "exact_non_o_tokens": correct_non_o,
    }


def main() -> None:
    args = parse_args()
    actual_sha = sha256_path(args.input)
    if actual_sha.lower() != args.expected_sha256.strip().lower():
        raise SystemExit(f"Journey development checksum mismatch: expected {args.expected_sha256}, got {actual_sha}")

    records = load_gold_jsonl(args.input)
    assert_valid_gold(records)
    instances = journey_training_instances(records)
    train_rows = [row for row in instances if row["split"] == "train"]
    dev_rows = [row for row in instances if row["split"] == "dev"]
    if not train_rows or not dev_rows:
        raise SystemExit("Deterministic journey transformer split is empty")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "training_instances.jsonl").open("w", encoding="utf-8") as fh:
        for row in instances:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    set_seed(args.seed)
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForTokenClassification, AutoTokenizer, DataCollatorForTokenClassification

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, revision=args.revision, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(
        args.base_model,
        revision=args.revision,
        num_labels=len(LABEL2ID),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )
    resolved_revision = getattr(model.config, "_commit_hash", None)

    train_dataset = RoleDataset(train_rows, tokenizer, args.max_length)
    dev_dataset = RoleDataset(dev_rows, tokenizer, args.max_length)
    collator = DataCollatorForTokenClassification(tokenizer=tokenizer, padding=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)

    epoch_metrics: list[dict[str, Any]] = []
    for epoch in range(args.epochs):
        generator = torch.Generator()
        generator.manual_seed(args.seed + epoch)
        train_loader = DataLoader(
            train_dataset,
            batch_size=args.batch_size,
            shuffle=True,
            generator=generator,
            collate_fn=collator,
        )
        model.train()
        total_loss = 0.0
        batches = 0
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            output = model(**batch)
            output.loss.backward()
            optimizer.step()
            total_loss += float(output.loss.detach().cpu())
            batches += 1

        dev_loader = DataLoader(dev_dataset, batch_size=args.batch_size, shuffle=False, collate_fn=collator)
        metrics = evaluate_token_roles(model, dev_loader, torch)
        metrics.update({
            "epoch": epoch + 1,
            "train_loss_mean": round(total_loss / batches, 6) if batches else None,
        })
        epoch_metrics.append(metrics)
        print(json.dumps(metrics, ensure_ascii=False))

    model_dir = args.out_dir / "model"
    model.save_pretrained(model_dir)
    tokenizer.save_pretrained(model_dir)

    # Evaluate the trained condition only on source records assigned to the
    # development split. This is intentionally not the formal 30-item holdout.
    split_map = development_record_splits(records)
    dev_records = [record for record in records if split_map[str(record["example_id"])] == "dev"]
    extractor = TransformerJourneyExtractor(str(model_dir), max_length=args.max_length)
    journey_rows: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    for record in dev_records:
        example_id = str(record["example_id"])
        result = extractor.extract(str(record["text"]), file_id=example_id)
        predictions.append({
            "example_id": example_id,
            "journeys": result.get("journeys", []),
            "telemetry": result.get("telemetry", []),
        })
        journey_rows.append(journey_benchmark_row(
            example_id=example_id,
            predicted=result.get("journeys", []),
            reference=record.get("journeys", []),
            telemetry=result.get("telemetry", []),
            provider="local",
            model=f"transformer_token_event_v1:{args.base_model}@{resolved_revision or args.revision or 'resolved-main'}",
        ))

    summary = aggregate_journey_benchmark_rows(journey_rows)
    with (args.out_dir / "dev_predictions.jsonl").open("w", encoding="utf-8") as fh:
        for row in predictions:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.out_dir / "dev_journey_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in journey_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    pd.DataFrame([
        {
            "example_id": row["example_id"],
            "tp": row["tp"], "fp": row["fp"], "fn": row["fn"],
            "precision": row["precision"], "recall": row["recall"], "f1": row["f1"],
            "evidence_grounded_rate": row["evidence_grounded_rate"],
            "requires_review_rate": row["requires_review_rate"],
        }
        for row in journey_rows
    ]).to_csv(args.out_dir / "dev_journey_rows.csv", index=False)

    manifest = {
        "schema_version": "sh2026-transformer-journey-development-v1",
        "development_sha256": actual_sha,
        "base_model": args.base_model,
        "requested_revision": args.revision,
        "resolved_revision": resolved_revision,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "seed": args.seed,
        "max_length": args.max_length,
        "train_instances": len(train_rows),
        "dev_instances": len(dev_rows),
        "train_source_records": sum(1 for value in split_map.values() if value == "train"),
        "dev_source_records": len(dev_records),
        "labels": LABEL2ID,
        "epoch_metrics": epoch_metrics,
        "journey_dev_summary": summary,
        "claim_boundary": "Development-only result; the frozen SH2026 formal holdout was not evaluated by this script.",
    }
    (args.out_dir / "training_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out_dir / "dev_journey_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

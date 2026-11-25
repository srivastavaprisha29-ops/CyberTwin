"""Evaluate precomputed clip-level manipulation scores at a fixed threshold."""

import argparse
import csv
import json
import math
from collections import defaultdict


def evaluate(rows, threshold):
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1.")

    groups = defaultdict(lambda: dict(tp=0, fp=0, tn=0, fn=0))
    seen = set()
    for line, row in enumerate(rows, 2):
        dataset, compression, clip, label = (
            (row.get(key) or "").strip()
            for key in ("dataset", "compression", "clip_id", "label")
        )
        try:
            score = float(row.get("score") or "")
        except ValueError as exc:
            raise ValueError(f"Line {line}: expected a numeric score.") from exc
        if not all((dataset, compression, clip)) or label not in {"genuine", "manipulated"}:
            raise ValueError(f"Line {line}: missing identifiers or invalid label.")
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError(f"Line {line}: score must be between 0 and 1.")
        key = (dataset, compression, clip)
        if key in seen:
            raise ValueError(f"Line {line}: duplicate clip in this dataset and compression level.")
        seen.add(key)
        predicted = score >= threshold
        if label == "manipulated":
            outcome = "tp" if predicted else "fn"
        else:
            outcome = "fp" if predicted else "tn"
        groups[(dataset, compression)][outcome] += 1

    if not seen:
        raise ValueError("Provide at least one scored clip.")

    results = []
    for (dataset, compression), counts in sorted(groups.items()):
        genuine = counts["fp"] + counts["tn"]
        manipulated = counts["fn"] + counts["tp"]
        results.append({
            "dataset": dataset,
            "compression": compression,
            "genuine_clips": genuine,
            "manipulated_clips": manipulated,
            **counts,
            "false_positive_rate": counts["fp"] / genuine if genuine else None,
            "false_negative_rate": counts["fn"] / manipulated if manipulated else None,
        })
    return {"threshold": threshold, "strata": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scores", help="CSV of labeled clips and precomputed scores")
    parser.add_argument("--threshold", type=float, required=True, help="Threshold fixed before evaluation")
    args = parser.parse_args()
    try:
        with open(args.scores, encoding="utf-8-sig", newline="") as stream:
            report = evaluate(csv.DictReader(stream), args.threshold)
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

"""Evaluate precomputed clip-level manipulation scores at a fixed threshold."""

import argparse
import csv
import json
import math
from collections import Counter, defaultdict


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


def calibrate(rows, max_false_positive_rate):
    if not 0 <= max_false_positive_rate <= 1:
        raise ValueError("Maximum false-positive rate must be between 0 and 1.")
    evaluate(rows, 1.0)  # Apply the same input validation as held-out evaluation.
    genuine = Counter(float(row["score"]) for row in rows if row["label"].strip() == "genuine")
    manipulated = Counter(float(row["score"]) for row in rows if row["label"].strip() == "manipulated")
    genuine_total = sum(genuine.values())
    manipulated_total = sum(manipulated.values())
    if not genuine_total or not manipulated_total:
        raise ValueError("Calibration needs both genuine and manipulated clips.")

    fp = tp = 0
    best = None
    best_key = None
    # Include 1.0 so an operating point that flags nothing is considered when reachable.
    for threshold in sorted(genuine.keys() | manipulated.keys() | {1.0}, reverse=True):
        fp += genuine[threshold]
        tp += manipulated[threshold]
        rate = fp / genuine_total
        if rate > max_false_positive_rate:
            break
        key = (tp, -fp, threshold)
        if best_key is None or key > best_key:
            best_key = key
            best = {
                "threshold": threshold,
                "max_false_positive_rate": max_false_positive_rate,
                "false_positive_rate": rate,
                "recall": tp / manipulated_total,
                "genuine_clips": genuine_total,
                "manipulated_clips": manipulated_total,
            }
    if best is None:
        raise ValueError("No threshold in [0, 1] meets the false-positive limit.")
    return best


def read_scores(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def clip_keys(rows):
    return {(row["dataset"].strip(), row["clip_id"].strip()) for row in rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scores", help="Held-out CSV of labeled clips and precomputed scores")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--threshold", type=float, help="Threshold fixed before evaluation")
    mode.add_argument("--calibration", help="Separate CSV used to select a threshold")
    parser.add_argument("--max-fpr", type=float, help="Maximum pooled calibration false-positive rate")
    args = parser.parse_args()
    if (args.calibration is None) != (args.max_fpr is None):
        parser.error("--calibration and --max-fpr must be used together.")
    try:
        held_out = read_scores(args.scores)
        if args.calibration is None:
            report = evaluate(held_out, args.threshold)
        else:
            calibration = read_scores(args.calibration)
            operating_point = calibrate(calibration, args.max_fpr)
            report = evaluate(held_out, operating_point["threshold"])
            if clip_keys(calibration) & clip_keys(held_out):
                raise ValueError("Calibration and held-out splits share a dataset and clip identifier.")
            report["calibration"] = operating_point
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

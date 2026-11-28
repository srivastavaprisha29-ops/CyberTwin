"""Compare two offline media scorers on matched calibration and test clips."""

import argparse
import csv
import json

from evaluate_media import calibrate, clip_keys, evaluate, read_scores


def labels_by_clip(rows):
    return {
        tuple(row[key].strip() for key in ("dataset", "compression", "clip_id")):
        row["label"].strip()
        for row in rows
    }


def compare(baseline_cal, candidate_cal, baseline_test, candidate_test, max_fpr):
    baseline_point = calibrate(baseline_cal, max_fpr)
    candidate_point = calibrate(candidate_cal, max_fpr)
    baseline = evaluate(baseline_test, baseline_point["threshold"])
    candidate = evaluate(candidate_test, candidate_point["threshold"])

    for name, first, second in (
        ("calibration", baseline_cal, candidate_cal), ("held-out", baseline_test, candidate_test)
    ):
        if labels_by_clip(first) != labels_by_clip(second):
            raise ValueError(f"The {name} clips and labels must match across scorers.")
    if clip_keys(baseline_cal) & clip_keys(baseline_test):
        raise ValueError("Calibration and held-out splits share a dataset and clip identifier.")

    strata = []
    for first, second in zip(baseline["strata"], candidate["strata"]):
        change = {}
        for metric in ("false_positive_rate", "false_negative_rate"):
            before, after = first[metric], second[metric]
            change[metric] = None if before is None else 100 * (after - before)
        strata.append({
            "dataset": first["dataset"],
            "compression": first["compression"],
            "candidate_minus_baseline_percentage_points": change,
            "baseline": first,
            "candidate": second,
        })
    return {
        "baseline_calibration": baseline_point,
        "candidate_calibration": candidate_point,
        "held_out": strata,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-calibration", required=True)
    parser.add_argument("--candidate-calibration", required=True)
    parser.add_argument("--baseline-test", required=True)
    parser.add_argument("--candidate-test", required=True)
    parser.add_argument("--max-fpr", type=float, required=True)
    args = parser.parse_args()
    try:
        report = compare(
            read_scores(args.baseline_calibration), read_scores(args.candidate_calibration),
            read_scores(args.baseline_test), read_scores(args.candidate_test), args.max_fpr,
        )
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

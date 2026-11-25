"""Train a logistic regression candidate and compare it with peak frame change."""

import argparse
import csv
import json
import subprocess
from pathlib import Path
from statistics import mean

from compare_media import compare
from evaluate_media import clip_keys
from score_media import frame_changes, manifest_rows


def read_manifest(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(manifest_rows(stream, path))


def features(clip):
    changes = frame_changes(clip)
    return [max(changes), mean(changes)]


def run_experiment(train, calibration, test, max_fpr):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    keys = [clip_keys([row for row, _ in split]) for split in (train, calibration, test)]
    if keys[0] & keys[1] or keys[0] & keys[2] or keys[1] & keys[2]:
        raise ValueError("Training, calibration and held-out splits must use distinct clip IDs per dataset.")
    paths = [{path.resolve() for _, path in split} for split in (train, calibration, test)]
    if paths[0] & paths[1] or paths[0] & paths[2] or paths[1] & paths[2]:
        raise ValueError("Training, calibration and held-out splits must use distinct media paths.")
    labels = [int(row["label"] == "manipulated") for row, _ in train]
    if set(labels) != {0, 1}:
        raise ValueError("Training needs both genuine and manipulated clips.")
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit([features(clip) for _, clip in train], labels)

    def score_split(split):
        measurements = [features(clip) for _, clip in split]
        probabilities = model.predict_proba(measurements)[:, 1]
        return (
            [{**row, "score": item[0]} for (row, _), item in zip(split, measurements)],
            [{**row, "score": float(score)} for (row, _), score in zip(split, probabilities)],
        )

    base_cal, candidate_cal = score_split(calibration)
    base_test, candidate_test = score_split(test)
    result = compare(base_cal, candidate_cal, base_test, candidate_test, max_fpr)
    result["training_clips"] = len(train)
    result["candidate_features"] = ["peak_frame_change", "mean_frame_change"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for split in ("train", "calibration", "test"):
        parser.add_argument("--" + split, type=Path, required=True)
    parser.add_argument("--max-fpr", type=float, required=True)
    args = parser.parse_args()
    try:
        result = run_experiment(
            read_manifest(args.train), read_manifest(args.calibration), read_manifest(args.test),
            args.max_fpr,
        )
    except (ImportError, OSError, ValueError, csv.Error, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

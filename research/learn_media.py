"""Train a logistic regression candidate and compare it with peak frame change."""

import argparse
import csv
import json
import subprocess
from pathlib import Path
from statistics import mean

from compare_media import compare
from evaluate_media import clip_keys
from score_media import SIDE, adjacent_changes, decode_frames, manifest_rows


def read_manifest(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(manifest_rows(stream, path))


def aligned_delta(before, after, radius=8):
    """Return signed differences on a fixed crop after integer translation."""
    import numpy as np

    center = before[radius:-radius, radius:-radius]
    height, width = center.shape
    reference = center - center.mean()
    best = after[radius:-radius, radius:-radius]
    best_error = float("inf")
    # Try zero first so flat or ambiguous frames do not prefer a large shift.
    shifts = sorted(
        ((dy, dx) for dy in range(-radius, radius + 1) for dx in range(-radius, radius + 1)),
        key=lambda shift: abs(shift[0]) + abs(shift[1]),
    )
    for dy, dx in shifts:
        y, x = radius + dy, radius + dx
        window = after[y:y + height, x:x + width]
        error = np.mean(np.abs(reference - (window - window.mean())))
        if error < best_error:
            best, best_error = window, error
    return (best - center) / 255


def features(clip, spatial=False, motion=False):
    frames = decode_frames(clip)
    changes = adjacent_changes(frames)
    measurements = [max(changes), mean(changes)]
    if spatial or motion:
        import numpy as np

        pixels = np.frombuffer(frames, dtype=np.uint8).reshape(-1, SIDE, SIDE)
        pixels = pixels.astype(np.float32)
        delta = (
            np.stack([aligned_delta(before, after) for before, after in zip(pixels[:-1], pixels[1:])])
            if motion else np.diff(pixels, axis=0) / 255
        )
        residual = np.abs(delta - np.median(delta, axis=(1, 2), keepdims=True))
        blocks_per_side = residual.shape[1] // 8
        blocks = residual.reshape(-1, blocks_per_side, 8, blocks_per_side, 8).mean(axis=(2, 4))
        block_peak = blocks.max(axis=(1, 2))
        block_mean = blocks.mean(axis=(1, 2))
        measurements.extend([
            float(block_peak.mean()),
            float(block_mean.mean()),
            float((block_peak - block_mean).mean()),
        ])
    return measurements


def run_experiment(train, calibration, test, max_fpr, spatial=False, motion=False):
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
    model.fit([features(clip, spatial, motion) for _, clip in train], labels)

    def score_split(split):
        measurements = [features(clip, spatial, motion) for _, clip in split]
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
    if spatial or motion:
        result["candidate_features"].extend([
            "mean_peak_block_residual", "mean_block_residual", "mean_block_concentration"
        ])
    if motion:
        result["motion_alignment_radius_pixels"] = 8
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for split in ("train", "calibration", "test"):
        parser.add_argument("--" + split, type=Path, required=True)
    parser.add_argument("--max-fpr", type=float, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--spatial", action="store_true", help="Add block-change features")
    modes.add_argument("--motion", action="store_true", help="Add motion-aligned block-change features")
    args = parser.parse_args()
    try:
        result = run_experiment(
            read_manifest(args.train), read_manifest(args.calibration), read_manifest(args.test),
            args.max_fpr, spatial=args.spatial, motion=args.motion,
        )
    except (ImportError, OSError, ValueError, csv.Error, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

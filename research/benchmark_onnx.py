"""Benchmark a local ONNX checkpoint against peak frame change."""

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

from compare_media import compare
from evaluate_media import clip_keys
from score_media import manifest_rows

RESEARCH = Path(__file__).resolve().parent


def read_split(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(manifest_rows(stream, path))


def score(script, manifest, options=()):
    result = subprocess.run(
        [sys.executable, str(RESEARCH / script), str(manifest), *options],
        check=True, stdout=subprocess.PIPE, text=True,
    )
    return list(csv.DictReader(io.StringIO(result.stdout)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--max-fpr", type=float, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--mean", nargs=3, type=float, required=True)
    parser.add_argument("--std", nargs=3, type=float, required=True)
    parser.add_argument("--output", choices=("logit", "probability"), required=True)
    args = parser.parse_args()
    if not 0 <= args.max_fpr <= 1:
        parser.error("--max-fpr must be between 0 and 1.")
    try:
        calibration = read_split(args.calibration)
        test = read_split(args.test)
        if clip_keys(row for row, _ in calibration) & clip_keys(row for row, _ in test):
            raise ValueError("Calibration and test share dataset and clip identifiers.")
        if {path.resolve() for _, path in calibration} & {path.resolve() for _, path in test}:
            raise ValueError("Calibration and test share resolved media paths.")

        with args.model.open("rb") as stream:
            checkpoint_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
        options = [
            "--model", str(args.model), "--size", str(args.size),
            "--mean", *map(str, args.mean), "--std", *map(str, args.std),
            "--output", args.output,
        ]
        report = compare(
            score("score_media.py", args.calibration),
            score("score_onnx.py", args.calibration, options),
            score("score_media.py", args.test),
            score("score_onnx.py", args.test, options),
            args.max_fpr,
        )
    except subprocess.CalledProcessError as exc:
        parser.error(f"{Path(exc.cmd[1]).name} failed. See the scorer error above.")
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))
    report["onnx_configuration"] = {
        "model_file_sha256": checkpoint_sha256, "size": args.size,
        "mean": args.mean, "std": args.std, "output": args.output,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

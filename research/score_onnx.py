"""Score model-ready clips with a local binary image classifier in ONNX format."""

import argparse
import csv
import io
import math
from pathlib import Path

from score_media import FIELDS, decode_frames, manifest_rows


def aggregate_scores(scores, mode):
    if mode == "three-frame-window":
        width = min(3, len(scores))
        return max(sum(scores[start:start + width]) / width
                   for start in range(len(scores) - width + 1))
    if mode == "top-quarter":
        count = (len(scores) + 3) // 4
        scores = sorted(scores, reverse=True)[:count]
    return sum(scores) / len(scores)


def score_clip(session, path, side, mean, std, output_type, aggregation="mean"):
    import numpy as np

    raw = decode_frames(path, side=side, rgb=True)
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, side, side, 3)
    center = np.asarray(mean, dtype=np.float32)
    scale = np.asarray(std, dtype=np.float32)
    input_name = session.get_inputs()[0].name
    scores = []
    for frame in frames:
        normalized = (frame.astype(np.float32) / 255 - center) / scale
        tensor = np.ascontiguousarray(normalized.transpose(2, 0, 1)[None])
        (output,) = session.run(None, {input_name: tensor})
        if output.size != 1 or not np.isfinite(output).all():
            raise ValueError(f"Expected one finite output value per frame: {path}")
        score = float(output.item())
        if output_type == "logit":
            magnitude = math.exp(-abs(score))
            score = 1 / (1 + magnitude) if score >= 0 else magnitude / (1 + magnitude)
        if not 0 <= score <= 1:
            raise ValueError(f"Probability is outside [0, 1]: {path}")
        scores.append(score)
    return aggregate_scores(scores, aggregation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--mean", nargs=3, type=float, required=True, metavar=("R", "G", "B"))
    parser.add_argument("--std", nargs=3, type=float, required=True, metavar=("R", "G", "B"))
    parser.add_argument("--output", choices=("logit", "probability"), required=True)
    parser.add_argument("--aggregation", choices=("mean", "top-quarter", "three-frame-window"), default="mean")
    args = parser.parse_args()
    if not 1 <= args.size <= 512:
        parser.error("--size must be in [1, 512].")
    if not all(math.isfinite(n) for n in args.mean + args.std) or min(args.std) <= 0:
        parser.error("Mean and standard deviation must be finite, and deviations must be positive.")

    try:
        import onnxruntime as ort
    except ImportError:
        parser.error("Install onnxruntime and numpy to score clips.")

    try:
        session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
        if len(session.get_inputs()) != 1 or len(session.get_outputs()) != 1:
            raise ValueError("The model must expose one tensor input and one output.")
        inputs = session.get_inputs()[0]
        expected = (1, 3, args.size, args.size)
        if inputs.type != "tensor(float)" or len(inputs.shape) != 4 or any(
            isinstance(dim, int) and dim != size for dim, size in zip(inputs.shape, expected)
        ):
            raise ValueError("Expected an FP32 NCHW input matching the requested frame size.")
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=(*FIELDS, "score"))
        writer.writeheader()
        with args.manifest.open(encoding="utf-8-sig", newline="") as stream:
            for record, clip in manifest_rows(stream, args.manifest):
                value = score_clip(session, clip, args.size, args.mean, args.std, args.output, args.aggregation)
                writer.writerow({**record, "score": value})
    except Exception as exc:
        # ONNX Runtime uses several native exception types for model and inference failures.
        parser.error(str(exc))
    print(buffer.getvalue(), end="")


if __name__ == "__main__":
    main()

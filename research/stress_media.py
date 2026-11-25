"""Run a reproducible synthetic stress test of both media scorers."""

import argparse
import json
import random
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from learn_media import run_experiment

SIDE = 64
FRAMES = 8
SCENARIOS = {
    "hard-cut": "genuine",
    "moving-object": "genuine",
    "lighting-flicker": "genuine",
    "localized-edit": "manipulated",
    "full-frame-edit": "manipulated",
}

FRESH_SCENARIOS = {
    "camera-pan": "genuine",
    "lighting-ramp": "genuine",
    "hard-cut-with-motion": "genuine",
    "low-contrast-patch": "manipulated",
    "brief-patch": "manipulated",
}


def fresh_frames_for(scenario, seed):
    rng = random.Random(seed)
    # A wider canvas lets the camera pan without wrapping the image.
    stride = SIDE + 24
    canvas = bytes(rng.randint(35, 130) for _ in range(SIDE * stride))
    for frame in range(FRAMES):
        offset = frame * 3 if scenario in {"camera-pan", "hard-cut-with-motion"} else 0
        pixels = bytearray(b"".join(
            canvas[row * stride + offset:row * stride + offset + SIDE]
            for row in range(SIDE)
        ))
        if scenario == "hard-cut-with-motion" and frame >= FRAMES // 2:
            pixels.reverse()
        elif scenario == "lighting-ramp":
            pixels = bytearray(value + frame * 7 for value in pixels)
        elif ((scenario == "low-contrast-patch" and frame % 2)
              or (scenario == "brief-patch" and frame == 4)):
            shift = 18 if scenario == "low-contrast-patch" else 65
            for y in range(21, 31):
                for x in range(29, 39):
                    index = y * SIDE + x
                    pixels[index] += shift
        yield pixels


def frames_for(scenario, seed):
    rng = random.Random(seed)
    texture = bytes(rng.randint(35, 130) for _ in range(SIDE * SIDE))
    for frame in range(FRAMES):
        pixels = bytearray(texture)
        if scenario == "hard-cut" and frame >= FRAMES // 2:
            pixels.reverse()
        elif scenario == "lighting-flicker" and frame % 2:
            pixels = bytearray(value + 45 for value in pixels)
        elif scenario == "full-frame-edit" and frame % 2:
            pixels.reverse()
        elif scenario in {"moving-object", "localized-edit"}:
            start = 8 + frame * 4 if scenario == "moving-object" else 24
            value = 205 if scenario == "moving-object" or frame % 2 else 80
            for y in range(24, 36):
                offset = y * SIDE + start
                pixels[offset:offset + 12] = bytes([value]) * 12
        yield pixels


def make_split(directory, split, seed, scenarios=SCENARIOS, generator=frames_for):
    rows = []
    for index, (scenario, label) in enumerate(scenarios.items()):
        raw = b"".join(generator(scenario, seed + index))
        clip_id = f"{split}-{scenario}"
        for compression, quality in (("jpeg-high", "2"), ("jpeg-low", "18")):
            path = directory / f"{clip_id}-{compression}.avi"
            subprocess.run([
                "ffmpeg", "-nostdin", "-v", "error", "-f", "rawvideo",
                "-pix_fmt", "gray", "-s", f"{SIDE}x{SIDE}", "-r", "5",
                "-i", "pipe:0", "-c:v", "mjpeg", "-threads", "1",
                "-pix_fmt", "yuvj420p", "-q:v", quality, str(path),
            ], input=raw, check=True, timeout=60)
            rows.append(({
                "dataset": scenario,
                "compression": compression,
                "clip_id": clip_id,
                "label": label,
            }, path))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-fpr", type=float, default=0.0,
                        help="Pooled calibration false-positive cap (default: 0)")
    parser.add_argument("--fresh", action="store_true", help="Use fresh held-out scenarios")
    args = parser.parse_args()
    try:
        with TemporaryDirectory(prefix="cybertwin-stress-") as temp:
            root = Path(temp)
            train = make_split(root, "train", 100)
            calibration = make_split(root, "calibration", 200)
            test = (
                make_split(root, "fresh", 400, FRESH_SCENARIOS, fresh_frames_for)
                if args.fresh else make_split(root, "test", 300)
            )
            splits = (train, calibration, test)
            report = run_experiment(*splits, args.max_fpr)
            report["held_out_suite"] = "fresh" if args.fresh else "original"
            report["spatial_experiment"] = run_experiment(*splits, args.max_fpr, spatial=True)
    except (ImportError, OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

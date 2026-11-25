"""Generate clip-level scores using a simple frame-change baseline."""

import argparse
import csv
import io
import subprocess
from pathlib import Path

SIDE = 64
FRAME_BYTES = SIDE * SIDE
FIELDS = ("dataset", "compression", "clip_id", "label")


def frame_changes(path):
    if not path.is_file():
        raise ValueError(f"Clip does not exist: {path}")
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-xerror",
        "-protocol_whitelist", "file", "-i", str(path.resolve()),
        "-map", "0:v:0", "-vf", f"fps=5,scale={SIDE}:{SIDE},format=gray",
        "-frames:v", "150", "-threads", "1", "-f", "rawvideo", "pipe:1",
    ]
    try:
        raw = subprocess.run(command, capture_output=True, check=True, timeout=60).stdout
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"Could not decode {path}: {exc.stderr.decode(errors='replace').strip()}") from exc
    if len(raw) < FRAME_BYTES * 2 or len(raw) % FRAME_BYTES:
        raise ValueError(f"Need at least two complete sampled frames: {path}")
    frames = memoryview(raw)
    return [
        sum(abs(a - b) for a, b in zip(
            frames[start - FRAME_BYTES:start], frames[start:start + FRAME_BYTES]
        )) / (255 * FRAME_BYTES)
        for start in range(FRAME_BYTES, len(raw), FRAME_BYTES)
    ]


def score_clip(path):
    return max(frame_changes(path))


def manifest_rows(stream, path):
    manifest = csv.DictReader(stream)
    if not set((*FIELDS, "path")).issubset(manifest.fieldnames or ()):
        raise ValueError("Manifest requires dataset, compression, clip_id, label and path.")
    seen = set()
    for line, row in enumerate(manifest, 2):
        record = {name: (row.get(name) or "").strip() for name in FIELDS}
        filename = (row.get("path") or "").strip()
        if not all(record.values()) or not filename or record["label"] not in {"genuine", "manipulated"}:
            raise ValueError(f"Line {line}: missing values or invalid label.")
        key = tuple(record[name] for name in FIELDS[:3])
        if key in seen:
            raise ValueError(f"Line {line}: duplicate clip identifier in this stratum.")
        seen.add(key)
        yield record, path.parent / filename
    if not seen:
        raise ValueError("Manifest contains no clips.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=(*FIELDS, "score"))
    writer.writeheader()
    try:
        with args.manifest.open(encoding="utf-8-sig", newline="") as stream:
            for record, clip_path in manifest_rows(stream, args.manifest):
                writer.writerow({**record, "score": score_clip(clip_path)})
    except (ValueError, OSError, csv.Error, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(output.getvalue(), end="")


if __name__ == "__main__":
    main()

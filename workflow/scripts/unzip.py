"""Safely extract ZIP archives from the command line."""

from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path


def _safe_member_path(root: Path, member: str) -> Path:
    target = (root / member).resolve()
    root_resolved = root.resolve()
    if root_resolved != target and root_resolved not in target.parents:
        raise ValueError(f"Unsafe ZIP member path: {member}")
    return target


def unzip_archive(input_path: str | Path, output_path: str | Path) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=output_path.parent) as tmpdir:
        tmpdir = Path(tmpdir)
        extract_root = tmpdir / "content"
        extract_root.mkdir()

        with zipfile.ZipFile(input_path, "r") as archive:
            for member in archive.infolist():
                _safe_member_path(extract_root, member.filename)
            archive.extractall(extract_root)

        if output_path.exists():
            shutil.rmtree(output_path)
        shutil.move(str(extract_root), str(output_path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract a ZIP archive safely.")
    parser.add_argument("--input", required=True, help="Input ZIP archive")
    parser.add_argument("--output", required=True, help="Output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(f"Extracting: {args.input}")
    print(f"Destination: {args.output}")
    unzip_archive(args.input, args.output)
    print("Completed")

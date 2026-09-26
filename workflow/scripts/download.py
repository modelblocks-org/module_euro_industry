"""Generic command-line downloader for the Snakemake workflow."""

from __future__ import annotations

import argparse
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


def download(url: str, output: str | Path, timeout: int = 120) -> None:
    """Download *url* atomically to *output*."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "industry-data-download/0.1"},
    )

    tmp_path: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                delete=False,
                dir=output.parent,
                prefix=f".{output.name}.",
            ) as tmp:
                shutil.copyfileobj(response, tmp)
                tmp_path = Path(tmp.name)

        if tmp_path.stat().st_size == 0:
            raise RuntimeError(f"Downloaded file is empty: {url}")

        tmp_path.replace(output)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download {url}: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a file from a URL.")
    parser.add_argument("--url", required=True, help="Source URL")
    parser.add_argument("--output", required=True, help="Destination file")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output = Path(args.output)

    print(f"Downloading: {args.url}")
    print(f"Destination: {output}")
    download(args.url, output, timeout=args.timeout)
    print(f"Completed: {output.stat().st_size} bytes")

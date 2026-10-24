"""
download_cuad.py
Standalone script to download the CUAD v1 dataset (Contract Understanding Atticus Dataset).

Downloads from HuggingFace (primary) or Zenodo (fallback).
Validates the JSON structure and reports the contract count.

Usage:
    cd d:/legal/backend
    .venv/Scripts/python -m scripts.download_cuad
    .venv/Scripts/python -m scripts.download_cuad --destination ./data/CUAD_v1.json
"""

import argparse
import json
import logging
import os
import sys
import zipfile

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_cuad")

# Primary: HuggingFace datasets direct resolve
# Fallback: Zenodo DOI-based archive (ZIP)
CUAD_DOWNLOAD_URLS: list[dict[str, str]] = [
    {
        "name": "HuggingFace Datasets (theatticusproject/cuad)",
        "url": "https://huggingface.co/datasets/theatticusproject/cuad/resolve/main/CUAD_v1/CUAD_v1.json",
        "format": "json",
    },
    {
        "name": "Zenodo Archive (4595826)",
        "url": "https://zenodo.org/records/4595826/files/CUAD_v1.zip",
        "format": "zip",
    },
]

DEFAULT_DESTINATION = os.path.join("data", "CUAD_v1.json")

# Minimum expected file size (100KB) to detect truncated downloads
MIN_VALID_SIZE_BYTES = 100_000


def download_cuad_dataset(destination: str = DEFAULT_DESTINATION) -> str:
    """
    Download the CUAD v1 dataset to the specified local path.

    Tries multiple mirrors in order. Validates the downloaded file contains
    valid JSON with a 'data' key containing contract entries.

    Args:
        destination: Local file path to save the dataset.

    Returns:
        The absolute path of the downloaded file.

    Raises:
        RuntimeError: If all download attempts fail or the file is invalid.
    """
    abs_dest = os.path.abspath(destination)

    if os.path.exists(abs_dest):
        # Validate existing file
        try:
            size = os.path.getsize(abs_dest)
            if size > MIN_VALID_SIZE_BYTES:
                with open(abs_dest, encoding="utf-8") as f:
                    data = json.load(f)
                num_contracts = len(data.get("data", []))
                if num_contracts > 0:
                    logger.info(
                        "CUAD dataset already exists at %s (%d contracts, %.1f MB). Skipping download.",
                        abs_dest,
                        num_contracts,
                        size / (1024 * 1024),
                    )
                    return abs_dest
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Existing file at %s is corrupt (%s). Re-downloading.", abs_dest, e)

    os.makedirs(os.path.dirname(abs_dest) or ".", exist_ok=True)

    for source in CUAD_DOWNLOAD_URLS:
        name = source["name"]
        url = source["url"]
        logger.info("Attempting download from %s: %s", name, url)

        is_zip = source.get("format") == "zip" or url.endswith(".zip")
        download_target = (abs_dest + ".zip.tmp") if is_zip else (abs_dest + ".tmp")
        tmp_path = abs_dest + ".tmp"

        try:
            # Stream download with generous timeout
            with httpx.Client(timeout=httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0), follow_redirects=True) as client:
                with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        logger.warning("HTTP %d from %s. Trying next source.", response.status_code, name)
                        continue

                    total_bytes = 0
                    with open(download_target, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=1024 * 256):
                            f.write(chunk)
                            total_bytes += len(chunk)
                            # Progress indicator every 10MB
                            if total_bytes % (10 * 1024 * 1024) < (256 * 1024):
                                logger.info("  Downloaded %.1f MB so far...", total_bytes / (1024 * 1024))

            if total_bytes < MIN_VALID_SIZE_BYTES:
                logger.warning("Downloaded file too small (%d bytes) from %s. Trying next.", total_bytes, name)
                if os.path.exists(download_target):
                    os.remove(download_target)
                continue

            # If it's a zip archive, extract CUAD_v1.json from it
            if is_zip:
                logger.info("Extracting CUAD_v1.json from archive %s...", download_target)
                with zipfile.ZipFile(download_target, "r") as z:
                    # Look for CUAD_v1.json in the zip
                    target_member = None
                    for member in z.namelist():
                        if os.path.basename(member).lower() == "cuad_v1.json":
                            target_member = member
                            break
                    if not target_member:
                        raise ValueError("No CUAD_v1.json found in downloaded ZIP archive")
                    with z.open(target_member) as source_f, open(tmp_path, "wb") as dest_f:
                        while chunk := source_f.read(1024 * 256):
                            dest_f.write(chunk)
                if os.path.exists(download_target):
                    os.remove(download_target)

            # Validate JSON structure
            logger.info("Validating downloaded JSON structure...")
            with open(tmp_path, encoding="utf-8") as f:
                data = json.load(f)

            num_contracts = len(data.get("data", []))
            if num_contracts == 0:
                logger.warning("Downloaded JSON has no 'data' entries from %s. Trying next.", name)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                continue

            # Atomic rename
            os.replace(tmp_path, abs_dest)
            logger.info(
                "Successfully downloaded CUAD dataset to %s (%d contracts, %.1f MB).",
                abs_dest,
                num_contracts,
                os.path.getsize(abs_dest) / (1024 * 1024),
            )
            return abs_dest

        except (httpx.HTTPError, OSError, json.JSONDecodeError, zipfile.BadZipFile, ValueError) as e:
            logger.warning("Download from %s failed: %s", name, e)
            for path_to_clean in (download_target, tmp_path):
                if os.path.exists(path_to_clean):
                    os.remove(path_to_clean)
            continue

    raise RuntimeError(
        "Failed to download CUAD dataset from all sources. "
        "Please download CUAD_v1.json manually from https://huggingface.co/datasets/theatticusproject/cuad "
        f"and place it at: {abs_dest}"
    )


def main() -> None:
    """CLI entrypoint for standalone CUAD download."""
    parser = argparse.ArgumentParser(description="Download the CUAD v1 dataset.")
    parser.add_argument(
        "--destination",
        type=str,
        default=DEFAULT_DESTINATION,
        help=f"Destination path for the dataset (default: {DEFAULT_DESTINATION})",
    )
    args = parser.parse_args()

    try:
        path = download_cuad_dataset(args.destination)
        print(f"\nCUAD dataset ready at: {path}")
    except RuntimeError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

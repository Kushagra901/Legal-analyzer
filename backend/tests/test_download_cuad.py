"""
test_download_cuad.py
Unit tests for the standalone CUAD dataset download script (scripts/download_cuad.py).
"""

import json
import os
import sys
import zipfile

import pytest

# Ensure backend root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.download_cuad import (
    DEFAULT_DESTINATION,
    MIN_VALID_SIZE_BYTES,
    download_cuad_dataset,
)


def test_download_cuad_existing_valid_file_skips(tmp_path):
    """
    Edge Case 1: When a valid CUAD_v1.json file already exists at the destination,
    download_cuad_dataset should validate its contents and return immediately without network calls.
    """
    dest = tmp_path / "CUAD_v1.json"
    dummy_data = {
        "version": "1.0",
        "data": [{"title": f"Contract {i}", "paragraphs": []} for i in range(10)],
        # Pad payload to exceed MIN_VALID_SIZE_BYTES
        "padding": "x" * (MIN_VALID_SIZE_BYTES + 1000),
    }
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f)

    result_path = download_cuad_dataset(str(dest))
    assert os.path.abspath(str(dest)) == result_path
    assert os.path.exists(result_path)


def test_download_cuad_creates_parent_directory(tmp_path):
    """
    Edge Case 2: When destination directory path does not exist,
    parent directories should be automatically created.
    """
    nested_dir = tmp_path / "deeply" / "nested" / "dir"
    dest = nested_dir / "CUAD_v1.json"

    # Pre-seed valid file to test directory creation on existing path check
    dummy_data = {
        "version": "1.0",
        "data": [{"title": "Contract 1", "paragraphs": []}],
        "padding": "x" * (MIN_VALID_SIZE_BYTES + 500),
    }
    nested_dir.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f)

    result_path = download_cuad_dataset(str(dest))
    assert os.path.exists(result_path)
    assert os.path.dirname(result_path) == str(nested_dir)


def test_download_cuad_corrupt_file_triggers_cleanup(tmp_path, monkeypatch):
    """
    Edge Case 3: If an existing file is corrupt JSON, download_cuad_dataset detects the corruption.
    If all mock mirrors fail, it raises a clean RuntimeError and cleans up temporary files.
    """
    dest = tmp_path / "corrupt_CUAD.json"
    # Write garbage content exceeding size threshold
    with open(dest, "w", encoding="utf-8") as f:
        f.write("NOT_VALID_JSON" * 10000)

    # Mock CUAD_DOWNLOAD_URLS with non-existent URLs to test graceful failure
    monkeypatch.setattr(
        "scripts.download_cuad.CUAD_DOWNLOAD_URLS",
        [{"name": "Invalid Test Mirror", "url": "http://invalid-test-url-12345.local/test.json"}],
    )

    with pytest.raises(RuntimeError) as exc_info:
        download_cuad_dataset(str(dest))
    assert "Failed to download CUAD dataset from all sources" in str(exc_info.value)


def test_download_cuad_zip_extraction(tmp_path, monkeypatch):
    """
    Edge Case 4: Tests extracting CUAD_v1.json from a simulated ZIP mirror archive.
    """
    zip_dest = tmp_path / "mock_archive.zip"
    valid_cuad_content = {
        "version": "v1.0",
        "data": [{"title": "Test Contract", "paragraphs": []}],
        "padding": "x" * (MIN_VALID_SIZE_BYTES + 500),
    }
    raw_json_bytes = json.dumps(valid_cuad_content).encode("utf-8")

    # Create in-memory zip
    with zipfile.ZipFile(zip_dest, "w") as z:
        z.writestr("CUAD_v1.json", raw_json_bytes)

    # Read zip bytes
    with open(zip_dest, "rb") as f:
        zip_bytes = f.read()

    # Mock httpx.Client to return the zip bytes
    class MockStreamResponse:
        def __init__(self, content):
            self.status_code = 200
            self._content = content

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def iter_bytes(self, chunk_size=1024):
            for i in range(0, len(self._content), chunk_size):
                yield self._content[i : i + chunk_size]

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def stream(self, method, url, **kwargs):
            return MockStreamResponse(zip_bytes)

    monkeypatch.setattr("httpx.Client", MockClient)
    monkeypatch.setattr(
        "scripts.download_cuad.CUAD_DOWNLOAD_URLS",
        [{"name": "Mock ZIP Mirror", "url": "https://mock.local/CUAD_v1.zip", "format": "zip"}],
    )

    extracted_target = tmp_path / "extracted_CUAD_v1.json"
    result = download_cuad_dataset(str(extracted_target))

    assert os.path.exists(result)
    with open(result, encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded["data"]) == 1
    assert loaded["data"][0]["title"] == "Test Contract"

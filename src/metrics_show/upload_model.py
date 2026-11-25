import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx


def _upload_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise ValueError("Use an HTTP(S) run URL without embedded credentials")

    path = parts.path.rstrip("/")
    if parts.fragment:
        match = re.fullmatch(r"/spaces/[^/]+/runs/([^/]+)/?", parts.fragment)
        if match is None:
            raise ValueError("Use the detail page URL of a completed run")
        run_id = UUID(match[1])
        path = f"{path}/api/v1/runs/{run_id}/models"
    else:
        match = re.fullmatch(r"(.*)/api/v1/runs/([^/]+)/models", path)
        if match is None:
            raise ValueError("Use a run detail URL or the full model upload API URL")
        run_id = UUID(match[2])
        path = f"{match[1]}/api/v1/runs/{run_id}/models"

    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def upload_model(file_path: str | os.PathLike[str], url: str) -> dict:
    """Upload a file to a completed run and return its server metadata.

    Pass the experiment page URL or the full /api/v1/runs/{id}/models URL.
    The token is read from METRICS_SHOW_TOKEN or TYPIE_API_KEY.
    """
    endpoint = _upload_url(url)
    api_key = (
        os.getenv("METRICS_SHOW_TOKEN", "").strip()
        or os.getenv("TYPIE_API_KEY", "").strip()
    )
    if not api_key:
        raise RuntimeError("Set METRICS_SHOW_TOKEN or TYPIE_API_KEY before uploading")
    return _post_model(
        httpx.post, endpoint, file_path, headers={"Authorization": f"Bearer {api_key}"}
    )


def _post_model(post, endpoint, file_path, *, headers=None):
    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    with path.open("rb") as file:
        size = os.fstat(file.fileno()).st_size
        if not size:
            raise ValueError("Model file must not be empty")
        response = post(
            endpoint,
            params={"filename": path.name},
            headers={
                **(headers or {}),
                "Content-Type": "application/octet-stream",
                "Content-Length": str(size),
            },
            content=iter(lambda: file.read(1024 * 1024), b""),
            timeout=120,
            follow_redirects=False,
        )
    response.raise_for_status()
    return response.json()

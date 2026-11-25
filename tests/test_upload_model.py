import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

import httpx
from metrics_show import upload_model


class ModelUploadTest(unittest.TestCase):
    def test_uploads_from_either_url(self):
        run = uuid4()
        base = "https://example.invalid"
        endpoint = f"{base}/api/v1/runs/{run}/models"
        payload = b"\x00weights" * 150_000
        urls = (f"{base}/#/spaces/{uuid4()}/runs/{run}", endpoint)

        def post(url, *, params, headers, content, timeout, follow_redirects):
            self.assertEqual(url, endpoint)
            self.assertEqual(params, {"filename": "best.pt"})
            self.assertEqual(headers["Authorization"], "Bearer test-only")
            self.assertEqual(headers["Content-Type"], "application/octet-stream")
            self.assertEqual(headers["Content-Length"], str(len(payload)))
            self.assertFalse(follow_redirects)
            first = next(content)
            self.assertLess(len(first), len(payload))
            self.assertEqual(first + b"".join(content), payload)
            return httpx.Response(
                200, json={"name": "best.pt"}, request=httpx.Request("POST", url)
            )

        with TemporaryDirectory() as directory:
            file = Path(directory) / "best.pt"
            file.write_bytes(payload)
            with patch.object(httpx, "post", side_effect=post):
                for env_name, url in zip(("METRICS_SHOW_TOKEN", "TYPIE_API_KEY"), urls):
                    with (
                        self.subTest(env_name=env_name),
                        patch.dict("os.environ", {env_name: "test-only"}, clear=True),
                    ):
                        self.assertEqual(upload_model(file, url)["name"], "best.pt")

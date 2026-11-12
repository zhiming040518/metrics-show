import json
import unittest
from uuid import uuid4

import httpx

from metrics_show import Event, Metric, MetricsClient


class MetricsContractTest(unittest.TestCase):
    def test_write_and_read_the_wire_format(self):
        run = uuid4()
        event = Event(step=1, values={"epoch": 1, "val/f1": 0.84})
        methods = []

        def handle(request):
            methods.append(request.method)
            self.assertEqual(request.headers["authorization"], "Bearer test-only")
            self.assertTrue(request.url.path.startswith("/api/v1/runs"))
            if request.method == "GET":
                self.assertEqual(request.url.params["after"], "0")
                return httpx.Response(
                    200,
                    json={
                        "events": [event.model_dump(mode="json")],
                        "next": 1,
                        "has_more": False,
                    },
                )
            if request.url.path.endswith("/events"):
                self.assertEqual(
                    json.loads(request.content)["events"][0]["id"], str(event.id)
                )
            return httpx.Response(200, json={"ok": True})

        with MetricsClient(
            "http://localhost", "test-only", transport=httpx.MockTransport(handle)
        ) as client:
            self.assertEqual(client.create_run("example", "baseline", run_id=run), run)
            client.define_metric(run, Metric(name="val/f1", x="epoch"))
            client.submit(run, [event])
            client.finish(run)
            self.assertEqual(list(client.iter_events(run)), [event])
        self.assertEqual(methods, ["POST", "PUT", "POST", "POST", "GET"])

# Metrics Show

Python client and request models for reporting training and evaluation metrics to a compatible `/api/v1` service. The client is synchronous and accepts explicit event batches.

```shell
python -m pip install .
```

Set `METRICS_SHOW_URL` to the base URL of your own service and `METRICS_SHOW_TOKEN` to a token scoped to the intended workspace. Use HTTPS when reporting to a remote host. Keep tokens in environment variables and out of source control. This package supplies the client and wire models. A compatible server is required.

```shell
python examples/report_metrics.py
```

| Method and path under `/api/v1` | Purpose |
| --- | --- |
| `POST /runs` | Register a run with a client-generated UUID, a project name, a run name, and optional configuration. Reuse the UUID when retrying registration. |
| `PUT /runs/{id}/metrics` | Declare display style, axis, label, and unit for a metric. |
| `POST /runs/{id}/events` | Submit 1–200 events. Each contains an event UUID, step, Unix timestamp in seconds, and a map of finite numeric values. |
| `GET /runs/{id}/events?after=0&limit=500` | Read the `events`, `next`, and `has_more` fields. Pass `next` back as `after` for the following page. |
| `POST /runs/{id}/heartbeat` | Mark a run completed, failed, or stopped. |
| `POST /runs/{id}/models?filename=...` | Upload a model file to a completed run on a server that supports model storage. |

Requests carry `Authorization: Bearer <token>`. Use the same `Event` objects or UUIDs when retrying a batch so the service can deduplicate it. The read cursor follows ingestion order. For plotting and statistics, sort by step and use the event with the latest timestamp at each step, breaking timestamp ties by event UUID. Supply the epoch and its metric in the same event when the chosen axis is `epoch`. Use consistent units across runs when computing differences.

## Upload a model file

After the server records the run as completed, set the run owner's workspace token in `METRICS_SHOW_TOKEN` (or reuse `TYPIE_API_KEY`), then pass the file path and run detail URL:

```python
from metrics_show import upload_model

run_url = "https://example.invalid/#/spaces/SPACE_ID/runs/RUN_UUID"
result = upload_model("weights/best.pt", run_url)
print(result["name"], result["sha256"])
```

Replace the example URL with the address copied from your browser. You can also pass the full `/api/v1/runs/{id}/models` endpoint URL. The helper streams the file using its local filename and returns the server's model metadata.

The bundled contract tests use a mock transport or request stub and require no server or credentials.

```shell
python -m unittest discover -s tests
```

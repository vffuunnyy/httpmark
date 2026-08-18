# Runs

One folder per run: machine + library versions + Python version. Each folder holds
the raw `results.json` (full per-iteration data, environment and package versions
embedded) and a `README.md` generated from it:

```bash
uv run httpmark --rounds 3 --shuffle --cpu-affinity <cores> --output results.json
python scripts/report.py results/<date>-<machine>/results.json
```

Optional tuned pass for the tokio-backed clients (rnet, wreq, primp):

```bash
TOKIO_WORKER_THREADS=1 uv run httpmark --categories async-http1 async-http2 \
    --clients rnet wreq primp --output results-tokio1.json
python scripts/report.py results/<dir>/results.json --tuned results/<dir>/results-tokio1.json
```

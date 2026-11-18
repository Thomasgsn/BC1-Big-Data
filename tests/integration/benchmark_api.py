"""Mesure de lecture réelle à 5 requêtes/s ; aucun écrit métier ni secret affiché."""

from datetime import datetime, timezone
import json
import os
import time
import urllib.request
import urllib.error

from benchmark_sql import distribution


def main():
    request = urllib.request.Request("http://api:8000/v1/alerts?limit=1",
                                    headers={"Authorization": "Bearer "+os.environ["API_TOKEN_ANALYST"]})
    timings, errors, started = [], [], time.monotonic()
    for position in range(50):
        time.sleep(max(0, started+position/5-time.monotonic()))
        begin = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = json.load(response)
            if len(body["items"]) != 1:
                errors.append("unexpected_item_count")
        except urllib.error.HTTPError as error:
            errors.append(error.code)
        timings.append((time.monotonic()-begin)*1000)
    elapsed = time.monotonic()-started
    print(json.dumps({"created_at_utc": datetime.now(timezone.utc).isoformat(), "target_requests_per_second": 5,
                      "attempts": 50, "elapsed_seconds": elapsed, "observed_requests_per_second": 50/elapsed,
                      "latency": distribution(timings), "errors": errors,
                      "scope": "actual Mongo alert API; shared Docker VM, single client, warm cache"}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())

"""Charge SQL SYNTHÉTIQUE en table temporaire, même jeu avant/après index ; rollback final."""

from datetime import datetime, timezone
import json
import math
import random
import statistics
import time

from rncp_bc1.api import connect_sql


def distribution(samples):
    ordered = sorted(samples)
    return {"p50_ms": statistics.median(samples), "p95_ms": ordered[math.ceil(.95*len(ordered))-1],
            "min_ms": ordered[0], "max_ms": ordered[-1], "queries": len(samples)}


def main():
    rng = random.Random(42)
    keys = [str(rng.randint(1, 100000)).zfill(64) for _ in range(50)]
    conn = connect_sql()
    try:
        conn.execute("CREATE TEMP TABLE benchmark_cases (case_id uuid PRIMARY KEY, transaction_id char(64) NOT NULL, status text NOT NULL CHECK (status='synthetic_test')) ON COMMIT DROP")
        begin = time.monotonic()
        conn.execute("INSERT INTO benchmark_cases SELECT gen_random_uuid(), lpad(n::text,64,'0'), 'synthetic_test' FROM generate_series(1,100000) n")
        insert_seconds = time.monotonic()-begin
        conn.execute("ANALYZE benchmark_cases")
        reports = {}
        for stage in ["without_transaction_index", "with_unique_transaction_index"]:
            if stage.startswith("with_unique"):
                conn.execute("CREATE UNIQUE INDEX ON benchmark_cases(transaction_id)")
                conn.execute("ANALYZE benchmark_cases")
            conn.execute("SELECT case_id FROM benchmark_cases WHERE transaction_id=%s", (keys[0],)).fetchall()
            timings = []
            for key in keys:
                begin = time.monotonic()
                rows = conn.execute("SELECT case_id FROM benchmark_cases WHERE transaction_id=%s", (key,)).fetchall()
                timings.append((time.monotonic()-begin)*1000)
                if len(rows) != 1:
                    raise AssertionError("Résultat SQL incorrect sous charge")
            plan = conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT case_id FROM benchmark_cases WHERE transaction_id=%s", (keys[0],)).fetchone()["QUERY PLAN"][0]
            reports[stage] = distribution(timings) | {"sample_plan": plan}
        integrity = conn.execute("SELECT count(*) AS rows, count(DISTINCT transaction_id) AS unique_transactions FROM benchmark_cases").fetchone()
        if integrity != {"rows": 100000, "unique_transactions": 100000}:
            raise AssertionError("Intégrité du jeu de charge altérée")
        report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "fixture": "SYNTHETIC_TEMPORARY_CASES_NOT_BUSINESS_DECISIONS",
                  "rows": 100000, "seed": 42, "insert_seconds": insert_seconds, "insert_rows_per_second": 100000/insert_seconds,
                  "integrity": integrity, "comparison": reports, "isolation": "temporary table; rollback; no persisted business rows",
                  "limitations": "single client, warm cache, loopback Docker network; not production capacity"}
    finally:
        conn.rollback()
        conn.close()
    print(json.dumps(report))


if __name__ == "__main__":
    main()

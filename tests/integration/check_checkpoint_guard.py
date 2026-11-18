"""Contrôle HDFS réel de fixtures explicitement synthétiques, sans suppression."""
import json
import uuid
from pyspark.sql import SparkSession
from rncp_bc1.streaming_state import guard_streaming_state

spark = SparkSession.builder.appName("bc1-checkpoint-preflight").getOrCreate()
spark.sparkContext.setLogLevel("WARN")
root = "hdfs://namenode:8020/bc1/checkpoint-contract-" + uuid.uuid4().hex
jvm = spark._jvm
Path = jvm.org.apache.hadoop.fs.Path
fs = Path(root).getFileSystem(spark._jsc.hadoopConfiguration())


def put(path, text):
    target = Path(path)
    fs.mkdirs(target.getParent())
    stream = fs.create(target, False)
    stream.write(bytearray(text.encode()))
    stream.close()


results = {}
try:
    guard_streaming_state(spark, root + "/new")
    results["empty_new_run_allowed"] = True
    for case, content in (("missing", None), ("corrupt", "not-json"), ("invalid-id", '{"id":"bad"}')):
        base = root + "/" + case
        put(base + "/curated/synthetic-fixture.txt", "explicit synthetic checkpoint precondition fixture")
        if content is not None:
            put(base + "/checkpoints/curated/metadata", content)
        try:
            guard_streaming_state(spark, base)
            raise AssertionError("Expected refusal " + case)
        except RuntimeError as error:
            results[case + "_refused"] = "refusée" in str(error)
        assert fs.getFileStatus(Path(base + "/curated/synthetic-fixture.txt")).getLen() == 50
    base = root + "/valid"
    put(base + "/curated/synthetic-fixture.txt", "synthetic fixture")
    put(base + "/checkpoints/curated/metadata", json.dumps({"id": str(uuid.uuid4())}))
    guard_streaming_state(spark, base)
    results["valid_metadata_allowed"] = True
    guard_streaming_state(spark, "hdfs://namenode:8020/bc1/runtime-v1")
    results["existing_real_run_allowed"] = True
    assert all(results.values())
    print(json.dumps({"event": "checkpoint_preflight_verified", "synthetic_fixture_root": root, "checks": results,
                      "scope": "preconditions only; Spark validates full offsets/state on resume; fixtures preserved"}))
finally:
    spark.stop()

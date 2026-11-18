from pyspark.sql import SparkSession
spark=SparkSession.builder.appName('BC1 authenticated encrypted RPC probe').getOrCreate()
sc=spark.sparkContext
assert sc.getConf().get('spark.authenticate')=='true'
assert sc.getConf().get('spark.network.crypto.enabled')=='true'
assert sc.getConf().get('spark.network.crypto.saslFallback')=='false'
assert sc.getConf().get('spark.io.encryption.enabled')=='true'
value=sc.parallelize(range(10000),8).map(lambda x:x*x).sum()
assert value==sum(x*x for x in range(10000))
print('BC1_SECURE_SPARK_RESULT='+str(value),flush=True)
spark.stop()

"""Preuve distribuée : vrai ticket Kerberos, autorisations HDFS et RPC Spark."""
import json
from pyspark.sql import SparkSession
spark=SparkSession.builder.appName('BC1 secure distributed lake boundary').getOrCreate()
sc=spark.sparkContext
try:
    conf=sc.getConf()
    for key,value in [('spark.authenticate','true'),('spark.network.crypto.enabled','true'),('spark.network.crypto.saslFallback','false')]:assert conf.get(key)==value,key
    ugi=sc._jvm.org.apache.hadoop.security.UserGroupInformation.getCurrentUser()
    assert str(ugi.getAuthenticationMethod())=='KERBEROS',str(ugi.getAuthenticationMethod())
    assert ugi.getUserName()=='alice@BC1.TEST'
    frame=spark.read.parquet('hdfs://namenode.bc1.test:8020/bc1/private/runtime-v1/curated')
    count=frame.count();assert count==1000,count
    executors=sc.parallelize(range(8),8).mapPartitions(lambda rows:[(__import__('socket').gethostname(),len(list(rows)))]).collect()
    assert all(host=='worker' for host,n in executors)
    assert frame.select('transaction_id').distinct().count()==1000
    print(json.dumps({'event':'secure_distributed_lake_verified','driver_principal':ugi.getUserName(),'authentication_method':str(ugi.getAuthenticationMethod()),'rows':count,'unique_transactions':1000,'executor_hosts':sorted({h for h,n in executors}),'spark_rpc_authentication':True,'spark_rpc_crypto_enabled':True,'sasl_fallback':False,'scope':'One trusted standalone worker, per-process Kerberos cache; no YARN token-renewal guarantee'}))
finally:spark.stop()

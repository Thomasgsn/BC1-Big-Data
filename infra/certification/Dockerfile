ARG SPARK_BASE=rncp-bc1-spark:3.5.8
FROM ${SPARK_BASE}
USER root
COPY requirements-runtime.txt /tmp/requirements-runtime.txt
RUN pip3 install --no-cache-dir --target /opt/bc1-deps --require-hashes -r /tmp/requirements-runtime.txt
ENV PYTHONPATH=/opt/bc1-deps:/project/src PYSPARK_PYTHON=python3 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /project
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends krb5-user && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 1000 --create-home --shell /bin/bash bc1
ENV HADOOP_CONF_DIR=/etc/bc1 KRB5_CONFIG=/etc/bc1/krb5.conf SPARK_CONF_DIR=/spark-auth
ENV KRB5CCNAME=FILE:/tmp/krb5cc_bc1 SPARK_LOG_DIR=/tmp/spark-logs SPARK_WORKER_DIR=/tmp/spark-work
ENV JAVA_TOOL_OPTIONS=-Djava.security.krb5.conf=/etc/bc1/krb5.conf
COPY infra/certification/CredentialBootstrap.java infra/certification/jars.lock.json infra/certification/patch_spark.py /opt/bc1-security/
RUN python3 /opt/bc1-security/patch_spark.py
RUN mkdir -p /opt/bc1-security/classes && javac --release 17 -cp "/opt/spark/jars/*" -d /opt/bc1-security/classes /opt/bc1-security/CredentialBootstrap.java
RUN apt-get update && apt-get purge -y --auto-remove build-essential gcc g++ linux-libc-dev libc6-dev dpkg-dev && rm -rf /var/lib/apt/lists/*
USER 1000:1000

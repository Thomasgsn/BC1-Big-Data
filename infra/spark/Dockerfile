ARG SPARK_IMAGE
FROM ${SPARK_IMAGE}
USER root
COPY requirements-runtime.txt /tmp/bc1-requirements.txt
RUN pip3 install --no-cache-dir --target /opt/bc1-deps --require-hashes -r /tmp/bc1-requirements.txt
ENV PYTHONPATH=/opt/bc1-deps:/project/src
ENV PYSPARK_PYTHON=python3
ENV HADOOP_USER_NAME=hadoop
ENV HADOOP_CONF_DIR=/project/infra/hadoop
ENV OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /project
USER 185

FROM apache/kafka:3.9.2@sha256:05b4616e0702ef2729327705d54ad6b50ea70b271c4b730fabd2320789fb7b02
USER root
RUN apk upgrade --no-cache && apk add --no-cache python3
COPY infra/certification/kafka-jars.lock.json /opt/bc1-security/jars.lock.json
COPY infra/certification/patch_spark.py /opt/bc1-security/patch_runtime.py
RUN BC1_JARS_DIRECTORY=/opt/kafka/libs python3 /opt/bc1-security/patch_runtime.py && apk del python3
USER 1000

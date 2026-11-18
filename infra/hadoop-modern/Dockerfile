# Le contexte de build contient uniquement l'archive acquise dans tmp/hadoop-modern.
ARG JAVA_IMAGE=eclipse-temurin:11-jre-noble@sha256:8f3fe814a88932ac679142aee0615a627b448e8a87c31dac279e538923870c84
FROM ${JAVA_IMAGE}
ARG HADOOP_SHA512=e25be7e57b4d3c5bfe83895844321a21d6cf7331266d524d8983c27cf484e576c3d79b3b60d590f8cddecf16229d0e232de2491b1b61b362ee7d67072c7290e1
USER root
RUN --mount=type=bind,source=hadoop-3.4.3.tar.gz,target=/tmp/hadoop.tar.gz \
    printf '%s  /tmp/hadoop.tar.gz\n' "$HADOOP_SHA512" | sha512sum -c - \
 && mkdir -p /opt/hadoop \
 && tar -xzf /tmp/hadoop.tar.gz --strip-components=1 -C /opt/hadoop \
 && if getent passwd 1000 >/dev/null; then \
      old_user="$(getent passwd 1000 | cut -d: -f1)"; \
      if [ "$old_user" != hadoop ]; then usermod -l hadoop -d /home/hadoop "$old_user"; fi; \
    else groupadd -g 1000 hadoop && useradd -u 1000 -g 1000 -d /home/hadoop hadoop; fi \
 && mkdir -p /home/hadoop /tmp/bc1-hadoop-logs \
 && chown 1000:1000 /home/hadoop /tmp/bc1-hadoop-logs
ENV HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/etc/bc1 \
    HADOOP_LOG_DIR=/tmp/bc1-hadoop-logs \
    HADOOP_PID_DIR=/tmp \
    HOME=/home/hadoop
ENV PATH=/opt/hadoop/bin:/opt/hadoop/sbin:${PATH}
WORKDIR /opt/hadoop
USER 1000:1000
CMD ["hdfs", "version"]

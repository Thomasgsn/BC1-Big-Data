FROM rncp-bc1-hadoop-secure:3.4.3 AS runtime
USER root
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends openssh-server psmisc netcat-openbsd \
 && rm -rf /var/lib/apt/lists/* /etc/ssh/ssh_host_* \
 && passwd -d hadoop
# Le compte n'accepte que la clé dédiée/commande forcée : aucun mot de passe SSH.
FROM maven:3.9.9-eclipse-temurin-17@sha256:f58d59b6273e785ac0a4477f6e9b5ba1d7731c75b906c0f7b34076f1851318cc AS compiler
COPY --from=runtime /opt/hadoop/share/hadoop/common /deps/common
COPY --from=runtime /opt/hadoop/share/hadoop/hdfs /deps/hdfs
COPY HaContinuityProbe.java /source/HaContinuityProbe.java
RUN javac --release 11 -cp '/deps/common/*:/deps/common/lib/*:/deps/hdfs/*:/deps/hdfs/lib/*' -d /classes /source/HaContinuityProbe.java
FROM runtime
COPY --from=compiler /classes /opt/bc1-ha/classes
USER 1000:1000

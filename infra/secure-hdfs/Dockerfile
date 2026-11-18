FROM rncp-bc1-hadoop:3.4.3-java11
USER root
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends krb5-kdc krb5-admin-server krb5-user openssl python3 \
 && rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1100 analysts \
 && useradd -u 1101 -g 1100 -M alice \
 && useradd -u 1102 -g 1100 -M bob
COPY jars.lock.json patch_jars.py /opt/bc1-build/
RUN python3 /opt/bc1-build/patch_jars.py
USER 1000:1000

FROM rncp-bc1-hadoop:3.4.3-java11
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-reportlab python3-pypdf python3-pil poppler-utils fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /project
USER 1000

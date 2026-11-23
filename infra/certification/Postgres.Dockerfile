FROM postgres:17-trixie@sha256:0d938e975177bef9f1f61f3f9dbcf2e0aa0a139568f66d3415ed8892eb97f6ac
USER root
RUN rm /usr/local/bin/gosu
USER 999:999

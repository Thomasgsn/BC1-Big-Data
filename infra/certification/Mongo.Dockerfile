FROM library/mongo:8.0@sha256:bdc216e9d5a6ec2cfdac789b5832fdab64cd32055f59885cae918a92de63c361
USER root
RUN rm /usr/local/bin/gosu
ENV HOME=/tmp
USER 999:999

ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/project/src
COPY requirements-api.lock /tmp/requirements-api.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-api.lock
WORKDIR /project
USER 10001:10001
ENTRYPOINT ["python", "-m", "uvicorn", "rncp_bc1.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]

FROM mcr.microsoft.com/playwright/python:v1.58.0-noble@sha256:678457c4c323b981d8b4befc57b95366bb1bb6aa30057b1269f6b171e8d9975a
RUN pip install --no-cache-dir playwright==1.58.0 \
 && python -c "import urllib.request; urllib.request.urlretrieve('https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.11.0/axe.min.js','/opt/axe.min.js')"
WORKDIR /project
ENTRYPOINT ["python", "/project/tests/integration/check_accessibility.py"]

#!/usr/bin/env bash
set -euo pipefail
# Logiciel client Gephi officiel dans un écran X11 isolé ; captures réelles, sans écran simulé.
echo '6ef1f1d4a16628ff2fb9e53b38bcccbbfc5f3ceed46f91b73d657556bcfc7773  /downloads/gephi.tar.gz' | sha256sum -c -
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xvfb openbox xdotool scrot libgl1-mesa-dri libgl1 libxrender1 libxtst6 libxi6 libasound2t64 fonts-dejavu-core
mkdir -p /work/software /exports/desktop
if [[ ! -x /work/software/gephi-0.11.4/bin/gephi ]]; then
  tar -xzf /downloads/gephi.tar.gz -C /work/software
fi
export DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1
Xvfb :99 -screen 0 1600x1000x24 -nolisten tcp >/work/xvfb.log 2>&1 &
for attempt in {1..50}; do
  if xdpyinfo >/dev/null 2>&1; then break; fi
  sleep .2
done
openbox >/work/openbox.log 2>&1 &
/work/software/gephi-0.11.4/bin/gephi --jdkhome "$JAVA_HOME" -J-Xmx1024m \
  --userdir /work/userdir --cachedir /work/cache \
  --open /exports/analysis/runtime-v1-desktop-project/five-components.gephi > /work/gephi.log 2>&1 &
application=$!
for stage in 1 2 3; do
  sleep 15
  scrot "/exports/desktop/gephi-stage-$stage.png"
  echo "Gephi desktop capture stage $stage recorded"
done
wait "$application"

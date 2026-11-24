#!/bin/bash
# Load test on the production VPS against a THROWAWAY copy of the live container:
# same image (agrisense:local), same 2 workers and 1.2 GB memory limit, its own empty database, no OTP e-mail.
# The live container and its database are not touched. Results land in /tmp/lt/.
set -u
cd /tmp/lt
NAME=agrisense-loadtest
cleanup() { kill "${SAMPLER:-0}" 2>/dev/null; docker rm -f $NAME >/dev/null 2>&1; }
trap cleanup EXIT

{ echo "cpu: $(lscpu | sed -n 's/^Model name:[ ]*//p')"; echo "vcpus: $(nproc)"; free -m | sed -n 2p;
  echo "image: $(docker inspect agrisense --format '{{.Config.Image}}')"; } > host.txt

docker rm -f $NAME >/dev/null 2>&1
docker run -d --name $NAME --memory 1200m -p 127.0.0.1:8159:8150 \
  -e AGRISENSE_STORAGE=/tmp/ltdata -e OTP_WEBHOOK_URL= agrisense:local >/dev/null
for i in $(seq 1 60); do curl -sf http://127.0.0.1:8159/healthz >/dev/null && break; sleep 2; done
echo "server up $(date +%T)"

docker exec -i $NAME python - < model_bench.py > bench.json
echo "bench done $(date +%T)"

# CPU % (of one core; 200% = both vCPUs) and memory of the test container, about once a second
( while true; do echo "$(date +%s.%N) $(docker stats --no-stream --format '{{.CPUPerc}} {{.MemUsage}}' $NAME)"; done ) > stats.txt &
SAMPLER=$!

chmod 777 /tmp/lt   # the generator container runs as a non-root user and writes load.json here
# the load generator gets at most half a core so the server keeps most of the machine
docker run --rm --network host --cpus 0.5 -v /tmp/lt:/lt agrisense:local \
  python /lt/loadtest.py --base http://127.0.0.1:8159 --out /lt/load.json > run.log 2>&1
echo "load done $(date +%T) exit=$?"

#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/root/httpmark}"
RESULTS="${RESULTS:-/root/results.json}"
ITERATIONS="${ITERATIONS:-30}"
ROUNDS="${ROUNDS:-3}"
TIME_BUDGET="${TIME_BUDGET:-60}"

cd "$REPO_DIR"

if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
fi
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq libcurl4-openssl-dev build-essential >/dev/null
fi

grep -q "httpbin.local" /etc/hosts || echo "127.0.0.1   httpbin.local" >> /etc/hosts

[ -f certs/ca.crt ] || bash certs/generate.sh

for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [ -w "$gov" ] && echo performance > "$gov" || true
done

declare -A CORE_CPUS
while IFS=, read -r cpu core; do
    CORE_CPUS[$core]+="$cpu "
done < <(lscpu -p=CPU,CORE | grep -v '^#')
CORE_IDS=($(printf '%s\n' "${!CORE_CPUS[@]}" | sort -n))
NCORES=${#CORE_IDS[@]}

AFFINITY_ARGS=()
COMPOSE_ARGS=(-f docker-compose.yml)
if [ "$NCORES" -ge 4 ]; then
    HALF=$((NCORES / 2))
    SERVER_LIST=""
    CLIENT_LIST=""
    for i in "${!CORE_IDS[@]}"; do
        cpus=(${CORE_CPUS[${CORE_IDS[$i]}]})
        if [ "$i" -lt "$HALF" ]; then
            SERVER_LIST+="${cpus[*]} "
        else
            CLIENT_LIST+="${cpus[0]} "
        fi
    done
    export SERVER_CPUSET=$(echo $SERVER_LIST | tr ' ' ',')
    CLIENT_CPUSET=$(echo $CLIENT_LIST | tr ' ' ',')
    COMPOSE_ARGS+=(-f docker-compose.pinning.yml)
    AFFINITY_ARGS=(--cpu-affinity "$CLIENT_CPUSET")
    echo "physical cores: $NCORES — server on cpus $SERVER_CPUSET (all threads), client on cpus $CLIENT_CPUSET (one thread per core)"
else
    echo "physical cores: $NCORES — too few for pinning, running unpinned"
fi

docker compose "${COMPOSE_ARGS[@]}" up -d
for _ in $(seq 1 30); do
    curl -s --cacert certs/ca.crt --max-time 2 https://httpbin.local:4443/get -o /dev/null && break
    sleep 2
done

uv sync
uv run httpmark \
    --iterations "$ITERATIONS" \
    --rounds "$ROUNDS" \
    --time-budget "$TIME_BUDGET" \
    --shuffle \
    "${AFFINITY_ARGS[@]}" \
    --output "$RESULTS"

echo "===RESULTS-JSON-BEGIN==="
cat "$RESULTS"
echo "===RESULTS-JSON-END==="

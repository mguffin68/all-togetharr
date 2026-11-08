#!/usr/bin/env bash
# Task 17b integration check for the Docker image.
# Usage: docker/test_image.sh [--multiarch]
# Builds the image, runs it as PUID/PGID 1234 with UMASK 027, and checks
# health, the SPA, file ownership, JSON-only logs and a clean stop.
set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE=all-togetharr:test
NAME=all-togetharr-test-$$
CONFIG_VOL=$NAME-config
DATA_VOL=$NAME-data
PORT=${PORT:-18080}
failures=0

pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*"; failures=$((failures + 1)); }

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker volume rm -f "$CONFIG_VOL" "$DATA_VOL" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker build -f docker/Dockerfile -t "$IMAGE" .

docker run -d --name "$NAME" \
  -e PUID=1234 -e PGID=1234 -e UMASK=027 \
  -v "$CONFIG_VOL:/config" -v "$DATA_VOL:/data" \
  -p "127.0.0.1:$PORT:8080" \
  "$IMAGE" >/dev/null

# Wait for Docker's own health check to pass.
status=starting
for _ in $(seq 1 90); do
  status=$(docker inspect -f '{{.State.Health.Status}}' "$NAME" 2>/dev/null || echo none)
  [ "$status" = healthy ] && break
  [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" = true ] || break
  sleep 1
done
[ "$status" = healthy ] && pass "health check reports healthy" || fail "health status is '$status'"

health=$(curl -fsS "http://127.0.0.1:$PORT/api/health" || true)
echo "$health" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["status"]=="ok"' \
  && pass "/api/health is ok" || fail "/api/health returned: $health"

curl -fsS "http://127.0.0.1:$PORT/" | grep -q '<div id="root">' \
  && pass "/ serves the SPA" || fail "/ does not serve the SPA"

curl -fsS "http://127.0.0.1:$PORT/titles/1" | grep -q '<div id="root">' \
  && pass "client routes fall back to the SPA" || fail "/titles/1 does not serve the SPA"

asset=$(curl -fsS "http://127.0.0.1:$PORT/" | grep -o '/assets/[^"]*\.js' | head -1)
[ -n "$asset" ] && curl -fsS -o /dev/null "http://127.0.0.1:$PORT$asset" \
  && pass "built JS asset is served" || fail "built JS asset '$asset' not served"

uid=$(docker exec "$NAME" awk '/^Uid:/{print $2}' /proc/1/status)
gid=$(docker exec "$NAME" awk '/^Gid:/{print $2}' /proc/1/status)
[ "$uid" = 1234 ] && [ "$gid" = 1234 ] \
  && pass "app runs as 1234:1234" || fail "app runs as $uid:$gid"

owner=$(docker exec "$NAME" stat -c '%u:%g %a' /config/all-togetharr.db)
[ "$owner" = "1234:1234 640" ] \
  && pass "database owned by 1234:1234 with mode 640" || fail "database is '$owner'"

data_owner=$(docker exec "$NAME" stat -c '%u:%g' /data)
[ "$data_owner" = "1234:1234" ] \
  && pass "/data owned by 1234:1234" || fail "/data is '$data_owner'"

start=$(date +%s)
docker stop -t 15 "$NAME" >/dev/null
elapsed=$(( $(date +%s) - start ))
code=$(docker inspect -f '{{.State.ExitCode}}' "$NAME")
[ "$code" = 0 ] && [ "$elapsed" -lt 10 ] \
  && pass "stops cleanly in ${elapsed}s" || fail "stop took ${elapsed}s with exit code $code"

LOG=$(mktemp)
docker logs "$NAME" > "$LOG" 2>&1
if python3 - "$LOG" <<'PY'
import json, sys
bad = []
lines = [l for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
for n, line in enumerate(lines, 1):
    try:
        if not isinstance(json.loads(line), dict):
            bad.append((n, line))
    except ValueError:
        bad.append((n, line))
for n, line in bad[:5]:
    print(f"  line {n}: {line.rstrip()[:200]}")
sys.exit(1 if bad or not lines else 0)
PY
then pass "every log line is a JSON object"; else fail "non-JSON log lines (above)"; fi
rm -f "$LOG"

for bad in "PUID=abc" "PGID=-1" "UMASK=xyz" "UMASK=0999"; do
  set +e
  out=$(docker run --rm -e "$bad" "$IMAGE" 2>&1)
  rc=$?
  set -e
  if [ "$rc" != 0 ] && [ "$(printf '%s\n' "$out" | wc -l)" = 1 ] \
    && printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["level"]=="ERROR"'; then
    pass "rejects $bad with one JSON error line"
  else
    fail "$bad: exit $rc, output: $out"
  fi
done

if [ "${1:-}" = --multiarch ]; then
  docker buildx build --platform linux/amd64,linux/arm64 -f docker/Dockerfile . \
    && pass "builds for amd64 and arm64" || fail "multi-arch build failed"
fi

echo
[ "$failures" = 0 ] && echo "ALL CHECKS PASSED" || echo "$failures CHECK(S) FAILED"
exit "$failures"

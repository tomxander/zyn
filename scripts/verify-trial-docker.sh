#!/usr/bin/env bash
# End-to-end verification script for Zyn Team Server trial compose on Linux Docker hosts.
# Run from repository root: ./scripts/verify-trial-docker.sh

set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT_NAME="zyn-verify-$$"
COMPOSE_FILE="compose.trial.yaml"
TRIAL_REALM_URL="http://localhost:8080/realms/zyn-trial"
APP_URL="http://localhost:8600"
MAX_WAIT_SECONDS=90

echo "=== Zyn Trial Compose Verification (Project: ${PROJECT_NAME}) ==="

# 1. Prerequisite checks
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is not installed"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: docker compose is not available"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is not installed"; exit 1; }

# Cleanup on exit
COOKIE_FILE=""
cleanup() {
    echo ""
    echo "=== Cleaning up trial containers and volumes ==="
    docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" down -v --remove-orphans || true
    rm -f cookies.txt login_page.html "${COOKIE_FILE}"
}
trap cleanup EXIT

# 2. Syntax validation
echo "[1/6] Validating compose configuration syntax..."
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" config >/dev/null
echo "  OK: Compose syntax valid."

# 3. Build images
echo "[2/6] Building images with docker compose..."
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" build
echo "  OK: Images built successfully."

# 4. Start containers
echo "[3/6] Starting services in background..."
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" up -d
echo "  OK: Containers started."

# 5. Wait for services to become healthy
echo "[4/6] Waiting for services (db, upgrade, keycloak, zyn)..."

# Wait for DB
echo "  Waiting for PostgreSQL (db)..."
elapsed=0
until docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ps db | grep -q "(healthy)"; do
    if [ "$elapsed" -ge "$MAX_WAIT_SECONDS" ]; then
        echo "ERROR: PostgreSQL failed to become healthy within ${MAX_WAIT_SECONDS}s"
        docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs db
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo "  OK: PostgreSQL is healthy."

# Wait for Upgrade migration
echo "  Waiting for schema upgrade (upgrade)..."
elapsed=0
until [ "$(docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" ps -a --filter "status=exited" --format '{{.ExitCode}}' upgrade 2>/dev/null || true)" = "0" ]; do
    if [ "$elapsed" -ge "$MAX_WAIT_SECONDS" ]; then
        echo "ERROR: Schema upgrade failed to complete successfully within ${MAX_WAIT_SECONDS}s"
        docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs upgrade
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo "  OK: Schema upgrade completed with exit code 0."

# Wait for Keycloak
echo "  Waiting for Keycloak (${TRIAL_REALM_URL})..."
elapsed=0
until curl -s -f "${TRIAL_REALM_URL}/.well-known/openid-configuration" >/dev/null 2>&1; do
    if [ "$elapsed" -ge "$MAX_WAIT_SECONDS" ]; then
        echo "ERROR: Keycloak failed to become ready within ${MAX_WAIT_SECONDS}s"
        docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs keycloak
        exit 1
    fi
    sleep 3
    elapsed=$((elapsed + 3))
done
echo "  OK: Keycloak realm discovery responding."

# Wait for Zyn
echo "  Waiting for Zyn (${APP_URL}/api/health)..."
elapsed=0
until curl -s -f "${APP_URL}/api/health" >/dev/null 2>&1; do
    if [ "$elapsed" -ge "$MAX_WAIT_SECONDS" ]; then
        echo "ERROR: Zyn server failed to become ready within ${MAX_WAIT_SECONDS}s"
        docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs zyn
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
echo "  OK: Zyn team server responding."

# 6. Functional verification
echo "[5/6] Performing live functional checks..."

# Check Zyn health response
HEALTH_RESP=$(curl -s "${APP_URL}/api/health")
echo "  Health response: ${HEALTH_RESP}"
if [[ "${HEALTH_RESP}" != *"\"status\":\"ok\""* && "${HEALTH_RESP}" != *"\"status\": \"ok\""* ]]; then
    echo "ERROR: Unexpected health response"
    exit 1
fi

# Check Login redirect to Keycloak and perform interactive OIDC PKCE sign-in flow (H4, J5)
COOKIE_FILE=$(mktemp)

LOGIN_INIT=$(curl -s -i -c "${COOKIE_FILE}" "${APP_URL}/auth/login" | tr -d '\r')
if ! echo "${LOGIN_INIT}" | grep -q -i "Location: http://localhost:8080/realms/zyn-trial/protocol/openid-connect/auth"; then
    echo "ERROR: Expected redirect to Keycloak trial realm. Headers:"
    echo "${LOGIN_INIT}"
    exit 1
fi
echo "  OK: /auth/login initiates PKCE redirect to Keycloak."

echo "  Performing interactive OIDC PKCE sign-in flow..."
AUTH_URL=$(echo "${LOGIN_INIT}" | grep -i "^location:" | head -n1 | awk '{print $2}')
LOGIN_PAGE=$(curl -s -L -b "${COOKIE_FILE}" -c "${COOKIE_FILE}" "${AUTH_URL}")
FORM_ACTION=$(echo "${LOGIN_PAGE}" | grep -o 'action="[^"]*"' | head -n1 | cut -d'"' -f2 | sed 's/&amp;/&/g')

if [ -z "${FORM_ACTION}" ]; then
    echo "ERROR: Could not find login form action URL in Keycloak page."
    exit 1
fi

LOGIN_POST=$(curl -s -i -b "${COOKIE_FILE}" -c "${COOKIE_FILE}" \
    --data-urlencode "username=alice" \
    --data-urlencode "password=alice123" \
    "${FORM_ACTION}" | tr -d '\r')

CALLBACK_URL=$(echo "${LOGIN_POST}" | grep -i "^location:" | head -n1 | awk '{print $2}')
if [ -z "${CALLBACK_URL}" ] || [[ "${CALLBACK_URL}" != *"/auth/callback"* ]]; then
    echo "ERROR: Keycloak login post did not return redirect to /auth/callback. Response:"
    echo "${LOGIN_POST}"
    exit 1
fi

CALLBACK_RESP=$(curl -s -i -L -b "${COOKIE_FILE}" -c "${COOKIE_FILE}" "${CALLBACK_URL}" | tr -d '\r')
CONFIG_RESP=$(curl -s -b "${COOKIE_FILE}" "${APP_URL}/api/config")

if [[ "${CONFIG_RESP}" != *"\"person\":"* || "${CONFIG_RESP}" != *"Alice"* ]]; then
    echo "ERROR: Signed-in API did not return person Alice. Response:"
    echo "${CONFIG_RESP}"
    exit 1
fi

PYTHON_BIN=$(command -v python3 || command -v python || true)
if [ -n "${PYTHON_BIN}" ]; then
    if ! "${PYTHON_BIN}" -c "import json, sys; d = json.loads(sys.argv[1]); sys.exit(0 if any(p.get('id') == 'bcm' and p.get('role') == 'approver' for p in d.get('projects', [])) else 1)" "${CONFIG_RESP}"; then
        echo "ERROR: bcm project does not carry approver role in config response: ${CONFIG_RESP}"
        exit 1
    fi
elif command -v jq >/dev/null 2>&1; then
    if ! echo "${CONFIG_RESP}" | jq -e '.projects[] | select(.id=="bcm" and .role=="approver")' >/dev/null; then
        echo "ERROR: bcm project does not carry approver role in config response: ${CONFIG_RESP}"
        exit 1
    fi
else
    if [[ "${CONFIG_RESP}" != *"\"bcm\""* || "${CONFIG_RESP}" != *"\"approver\""* ]]; then
        echo "ERROR: Signed-in API did not return project bcm with approver role. Response: ${CONFIG_RESP}"
        exit 1
    fi
fi
echo "  OK: Full interactive OIDC sign-in completed; verified person, project bcm, and approver role."

# Check Keycloak direct grant token exchange (H6)
TOKEN_RESP=$(curl -s -X POST "${TRIAL_REALM_URL}/protocol/openid-connect/token" \
    -d "client_id=zyn-app" \
    -d "client_secret=zyn-trial-client-secret" \
    -d "grant_type=password" \
    -d "username=alice" \
    -d "password=alice123" \
    -d "scope=openid profile email")

if [[ "${TOKEN_RESP}" != *"access_token"* ]]; then
    echo "ERROR: Direct token exchange failed for trial user alice:"
    echo "${TOKEN_RESP}"
    exit 1
fi
echo "  OK: Direct token grant succeeded for user 'alice' in realm 'zyn-trial'."

# Check DB schema table
SCHEMA_COUNT=$(docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" exec -T db psql -U zyn_admin -d zyn -t -A -c "SELECT count(*) FROM schema_versions;")
echo "  Schema migrations applied: ${SCHEMA_COUNT} versions."
if [ "${SCHEMA_COUNT}" -lt 1 ]; then
    echo "ERROR: No schema versions found in PostgreSQL database."
    exit 1
fi

echo "[6/6] All trial checks passed!"
echo "=== Zyn Team Server Trial verified successfully! ==="

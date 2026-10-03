#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost}"
BASE_URL="${BASE_URL%/}"
DEMO_MODE="${DEMO_MODE:-false}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

request() {
  local name="$1" expected="$2" url="$3"; shift 3
  local code
  code="$(curl -sS -o "$TMP_DIR/body" -w '%{http_code}' "$@" "$url")"
  if [[ ! ",$expected," =~ ,$code, ]]; then
    echo "FAIL $name: expected $expected, received $code" >&2
    sed -n '1,5p' "$TMP_DIR/body" >&2
    exit 1
  fi
  echo "PASS $name ($code)"
}

login_token() {
  local email="$1" password="$2"
  curl -fsS -H 'Content-Type: application/json' -d "{\"email\":\"$email\",\"password\":\"$password\"}" "$BASE_URL/api/v1/auth/login" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
}

request "landing" "200" "$BASE_URL/"
cp "$TMP_DIR/body" "$TMP_DIR/landing"
request "backend liveness" "200" "$BASE_URL/api/v1/health/live"
request "backend readiness" "200" "$BASE_URL/api/v1/health/ready"
request "public trust summary" "200" "$BASE_URL/api/v1/public/trust-summary"
python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "registered_users", "active_users", "active_merchants", "active_outlets",
    "payments_checked", "verified_payments", "verification_rate", "updated_at",
}
assert required.issubset(data)
assert data["registered_users"] >= 0
assert data["active_users"] <= data["registered_users"]
assert data["verified_payments"] <= data["payments_checked"]
assert 0 <= data["verification_rate"] <= 100
print("PASS public anonymous database aggregates")
PY
request "unauthorized audit" "401,403" "$BASE_URL/api/v1/audit-logs"
request "frontend health" "200" "$BASE_URL/healthz"

asset="$(grep -oE '/_next/static/[^" ]+\.js' "$TMP_DIR/landing" | head -1 || true)"
if [[ -n "$asset" ]]; then request "Next.js static asset" "200" "$BASE_URL$asset"; else echo "FAIL no Next.js asset found" >&2; exit 1; fi

if [[ "$DEMO_MODE" == "true" ]]; then
  merchant_token="$(login_token "${DEMO_MERCHANT_EMAIL:-merchant@fingraph.id}" "${DEMO_PASSWORD:-password123}")"
  request "merchant me" "200" "$BASE_URL/api/v1/auth/me" -H "Authorization: Bearer $merchant_token"
  python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["subscription_plan"] == "premium"
assert data["subscription"]["monthly_price"] == 149000
print("PASS demo merchant premium entitlement")
PY
  request "merchant subscription catalog" "200" "$BASE_URL/api/v1/merchants/subscription" -H "Authorization: Bearer $merchant_token"
  python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["current"]["code"] == "premium"
assert data["checkout_available"] is False
assert data["demo_change_available"] is True
print("PASS subscription catalog without fake checkout")
PY
  request "merchant dashboard" "200" "$BASE_URL/api/v1/merchants/dashboard" -H "Authorization: Bearer $merchant_token"
  request "merchant impact dashboard" "200" "$BASE_URL/api/v1/reports/impact-dashboard?period=30d&limit=5" -H "Authorization: Bearer $merchant_token"
  python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["metrics"]["payment_count"] == data["total"]
assert len(data["items"]) <= 5
assert all(item["category"] and item["priority"] in {"rendah", "sedang", "tinggi"} for item in data["items"])
print("PASS impact aggregation and explicit category/priority")
PY
  request "merchant payments" "200" "$BASE_URL/api/v1/payments?limit=1" -H "Authorization: Bearer $merchant_token"
  cp "$TMP_DIR/body" "$TMP_DIR/merchant-payments"
  python3 - "$TMP_DIR/merchant-payments" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["limit"] == 1 and len(data["items"]) <= 1
assert data["total"] >= len(data["items"]) and data["page"] == 1
print("PASS server-side payment pagination metadata")
PY
  payment_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["items"][0]["id"])' "$TMP_DIR/merchant-payments")"
  second_merchant_token="$(login_token "${DEMO_SECOND_MERCHANT_EMAIL:-batik@fingraph.id}" "${DEMO_PASSWORD:-password123}")"
  request "merchant ownership isolation" "404" "$BASE_URL/api/v1/payments/$payment_id" -H "Authorization: Bearer $second_merchant_token"

  analyst_token="$(login_token "${DEMO_ANALYST_EMAIL:-analyst@fingraph.id}" "${DEMO_PASSWORD:-password123}")"
  request "analyst merchant subscription denied" "403" "$BASE_URL/api/v1/merchants/subscription" -H "Authorization: Bearer $analyst_token"
  request "merchant admin monitoring denied" "403" "$BASE_URL/api/v1/admin/activity-monitoring" -H "Authorization: Bearer $merchant_token"
  request "analyst admin monitoring denied" "403" "$BASE_URL/api/v1/admin/activity-monitoring" -H "Authorization: Bearer $analyst_token"
  request "analyst overview" "200" "$BASE_URL/api/v1/dashboard/summary" -H "Authorization: Bearer $analyst_token"
  request "audit pagination" "200" "$BASE_URL/api/v1/audit-logs?limit=2&offset=0&ordering=newest" -H "Authorization: Bearer $analyst_token"
  python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["limit"] == 2 and len(data["items"]) <= 2 and data["offset"] == 0
print("PASS server-side audit pagination metadata")
PY
  request "analyst graph" "200" "$BASE_URL/api/v1/graph?limit=10" -H "Authorization: Bearer $analyst_token"
  python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["returned_nodes"] <= 10, data["returned_nodes"]
assert all(edge["source"] in {n["id"] for n in data["nodes"]} and edge["target"] in {n["id"] for n in data["nodes"]} for edge in data["edges"])
print("PASS graph limit and edge integrity")
PY
  request "cross-border route semantics" "200" "$BASE_URL/api/v1/cross-border/routes?limit=100" -H "Authorization: Bearer $analyst_token"
  python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for route in data["items"]:
    assert route["route_status"] in {"normal", "monitor", "high"}
    assert "high_risk_rate" in route and "status_reason" in route
    assert not (route["average_fraud_score"] < .4 and route["high_risk_count"] == 0 and route["route_status"] == "high")
print("PASS cross-border status semantics")
PY
  admin_token="$(login_token "${DEMO_ADMIN_EMAIL:-admin@fingraph.id}" "${DEMO_PASSWORD:-password123}")"
  request "admin activity monitoring" "200" "$BASE_URL/api/v1/admin/activity-monitoring?period=30d" -H "Authorization: Bearer $admin_token"
  python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["total_users"] >= 3
assert set(("merchant", "analyst", "admin")).issubset(data["activity_by_role"])
assert data["active_window_minutes"] == 15
print("PASS admin activity monitoring metrics")
PY
  request "admin merchant-role filter" "200" "$BASE_URL/api/v1/admin/activity-monitoring?period=30d&role=merchant" -H "Authorization: Bearer $admin_token"
  python3 - "$TMP_DIR/body" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["activity_by_role"]["analyst"] == 0
assert data["activity_by_role"]["admin"] == 0
assert all(item["actor_role"] == "merchant" for item in data["recent_activities"])
print("PASS admin period and role filters")
PY
else
  request "production demo mutation disabled" "404" "$BASE_URL/api/v1/demo/qris/scenarios/normal_payment" -X POST
  request "production API docs disabled" "404" "$BASE_URL/docs"
  request "production registration disabled" "403" "$BASE_URL/api/v1/auth/register" \
    -H 'Content-Type: application/json' \
    -d '{"full_name":"Smoke Test","email":"smoke-registration@example.com","password":"not-used-password","role":"merchant"}'
fi

echo "Smoke test complete for $BASE_URL (DEMO_MODE=$DEMO_MODE)."

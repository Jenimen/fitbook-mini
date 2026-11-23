#!/usr/bin/env bash
# Smoke teszt a telepített alkalmazásra: végigjátssza a fő üzleti folyamatot.
# Használat: ./scripts/smoke_test.sh [BASE_URL]
set -euo pipefail
BASE_URL="${1:-http://localhost:8000}"

echo "1) Várakozás, amíg az alkalmazás elindul..."
for i in $(seq 1 30); do
  if curl -fs "$BASE_URL/health" > /dev/null; then break; fi
  sleep 1
  if [ "$i" -eq 30 ]; then echo "HIBA: az alkalmazás nem indult el"; exit 1; fi
done
curl -fs "$BASE_URL/health"; echo

echo "2) Admin létrehoz egy 1 fős órát"
SESSION_ID=$(curl -fs -X POST "$BASE_URL/sessions" -H "X-Role: admin" -H "Content-Type: application/json" \
  -d '{"name":"Smoke jóga","trainer":"Anna","starts_at":"2026-12-20T18:00:00","capacity":1}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "   óra id: $SESSION_ID"

echo "3) Béla foglal (ACTIVE), Cili várólistára kerül (WAITLISTED)"
B1=$(curl -fs -X POST "$BASE_URL/sessions/$SESSION_ID/bookings" -H "Content-Type: application/json" -d '{"member":"Bela"}')
B2=$(curl -fs -X POST "$BASE_URL/sessions/$SESSION_ID/bookings" -H "Content-Type: application/json" -d '{"member":"Cili"}')
echo "$B1" | grep -q '"ACTIVE"' || { echo "HIBA: Béla nem ACTIVE"; exit 1; }
echo "$B2" | grep -q '"WAITLISTED"' || { echo "HIBA: Cili nem WAITLISTED"; exit 1; }
B1_ID=$(echo "$B1" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "4) Béla lemond -> Cili automatikusan bekerül"
curl -fs -X DELETE "$BASE_URL/bookings/$B1_ID" | grep -q '"promoted":[0-9]' || { echo "HIBA: nem történt előléptetés"; exit 1; }

echo "OK: minden smoke teszt sikeres, az alkalmazás üzleti funkciói elérhetők."

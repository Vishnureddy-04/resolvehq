#!/bin/bash
# Quick API testing script with curl

API_URL="http://localhost:5000/api"

echo "=== ResolveHQ API Testing ==="
echo ""

# 1. LOGIN (customer)
echo "1. Customer Login..."
CUSTOMER_TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"customer@acme.com","password":"demo1234"}' | jq -r '.access_token')
echo "Token: $CUSTOMER_TOKEN"
echo ""

# 2. LOGIN (company)
echo "2. Company Login..."
COMPANY_TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"agent@resolvehq.com","password":"demo1234"}' | jq -r '.access_token')
echo "Token: $COMPANY_TOKEN"
echo ""

# 3. GET CURRENT USER
echo "3. Get Current User (customer)..."
curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" | jq '.'
echo ""

# 4. GET CUSTOMER'S TICKETS
echo "4. Get Customer Tickets..."
curl -s -X GET "$API_URL/tickets" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" | jq '.' | head -20
echo ""

# 5. GET ALL TICKETS (company)
echo "5. Get All Tickets (company)..."
curl -s -X GET "$API_URL/tickets?status=open" \
  -H "Authorization: Bearer $COMPANY_TOKEN" | jq '.' | head -20
echo ""

# 6. GET SINGLE TICKET
echo "6. Get Single Ticket..."
curl -s -X GET "$API_URL/tickets/TKT-3001" \
  -H "Authorization: Bearer $COMPANY_TOKEN" | jq '.'
echo ""

# 7. UPDATE TICKET (company)
echo "7. Update Ticket Priority..."
curl -s -X PATCH "$API_URL/tickets/TKT-3003" \
  -H "Authorization: Bearer $COMPANY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"priority":"P1","assigned_team":"Engineering"}' | jq '.'
echo ""

# 8. GET DASHBOARD
echo "8. Get Company Dashboard..."
curl -s -X GET "$API_URL/analytics/dashboard" \
  -H "Authorization: Bearer $COMPANY_TOKEN" | jq '.'
echo ""

# 9. GET METRICS
echo "9. Get Analytics Metrics..."
curl -s -X GET "$API_URL/analytics/metrics?days=90" \
  -H "Authorization: Bearer $COMPANY_TOKEN" | jq '.'
echo ""

# 10. GET TEAM WORKLOAD
echo "10. Get Team Workload..."
curl -s -X GET "$API_URL/analytics/team-workload" \
  -H "Authorization: Bearer $COMPANY_TOKEN" | jq '.'
echo ""

# 11. GET RECURRING ISSUES
echo "11. Get Recurring Issues..."
curl -s -X GET "$API_URL/analytics/recurring" \
  -H "Authorization: Bearer $COMPANY_TOKEN" | jq '.'
echo ""

echo "=== Test Complete ==="

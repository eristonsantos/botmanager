#!/bin/bash

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000/api/v1"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4N2Q2M2Y0OC04M2Y5LTQyYWUtOTQ0Ni04OGEwMDAzOGUwOWQiLCJ0ZW5hbnRfaWQiOiIxMTM4NTIzOS0xMGE2LTQ4MDgtYWZhYi1iNTgxNjY2NTVjNjYiLCJlbWFpbCI6InRlc3QtOWVlMDFiYjlAZXhhbXBsZS5jb20iLCJpc19zdXBlcnVzZXIiOmZhbHNlLCJleHAiOjE3NjUzMzk5NjcsImlhdCI6MTc2NTMzODE2NywidHlwZSI6ImFjY2VzcyJ9.Y5gGtZvyVcWF_bCXsHtuY8xCEJZw6Cm2lbfv4652i5Q"

print_test() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# TEST 1: Create Agent
print_test "TEST 1: POST /agents - Create New Agent"
AGENT_NAME="Agent-$(date +%s%N | cut -b1-13)"
echo "Creating agent: $AGENT_NAME"

RESPONSE=$(curl -s -X POST "$BASE_URL/agents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"name\":\"$AGENT_NAME\",\"machine_name\":\"m-001\",\"ip_address\":\"192.168.1.50\",\"version\":\"1.2.3\",\"capabilities\":[\"web\",\"excel\"]}")

AGENT_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ ! -z "$AGENT_ID" ]; then
    print_success "Agent created: $AGENT_ID"
    echo "Response: $RESPONSE" | head -c 200
    echo ""
else
    print_error "Failed to create agent"
    echo "Response: $RESPONSE" | head -c 300
    echo ""
fi

# TEST 2: Get Agent
if [ ! -z "$AGENT_ID" ]; then
    print_test "TEST 2: GET /agents/{id} - Retrieve Agent"
    RESPONSE=$(curl -s -X GET "$BASE_URL/agents/$AGENT_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    NAME=$(echo "$RESPONSE" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ "$NAME" = "$AGENT_NAME" ]; then
        print_success "Agent retrieved: $NAME"
    else
        print_error "Failed to retrieve agent"
        echo "Response: $RESPONSE" | head -c 200
    fi
fi

# TEST 3: List Agents
print_test "TEST 3: GET /agents - List Agents"
RESPONSE=$(curl -s -X GET "$BASE_URL/agents?page=1&size=5" \
  -H "Authorization: Bearer $TOKEN")

TOTAL=$(echo "$RESPONSE" | grep -o '"total":[0-9]*' | cut -d':' -f2)

if [ ! -z "$TOTAL" ]; then
    print_success "Listed agents (total: $TOTAL)"
    echo "First 200 chars: "
    echo "$RESPONSE" | head -c 200
    echo ""
else
    print_error "Failed to list agents"
    echo "Response: $RESPONSE" | head -c 200
fi

# TEST 4: Update Agent
if [ ! -z "$AGENT_ID" ]; then
    print_test "TEST 4: PUT /agents/{id} - Update Agent"
    NEW_NAME="Updated-$AGENT_NAME"
    
    RESPONSE=$(curl -s -X PUT "$BASE_URL/agents/$AGENT_ID" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "{\"name\":\"$NEW_NAME\",\"ip_address\":\"192.168.1.100\"}")
    
    UPDATED_NAME=$(echo "$RESPONSE" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ "$UPDATED_NAME" = "$NEW_NAME" ]; then
        print_success "Agent updated: $UPDATED_NAME"
    else
        print_error "Failed to update agent"
        echo "Response: $RESPONSE" | head -c 200
    fi
fi

# TEST 5: Heartbeat
if [ ! -z "$AGENT_ID" ]; then
    print_test "TEST 5: POST /agents/{id}/heartbeat - Record Heartbeat"
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/agents/$AGENT_ID/heartbeat" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{"status":"online","extra_data":{"cpu":45.2,"memory":62.1}}')
    
    STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ "$STATUS" = "online" ]; then
        print_success "Heartbeat recorded: $STATUS"
    else
        print_error "Failed to record heartbeat"
        echo "Response: $RESPONSE" | head -c 200
    fi
fi

# TEST 6: Delete Agent
if [ ! -z "$AGENT_ID" ]; then
    print_test "TEST 6: DELETE /agents/{id} - Delete Agent"
    
    RESPONSE=$(curl -s -X DELETE "$BASE_URL/agents/$AGENT_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    if echo "$RESPONSE" | grep -q "sucesso\|deleted\|message"; then
        print_success "Agent deleted successfully"
    else
        print_error "Failed to delete agent"
        echo "Response: $RESPONSE" | head -c 200
    fi
fi

print_test "ALL TESTS COMPLETED"
echo -e "${GREEN}✓ Agents API validation complete!${NC}\n"

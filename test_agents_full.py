#!/usr/bin/env python3
"""
Teste direto da API agents sem servidor rodando.
Usando cliente HTTP para validar endpoints.
"""

import json
import sys

# Test token (válido por 30 minutos)
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4N2Q2M2Y0OC04M2Y5LTQyYWUtOTQ0Ni04OGEwMDAzOGUwOWQiLCJ0ZW5hbnRfaWQiOiIxMTM4NTIzOS0xMGE2LTQ4MDgtYWZhYi1iNTgxNjY2NTVjNjYiLCJlbWFpbCI6InRlc3QtOWVlMDFiYjlAZXhhbXBsZS5jb20iLCJpc19zdXBlcnVzZXIiOmZhbHNlLCJleHAiOjE3NjUzMzk5NjcsImlhdCI6MTc2NTMzODE2NywidHlwZSI6ImFjY2VzcyJ9.Y5gGtZvyVcWF_bCXsHtuY8xCEJZw6Cm2lbfv4652i5Q"
BASE_URL = "http://localhost:8000/api/v1"

import requests
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test(name):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{name}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.ENDC} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.ENDC} {msg}")

def print_info(msg):
    print(f"{Colors.CYAN}ℹ{Colors.ENDC} {msg}")

# Test 1: Create Agent
print_test("TEST 1: POST /agents - Create New Agent")
agent_name = f"Agent-{datetime.now().timestamp():.0f}"
create_payload = {
    "name": agent_name,
    "machine_name": "machine-test-001",
    "ip_address": "192.168.1.50",
    "version": "1.2.3",
    "capabilities": ["web", "excel", "pdf"]
}
print_info(f"Payload: {json.dumps(create_payload, indent=2)}")

response = requests.post(
    f"{BASE_URL}/agents",
    json=create_payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
)

print_info(f"Status Code: {response.status_code}")
if response.status_code == 201:
    agent = response.json()
    agent_id = agent.get("id")
    print_success(f"Agent created with ID: {agent_id}")
    print_info(f"Response: {json.dumps(agent, indent=2, default=str)}")
else:
    print_error(f"Failed to create agent")
    print_info(f"Response: {response.text}")
    sys.exit(1)

# Test 2: Get Agent by ID
print_test("TEST 2: GET /agents/{id} - Retrieve Agent")
print_info(f"Agent ID: {agent_id}")

response = requests.get(
    f"{BASE_URL}/agents/{agent_id}",
    headers={"Authorization": f"Bearer {TOKEN}"}
)

print_info(f"Status Code: {response.status_code}")
if response.status_code == 200:
    agent = response.json()
    print_success(f"Agent retrieved: {agent.get('name')}")
    print_info(f"Response: {json.dumps(agent, indent=2, default=str)}")
else:
    print_error(f"Failed to get agent")
    print_info(f"Response: {response.text}")

# Test 3: List Agents (without filters)
print_test("TEST 3: GET /agents - List All Agents")

response = requests.get(
    f"{BASE_URL}/agents?page=1&size=10",
    headers={"Authorization": f"Bearer {TOKEN}"}
)

print_info(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    total = data.get("total", 0)
    items = data.get("items", [])
    print_success(f"Listed {len(items)} agents (total: {total})")
    print_info(f"First few agents:")
    for agent in items[:3]:
        print(f"  - {agent.get('name')} (status: {agent.get('status')})")
else:
    print_error(f"Failed to list agents")
    print_info(f"Response: {response.text[:200]}")

# Test 4: Update Agent
print_test("TEST 4: PUT /agents/{id} - Update Agent")
update_payload = {
    "name": f"Updated-{agent_name}",
    "ip_address": "192.168.1.100"
}
print_info(f"Payload: {json.dumps(update_payload, indent=2)}")

response = requests.put(
    f"{BASE_URL}/agents/{agent_id}",
    json=update_payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
)

print_info(f"Status Code: {response.status_code}")
if response.status_code == 200:
    agent = response.json()
    print_success(f"Agent updated: {agent.get('name')}")
    print_info(f"New IP: {agent.get('ip_address')}")
else:
    print_error(f"Failed to update agent")
    print_info(f"Response: {response.text}")

# Test 5: Record Heartbeat
print_test("TEST 5: POST /agents/{id}/heartbeat - Record Heartbeat")
heartbeat_payload = {
    "status": "online",
    "extra_data": {
        "cpu_usage": 45.2,
        "memory_usage": 62.1,
        "disk_usage": 72.3
    }
}
print_info(f"Payload: {json.dumps(heartbeat_payload, indent=2)}")

response = requests.post(
    f"{BASE_URL}/agents/{agent_id}/heartbeat",
    json=heartbeat_payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
)

print_info(f"Status Code: {response.status_code}")
if response.status_code == 200:
    hb = response.json()
    print_success(f"Heartbeat recorded: {hb.get('status')}")
    print_info(f"Last heartbeat: {hb.get('last_heartbeat')}")
else:
    print_error(f"Failed to record heartbeat")
    print_info(f"Response: {response.text}")

# Test 6: Filter by status
print_test("TEST 6: GET /agents?status=online - Filter by Status")

response = requests.get(
    f"{BASE_URL}/agents?status=online&size=5",
    headers={"Authorization": f"Bearer {TOKEN}"}
)

print_info(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    items = data.get("items", [])
    print_success(f"Found {len(items)} online agents")
else:
    print_error(f"Failed to filter agents")
    print_info(f"Response: {response.text[:200]}")

# Test 7: Delete Agent
print_test("TEST 7: DELETE /agents/{id} - Soft Delete Agent")

response = requests.delete(
    f"{BASE_URL}/agents/{agent_id}",
    headers={"Authorization": f"Bearer {TOKEN}"}
)

print_info(f"Status Code: {response.status_code}")
if response.status_code == 200:
    msg = response.json()
    print_success(f"Agent deleted: {msg.get('message')}")
else:
    print_error(f"Failed to delete agent")
    print_info(f"Response: {response.text}")

# Test 8: Verify agent is soft-deleted
print_test("TEST 8: Verify Soft Delete - Agent Should Not Appear in List")

response = requests.get(
    f"{BASE_URL}/agents?size=100",
    headers={"Authorization": f"Bearer {TOKEN}"}
)

print_info(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    items = data.get("items", [])
    deleted_agent_found = any(a.get("id") == agent_id for a in items)
    
    if not deleted_agent_found:
        print_success(f"Deleted agent correctly excluded from list")
    else:
        print_error(f"Deleted agent still appears in list!")
else:
    print_error(f"Failed to list agents")

print_test("ALL TESTS COMPLETED")
print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Agents API validation complete!{Colors.ENDC}\n")

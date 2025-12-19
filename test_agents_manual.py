#!/usr/bin/env python3
"""
Script de teste dos endpoints de Agents.

Cria dados de teste e executa requisições HTTP para validar todos
os endpoints de CRUD de agentes.
"""

import asyncio
import requests
import json
from uuid import uuid4
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

# Cores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_section(title):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")


class AgentTestClient:
    def __init__(self):
        self.token = None
        # Use existing tenant from database
        self.tenant_id = "11385239-10a6-4808-afab-b58166655c66"  # Demo Corporation tenant
        self.agent_id = None
        self.session = requests.Session()
    
    def get_headers(self):
        """Retorna headers com token de autenticação"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def register_user(self):
        """Registra novo usuário de teste e faz login"""
        print_section("1. Autenticando Usuário")
        
        # Try login first
        print(f"{BLUE}Tentando login com credenciais existentes...{RESET}")
        login_payload = {
            "email": "admin@demo.com",
            "password": "Demo123!"
        }
        
        print(f"Payload: {json.dumps(login_payload, indent=2)}")
        
        response = self.session.post(
            f"{BASE_URL}/auth/login",
            json=login_payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            print_success(f"Login bem-sucedido! Token obtido: {self.token[:20]}...")
            return True
        else:
            print_error(f"Login falhou: {response.text}")
            
            # Try registering new user
            print(f"\n{BLUE}Registrando novo usuário...{RESET}")
            
            email = f"test-{uuid4().hex[:8]}@example.com"
            password = "AgentTest123!"
            
            payload = {
                "email": email,
                "password": password,
                "full_name": "Agent Tester",
                "tenant_id": self.tenant_id,
                "is_superuser": False
            }
            
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            response = self.session.post(
                f"{BASE_URL}/auth/register",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code in [200, 201]:
                print_success(f"Usuário registrado: {email}")
                
                # Now login with the new user
                print(f"\n{BLUE}Fazendo login com novo usuário...{RESET}")
                login_payload = {
                    "email": email,
                    "password": password
                }
                
                response = self.session.post(
                    f"{BASE_URL}/auth/login",
                    json=login_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"Status: {response.status_code}")
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    print_success(f"Token obtido: {self.token[:20]}...")
                    return True
                else:
                    print_error(f"Login falhou: {response.text}")
                    return False
            else:
                print_error(f"Falha ao registrar: {response.text}")
                return False
    
    def create_agent(self, name="Test Agent 001"):
        """Cria novo agente"""
        print_section("2. Criando Agente")
        
        payload = {
            "name": name,
            "machine_name": "machine-001",
            "ip_address": "192.168.1.1",
            "version": "1.0.0",
            "capabilities": ["web", "excel"]
        }
        
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = self.session.post(
            f"{BASE_URL}/agents",
            json=payload,
            headers=self.get_headers()
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            data = response.json()
            self.agent_id = data.get("id")
            print_success(f"Agente criado: {self.agent_id}")
            return True
        else:
            print_error(f"Falha ao criar agente: {response.text}")
            return False
    
    def list_agents(self, **params):
        """Lista agentes com filtros opcionais"""
        print_section("3. Listando Agentes")
        
        print(f"Filtros: {params}")
        
        response = self.session.get(
            f"{BASE_URL}/agents",
            params=params,
            headers=self.get_headers()
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, default=str)}")
        
        if response.status_code == 200:
            total = data.get("total", 0)
            items = len(data.get("items", []))
            print_success(f"Total: {total}, Retornados: {items}")
            return True
        else:
            print_error(f"Falha ao listar: {response.text}")
            return False
    
    def get_agent(self, agent_id=None):
        """Busca agente por ID"""
        print_section("4. Buscando Agente por ID")
        
        agent_id = agent_id or self.agent_id
        print(f"Agent ID: {agent_id}")
        
        response = self.session.get(
            f"{BASE_URL}/agents/{agent_id}",
            headers=self.get_headers()
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            print_success("Agente encontrado")
            return True
        else:
            print_error(f"Falha ao buscar: {response.text}")
            return False
    
    def update_agent(self, agent_id=None):
        """Atualiza agente"""
        print_section("5. Atualizando Agente")
        
        agent_id = agent_id or self.agent_id
        
        payload = {
            "name": "Updated Agent Name",
            "ip_address": "192.168.1.100"
        }
        
        print(f"Agent ID: {agent_id}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = self.session.put(
            f"{BASE_URL}/agents/{agent_id}",
            json=payload,
            headers=self.get_headers()
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            print_success("Agente atualizado")
            return True
        else:
            print_error(f"Falha ao atualizar: {response.text}")
            return False
    
    def record_heartbeat(self, agent_id=None):
        """Registra heartbeat"""
        print_section("6. Registrando Heartbeat")
        
        agent_id = agent_id or self.agent_id
        
        payload = {
            "status": "online",
            "extra_data": {
                "cpu_usage": 45.2,
                "memory_usage": 62.1,
                "disk_usage": 72.3
            }
        }
        
        print(f"Agent ID: {agent_id}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = self.session.post(
            f"{BASE_URL}/agents/{agent_id}/heartbeat",
            json=payload,
            headers=self.get_headers()
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            print_success("Heartbeat registrado")
            return True
        else:
            print_error(f"Falha ao registrar heartbeat: {response.text}")
            return False
    
    def delete_agent(self, agent_id=None):
        """Deleta agente (soft delete)"""
        print_section("7. Deletando Agente")
        
        agent_id = agent_id or self.agent_id
        print(f"Agent ID: {agent_id}")
        
        response = self.session.delete(
            f"{BASE_URL}/agents/{agent_id}",
            headers=self.get_headers()
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print_success("Agente deletado")
            return True
        else:
            print_error(f"Falha ao deletar: {response.text}")
            return False
    
    def test_filtering(self):
        """Testa filtros de listagem"""
        print_section("8. Testando Filtros")
        
        # Criar múltiplos agentes
        print(f"{BLUE}Criando 3 agentes para teste de filtros...{RESET}")
        for i in range(1, 4):
            self.create_agent(f"Agent {i:03d}")
        
        # Teste: filtrar por machine_name
        print(f"\n{BLUE}Filtrando por machine_name...{RESET}")
        self.list_agents(machine_name="machine")
        
        # Teste: paginação
        print(f"\n{BLUE}Testando paginação (page=1, size=2)...{RESET}")
        self.list_agents(page=1, size=2)
        
        # Teste: sorting
        print(f"\n{BLUE}Testando ordenação (sort_by=name, sort_order=asc)...{RESET}")
        self.list_agents(sort_by="name", sort_order="asc")
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print_section("TESTE DE AGENTS - SUITE COMPLETA")
        
        # 1. Registrar usuário
        if not self.register_user():
            print_error("Falha no registro. Abortando...")
            return False
        
        # 2. Criar agente
        if not self.create_agent():
            print_error("Falha ao criar agente. Abortando...")
            return False
        
        # 3. Listar agentes
        self.list_agents()
        
        # 4. Buscar agente
        self.get_agent()
        
        # 5. Atualizar agente
        self.update_agent()
        
        # 6. Heartbeat
        self.record_heartbeat()
        
        # 7. Deletar
        self.delete_agent()
        
        # 8. Filtros
        self.test_filtering()
        
        print_section("TESTES CONCLUÍDOS")
        print_success("Todos os testes foram executados!")


if __name__ == "__main__":
    client = AgentTestClient()
    client.run_all_tests()

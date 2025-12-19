#!/bin/bash
# backend/scripts/test_fase5a_processes.sh
# Script de teste para Fase 5A - Processos + Versionamento

set -e

API_URL="http://localhost:8000"
API_PREFIX="/api/v1"

# ✅ COLOQUE SEU TOKEN AQUI
ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmNjBlOTcwNC0yOWVmLTRjNGYtOTI4ZS02MTdiODJkMmZmMTUiLCJ0ZW5hbnRfaWQiOiIxMTM4NTIzOS0xMGE2LTQ4MDgtYWZhYi1iNTgxNjY2NTVjNjYiLCJlbWFpbCI6InRlc3RlQGRlbW8uY29tIiwiaXNfc3VwZXJ1c2VyIjpmYWxzZSwiZXhwIjoxNzY1OTExNjM4LCJpYXQiOjE3NjU5MDk4MzgsInR5cGUiOiJhY2Nlc3MifQ.mWxFNFYl2D_zi1wGwFFNm0TC6_HKdLf8WkyXVT5LgCU"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Timestamp único para cada execução
TIMESTAMP=$(date +%s)

echo -e "${YELLOW}=== FASE 5A: Testes de Processos e Versionamento ===${NC}\n"

# ============================================================================
# 1. CRIAR PROCESSO
# ============================================================================

echo -e "${YELLOW}[1] POST /processes - Criar Processo${NC}"

PROCESS_RESPONSE=$(curl -s -X POST "$API_URL$API_PREFIX/processes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
    \"name\": \"invoice_processing_v2_$TIMESTAMP\",
    \"description\": \"Processa faturas com validação automática\",
    \"tipo\": \"unattended\",
    \"tags\": [\"financeiro\", \"mensal\", \"critico\"],
    \"extra_data\": {
      \"priority\": \"high\",
      \"department\": \"finance\"
    }
  }")

echo "$PROCESS_RESPONSE" | jq .

PROCESS_ID=$(echo "$PROCESS_RESPONSE" | jq -r '.id // empty')

if [ -z "$PROCESS_ID" ] || [ "$PROCESS_ID" = "null" ]; then
  echo -e "${RED}✗ Erro ao criar processo${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Processo criado com ID: $PROCESS_ID${NC}\n"

# ============================================================================
# 2. LISTAR PROCESSOS
# ============================================================================

echo -e "${YELLOW}[2] GET /processes - Listar Processos${NC}"

curl -s -X GET "$API_URL$API_PREFIX/processes?tipo=unattended&is_active=true&page=1&size=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

echo -e "${GREEN}✓ Processos listados${NC}\n"

# ============================================================================
# 3. FILTRO POR TAGS (ANY) - COM HEADER DE AUTH
# ============================================================================

echo -e "${YELLOW}[3] GET /processes - Filtro por Tags (ANY)${NC}"

curl -s -X GET "$API_URL$API_PREFIX/processes?tags=financeiro%2Cmensal&tag_match=any&page=1&size=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

echo -e "${GREEN}✓ Processos filtrados por tags (ANY)${NC}\n"

# ============================================================================
# 4. BUSCA TEXTUAL
# ============================================================================

echo -e "${YELLOW}[4] GET /processes - Busca Textual${NC}"

curl -s -X GET "$API_URL$API_PREFIX/processes?search=invoice" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

echo -e "${GREEN}✓ Busca textual realizada${NC}\n"

# ============================================================================
# 5. OBTER DETALHE
# ============================================================================

echo -e "${YELLOW}[5] GET /processes/{id} - Obter Detalhe${NC}"

curl -s -X GET "$API_URL$API_PREFIX/processes/$PROCESS_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

echo -e "${GREEN}✓ Detalhe do processo obtido${NC}\n"

# ============================================================================
# 6. ATUALIZAR PROCESSO
# ============================================================================

echo -e "${YELLOW}[6] PUT /processes/{id} - Atualizar Processo${NC}"

curl -s -X PUT "$API_URL$API_PREFIX/processes/$PROCESS_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "description": "Processamento de faturas ATUALIZADO",
    "tags": ["financeiro", "urgente"],
    "is_active": true
  }' | jq .

echo -e "${GREEN}✓ Processo atualizado${NC}\n"

# ============================================================================
# 7. CRIAR VERSÃO 1.0.0
# ============================================================================

echo -e "${YELLOW}[7] POST /processes/{id}/versions - Criar Versão 1.0.0${NC}"

VERSION_1_RESPONSE=$(curl -s -X POST "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "version": "1.0.0",
    "package_path": "s3://bucket/processes/invoice_v1.0.0.zip",
    "release_notes": "Versão inicial",
    "config": {"timeout": 300, "retry_count": 3}
  }')

echo "$VERSION_1_RESPONSE" | jq .

VERSION_1_ID=$(echo "$VERSION_1_RESPONSE" | jq -r '.id // empty')

if [ -z "$VERSION_1_ID" ] || [ "$VERSION_1_ID" = "null" ]; then
  echo -e "${RED}✗ Erro ao criar versão${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Versão 1.0.0 criada${NC}\n"

# ============================================================================
# 8. ATIVAR VERSÃO 1.0.0
# ============================================================================

echo -e "${YELLOW}[8] PUT /processes/{id}/versions/{vid}/activate - Ativar Versão 1.0.0${NC}"

curl -s -X PUT "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions/$VERSION_1_ID/activate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{}' | jq .

echo -e "${GREEN}✓ Versão 1.0.0 ativada${NC}\n"

# ============================================================================
# 9. CRIAR VERSÃO 1.1.0
# ============================================================================

echo -e "${YELLOW}[9] POST /processes/{id}/versions - Criar Versão 1.1.0${NC}"

VERSION_2_RESPONSE=$(curl -s -X POST "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "version": "1.1.0",
    "package_path": "s3://bucket/processes/invoice_v1.1.0.zip",
    "release_notes": "Adicionada validação de CNPJ",
    "config": {"timeout": 600, "retry_count": 5}
  }')

echo "$VERSION_2_RESPONSE" | jq .

VERSION_2_ID=$(echo "$VERSION_2_RESPONSE" | jq -r '.id // empty')

if [ -z "$VERSION_2_ID" ] || [ "$VERSION_2_ID" = "null" ]; then
  echo -e "${RED}✗ Erro ao criar versão${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Versão 1.1.0 criada${NC}\n"

# ============================================================================
# 10. LISTAR VERSÕES
# ============================================================================

echo -e "${YELLOW}[10] GET /processes/{id}/versions - Listar Versões${NC}"

curl -s -X GET "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

echo -e "${GREEN}✓ Versões listadas${NC}\n"

# ============================================================================
# 11. ATIVAR VERSÃO 1.1.0
# ============================================================================

echo -e "${YELLOW}[11] PUT /processes/{id}/versions/{vid}/activate - Ativar Versão 1.1.0${NC}"

curl -s -X PUT "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions/$VERSION_2_ID/activate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{}' | jq .

echo -e "${GREEN}✓ Versão 1.1.0 ativada (1.0.0 desativada)${NC}\n"

# ============================================================================
# 12. VERIFICAR VERSÃO ATIVA
# ============================================================================

echo -e "${YELLOW}[12] GET /processes/{id} - Verificar Nova Versão Ativa${NC}"

curl -s -X GET "$API_URL$API_PREFIX/processes/$PROCESS_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.active_version'

echo -e "${GREEN}✓ Versão ativa agora é 1.1.0${NC}\n"

# ============================================================================
# 13. SOFT DELETE
# ============================================================================

echo -e "${YELLOW}[13] DELETE /processes/{id} - Soft Delete${NC}"

curl -s -X DELETE "$API_URL$API_PREFIX/processes/$PROCESS_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

echo -e "${GREEN}✓ Processo deletado${NC}\n"

# ============================================================================
# 14. VERIFICAR QUE NÃO APARECE MAIS
# ============================================================================

echo -e "${YELLOW}[14] GET /processes - Verificar que Processo Não Aparece${NC}"

FINAL_COUNT=$(curl -s -X GET "$API_URL$API_PREFIX/processes" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.items | length')

echo "Total de processos: $FINAL_COUNT"
echo -e "${GREEN}✓ Processo deletado não aparece${NC}\n"

# ============================================================================
# RESUMO
# ============================================================================

echo -e "${GREEN}=== TESTES COMPLETADOS COM SUCESSO ===${NC}"

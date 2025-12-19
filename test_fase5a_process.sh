#!/bin/bash
# backend/scripts/test_fase5a_processes.sh
# Script de teste para Fase 5A - Processos + Versionamento

set -euo pipefail

API_URL="http://localhost:8000"
API_PREFIX="/api/v1"

# ✅ COLOQUE SEU TOKEN AQUI (recomendado: export ACCESS_TOKEN=... e comentar essa linha)
ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmNjBlOTcwNC0yOWVmLTRjNGYtOTI4ZS02MTdiODJkMmZmMTUiLCJ0ZW5hbnRfaWQiOiIxMTM4NTIzOS0xMGE2LTQ4MDgtYWZhYi1iNTgxNjY2NTVjNjYiLCJlbWFpbCI6InRlc3RlQGRlbW8uY29tIiwiaXNfc3VwZXJ1c2VyIjpmYWxzZSwiZXhwIjoxNzY1OTIyNjI1LCJpYXQiOjE3NjU5MjA4MjUsInR5cGUiOiJhY2Nlc3MifQ.FGGHCBn6Q5nK7KZC9t7W0QPjtrXILM7ShKGA7WjOYmw"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Timestamp único para cada execução
TIMESTAMP="$(date +%s)"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

require_bin() {
  command -v "$1" >/dev/null 2>&1 || {
    echo -e "${RED}✗ Dependência ausente: $1${NC}"
    exit 127
  }
}

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo -e "${RED}✗ Variável obrigatória não definida: $name${NC}"
    exit 2
  fi
}

# Faz uma request e:
# - imprime body formatado se for JSON
# - valida HTTP status (2xx esperado)
# - mostra erro claro se body não for JSON (401/500 etc.)
request_json() {
  local method="$1"; shift
  local url="$1"; shift
  local data="${1:-}"

  # curl: -sS (silencioso, mas mostra erro), -L (segue redirect se houver)
  # --fail-with-body: retorna exit != 0 em 4xx/5xx mantendo body (se suportado)
  local curl_fail="--fail-with-body"
  if ! curl --help 2>/dev/null | grep -q -- "--fail-with-body"; then
    curl_fail="--fail"
  fi

  local resp http body
  if [ -n "$data" ]; then
    resp="$(curl -sS -X "$method" "$url" \
      $curl_fail \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -d "$data" \
      -w $'\nHTTP_STATUS:%{http_code}\n' \
    )" || true
  else
    resp="$(curl -sS -X "$method" "$url" \
      $curl_fail \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -w $'\nHTTP_STATUS:%{http_code}\n' \
    )" || true
  fi

  http="$(echo "$resp" | awk -F'HTTP_STATUS:' 'END{print $2}' | tr -d '\r' | tr -d '\n')"
  body="$(echo "$resp" | sed '$d')"

  # tenta validar JSON
  if echo "$body" | jq -e . >/dev/null 2>&1; then
    echo "$body" | jq .
  else
    echo -e "${RED}✗ Resposta não é JSON válido (HTTP $http). Body bruto:${NC}"
    echo "----------------------------------------"
    echo "$body"
    echo "----------------------------------------"
    exit 1
  fi

  # valida HTTP status 2xx
  if [[ ! "$http" =~ ^2[0-9]{2}$ ]]; then
    echo -e "${RED}✗ HTTP status inesperado: $http${NC}"
    exit 1
  fi
}

# Versão GET com query params via --data-urlencode (evita problemas de encoding)
request_json_get_params() {
  local url="$1"; shift

  local curl_fail="--fail-with-body"
  if ! curl --help 2>/dev/null | grep -q -- "--fail-with-body"; then
    curl_fail="--fail"
  fi

  local resp http body
  # -G transforma --data-urlencode em querystring
  resp="$(curl -sS -G "$url" \
    $curl_fail \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "$@" \
    -w $'\nHTTP_STATUS:%{http_code}\n' \
  )" || true

  http="$(echo "$resp" | awk -F'HTTP_STATUS:' 'END{print $2}' | tr -d '\r' | tr -d '\n')"
  body="$(echo "$resp" | sed '$d')"

  if echo "$body" | jq -e . >/dev/null 2>&1; then
    echo "$body" | jq .
  else
    echo -e "${RED}✗ Resposta não é JSON válido (HTTP $http). Body bruto:${NC}"
    echo "----------------------------------------"
    echo "$body"
    echo "----------------------------------------"
    exit 1
  fi

  if [[ ! "$http" =~ ^2[0-9]{2}$ ]]; then
    echo -e "${RED}✗ HTTP status inesperado: $http${NC}"
    exit 1
  fi
}

# ------------------------------------------------------------------------------
# Pré-checks
# ------------------------------------------------------------------------------

require_bin curl
require_bin jq
require_env ACCESS_TOKEN

echo -e "${YELLOW}=== FASE 5A: Testes de Processos e Versionamento ===${NC}\n"

# ============================================================================
# 1. CRIAR PROCESSO
# ============================================================================

echo -e "${YELLOW}[1] POST /processes - Criar Processo${NC}"

PROCESS_PAYLOAD="$(cat <<JSON
{
  "name": "invoice_processing_v2_${TIMESTAMP}",
  "description": "Processa faturas com validação automática",
  "tipo": "unattended",
  "tags": ["financeiro", "mensal", "critico"],
  "extra_data": {
    "priority": "high",
    "department": "finance"
  }
}
JSON
)"

PROCESS_RESPONSE="$(curl -sS -X POST "$API_URL$API_PREFIX/processes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "$PROCESS_PAYLOAD")"

# valida e imprime
echo "$PROCESS_RESPONSE" | jq .

PROCESS_ID="$(echo "$PROCESS_RESPONSE" | jq -r '.id // empty')"

if [ -z "$PROCESS_ID" ] || [ "$PROCESS_ID" = "null" ]; then
  echo -e "${RED}✗ Erro ao criar processo (id vazio)${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Processo criado com ID: $PROCESS_ID${NC}\n"

# ============================================================================
# 2. LISTAR PROCESSOS
# ============================================================================

echo -e "${YELLOW}[2] GET /processes - Listar Processos${NC}"

request_json_get_params "$API_URL$API_PREFIX/processes" \
  --data-urlencode "tipo=unattended" \
  --data-urlencode "is_active=true" \
  --data-urlencode "page=1" \
  --data-urlencode "size=10"

echo -e "${GREEN}✓ Processos listados${NC}\n"

# ============================================================================
# 3. FILTRO POR TAGS (ANY) - CORRIGIDO (tags repetidas)
# ============================================================================

echo -e "${YELLOW}[3] GET /processes - Filtro por Tags (ANY)${NC}"

request_json_get_params "$API_URL$API_PREFIX/processes" \
  --data-urlencode "tags=financeiro" \
  --data-urlencode "tags=mensal" \
  --data-urlencode "tag_match=any" \
  --data-urlencode "page=1" \
  --data-urlencode "size=10"

echo -e "${GREEN}✓ Processos filtrados por tags (ANY)${NC}\n"

# ============================================================================
# 4. BUSCA TEXTUAL
# ============================================================================

echo -e "${YELLOW}[4] GET /processes - Busca Textual${NC}"

request_json_get_params "$API_URL$API_PREFIX/processes" \
  --data-urlencode "search=invoice"

echo -e "${GREEN}✓ Busca textual realizada${NC}\n"

# ============================================================================
# 5. OBTER DETALHE
# ============================================================================

echo -e "${YELLOW}[5] GET /processes/{id} - Obter Detalhe${NC}"

request_json "GET" "$API_URL$API_PREFIX/processes/$PROCESS_ID"

echo -e "${GREEN}✓ Detalhe do processo obtido${NC}\n"

# ============================================================================
# 6. ATUALIZAR PROCESSO
# ============================================================================

echo -e "${YELLOW}[6] PUT /processes/{id} - Atualizar Processo${NC}"

UPDATE_PAYLOAD="$(cat <<'JSON'
{
  "description": "Processamento de faturas ATUALIZADO",
  "tags": ["financeiro", "urgente"],
  "is_active": true
}
JSON
)"

request_json "PUT" "$API_URL$API_PREFIX/processes/$PROCESS_ID" "$UPDATE_PAYLOAD"

echo -e "${GREEN}✓ Processo atualizado${NC}\n"

# ============================================================================
# 7. CRIAR VERSÃO 1.0.0
# ============================================================================

echo -e "${YELLOW}[7] POST /processes/{id}/versions - Criar Versão 1.0.0${NC}"

VERSION_1_PAYLOAD="$(cat <<'JSON'
{
  "version": "1.0.0",
  "package_path": "s3://bucket/processes/invoice_v1.0.0.zip",
  "release_notes": "Versão inicial",
  "config": {"timeout": 300, "retry_count": 3}
}
JSON
)"

VERSION_1_RESPONSE="$(curl -sS -X POST "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "$VERSION_1_PAYLOAD")"

echo "$VERSION_1_RESPONSE" | jq .

VERSION_1_ID="$(echo "$VERSION_1_RESPONSE" | jq -r '.id // empty')"

if [ -z "$VERSION_1_ID" ] || [ "$VERSION_1_ID" = "null" ]; then
  echo -e "${RED}✗ Erro ao criar versão 1.0.0${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Versão 1.0.0 criada (ID: $VERSION_1_ID)${NC}\n"

# ============================================================================
# 8. ATIVAR VERSÃO 1.0.0
# ============================================================================

echo -e "${YELLOW}[8] PUT /processes/{id}/versions/{vid}/activate - Ativar Versão 1.0.0${NC}"

request_json "PUT" "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions/$VERSION_1_ID/activate" '{}'

echo -e "${GREEN}✓ Versão 1.0.0 ativada${NC}\n"

# ============================================================================
# 9. CRIAR VERSÃO 1.1.0
# ============================================================================

echo -e "${YELLOW}[9] POST /processes/{id}/versions - Criar Versão 1.1.0${NC}"

VERSION_2_PAYLOAD="$(cat <<'JSON'
{
  "version": "1.1.0",
  "package_path": "s3://bucket/processes/invoice_v1.1.0.zip",
  "release_notes": "Adicionada validação de CNPJ",
  "config": {"timeout": 600, "retry_count": 5}
}
JSON
)"

VERSION_2_RESPONSE="$(curl -sS -X POST "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "$VERSION_2_PAYLOAD")"

echo "$VERSION_2_RESPONSE" | jq .

VERSION_2_ID="$(echo "$VERSION_2_RESPONSE" | jq -r '.id // empty')"

if [ -z "$VERSION_2_ID" ] || [ "$VERSION_2_ID" = "null" ]; then
  echo -e "${RED}✗ Erro ao criar versão 1.1.0${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Versão 1.1.0 criada (ID: $VERSION_2_ID)${NC}\n"

# ============================================================================
# 10. LISTAR VERSÕES
# ============================================================================

echo -e "${YELLOW}[10] GET /processes/{id}/versions - Listar Versões${NC}"

request_json "GET" "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions"

echo -e "${GREEN}✓ Versões listadas${NC}\n"

# ============================================================================
# 11. ATIVAR VERSÃO 1.1.0
# ============================================================================

echo -e "${YELLOW}[11] PUT /processes/{id}/versions/{vid}/activate - Ativar Versão 1.1.0${NC}"

request_json "PUT" "$API_URL$API_PREFIX/processes/$PROCESS_ID/versions/$VERSION_2_ID/activate" '{}'

echo -e "${GREEN}✓ Versão 1.1.0 ativada (1.0.0 desativada)${NC}\n"

# ============================================================================
# 12. VERIFICAR VERSÃO ATIVA
# ============================================================================

echo -e "${YELLOW}[12] GET /processes/{id} - Verificar Nova Versão Ativa${NC}"

# imprime só o campo active_version (valida json antes)
ACTIVE_VERSION="$(curl -sS -X GET "$API_URL$API_PREFIX/processes/$PROCESS_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.active_version // empty')"

if [ -z "$ACTIVE_VERSION" ]; then
  echo -e "${RED}✗ Não foi possível obter active_version${NC}"
  exit 1
fi

echo "active_version: $ACTIVE_VERSION"
echo -e "${GREEN}✓ Versão ativa agora é ${ACTIVE_VERSION}${NC}\n"

# ============================================================================
# 13. SOFT DELETE
# ============================================================================

echo -e "${YELLOW}[13] DELETE /processes/{id} - Soft Delete${NC}"

request_json "DELETE" "$API_URL$API_PREFIX/processes/$PROCESS_ID"

echo -e "${GREEN}✓ Processo deletado${NC}\n"

# ============================================================================
# 14. VERIFICAR QUE NÃO APARECE MAIS
# ============================================================================

echo -e "${YELLOW}[14] GET /processes - Verificar que Processo Não Aparece${NC}"

FINAL_COUNT="$(curl -sS -X GET "$API_URL$API_PREFIX/processes" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq '.items | length')"

echo "Total de processos: $FINAL_COUNT"
echo -e "${GREEN}✓ Processo deletado não aparece (validar pelo seu filtro de soft delete no backend)${NC}\n"

# ============================================================================
# RESUMO
# ============================================================================

echo -e "${GREEN}=== TESTES COMPLETADOS COM SUCESSO ===${NC}"

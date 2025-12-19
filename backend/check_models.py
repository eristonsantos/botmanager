#!/usr/bin/env python3
"""
Script para forçar registro de todas as tabelas no metadata.
Execute ANTES de gerar migrations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# IMPORTANTE: Importar TODOS os modelos explicitamente
from app.models import (
    BaseModel,
    Tenant,
    User,
    Agente,
    Processo,
    VersaoProcesso,
    Execucao,
    ItemFila,
    Excecao,
    Asset,
    Credencial,
    Agendamento,
    AuditoriaEvento,
    LogExecucao,
    LogMetadata,
)

print("=" * 70)
print("🔧 REGISTRO DE TABELAS NO METADATA")
print("=" * 70)

# Verificar metadata
tables = BaseModel.metadata.tables
print(f"\n📊 Total de tabelas registradas: {len(tables)}")

if len(tables) == 0:
    print("\n❌ NENHUMA tabela detectada!")
    print("\n🔍 Isso indica um problema estrutural.")
    print("   Possíveis causas:")
    print("   1. BaseModel não está sendo reconhecido corretamente")
    print("   2. Modelos não estão sendo importados")
    print("   3. table=True está faltando nos modelos")
else:
    print("\n✅ Tabelas detectadas:")
    for table_name in sorted(tables.keys()):
        table = tables[table_name]
        print(f"   • {table_name:20s} ({len(table.columns):2d} colunas, {len(table.foreign_keys):2d} FKs)")

# Verificar se Tenant está separado
print(f"\n🏢 Tenant metadata: {Tenant.metadata.tables}")

print("\n" + "=" * 70)
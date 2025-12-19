#!/usr/bin/env python3
"""
Script de diagnóstico para verificar se o SQLModel está registrando as tabelas.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.models import BaseModel

print("=" * 70)
print("🔍 DIAGNÓSTICO DO METADATA")
print("=" * 70)

# Verificar quantas tabelas estão registradas
tables = BaseModel.metadata.tables
print(f"\n📊 Total de tabelas no metadata: {len(tables)}")

if len(tables) == 0:
    print("\n❌ PROBLEMA: Nenhuma tabela detectada no metadata!")
    print("   Isso explica por que o Alembic não gera nada.")
else:
    print("\n✅ Tabelas encontradas:")
    for table_name in sorted(tables.keys()):
        table = tables[table_name]
        print(f"   • {table_name} ({len(table.columns)} colunas)")

print("\n" + "=" * 70)
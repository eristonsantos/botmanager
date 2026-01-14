# backend/app/api/v1/workload.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_tenant_id
from app.models.workload import ItemFila, StatusItemFilaEnum

# Imports corretos do schema
from app.schemas.workload import (
    ItemFilaCreate, 
    ItemFilaRead, 
    ItemFilaUpdate,
    WorkloadActionResponse
)

router = APIRouter(prefix="/workload", tags=["Filas de Trabalho"])

# --- 1. CRIAÇÃO ---
@router.post("/items", response_model=ItemFilaRead)
async def create_item(
    item: ItemFilaCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    # Verifica duplicidade (PENDING ou RUNNING)
    if item.reference:
        query = select(ItemFila).where(
            ItemFila.queue_name == item.queue_name,
            ItemFila.reference == item.reference,
            ItemFila.tenant_id == tenant_id,
            # ATENÇÃO: Mudamos de PROCESSING para RUNNING aqui
            ItemFila.status.in_([StatusItemFilaEnum.PENDING, StatusItemFilaEnum.RUNNING])
        )
        existing = (await session.execute(query)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail=f"Item '{item.reference}' já existe e está pendente/rodando.")

    db_item = ItemFila(**item.model_dump(), tenant_id=tenant_id)
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    return db_item

# --- 2. LISTAGEM ---
@router.get("/items", response_model=List[ItemFilaRead])
async def list_items(
    queue_name: Optional[str] = None,
    status: Optional[StatusItemFilaEnum] = None,
    skip: int = 0,
    limit: int = 50,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    query = select(ItemFila).where(ItemFila.tenant_id == tenant_id)
    if queue_name:
        query = query.where(ItemFila.queue_name == queue_name)
    if status:
        query = query.where(ItemFila.status == status)
        
    query = query.order_by(ItemFila.priority.desc(), ItemFila.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()

# --- 3. EXCLUSÃO ---
@router.delete("/items/{item_id}")
async def delete_item(
    item_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    query = select(ItemFila).where(ItemFila.id == item_id, ItemFila.tenant_id == tenant_id)
    item = (await session.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
        
    await session.delete(item)
    await session.commit()
    return {"message": "Item excluído"}

# --- 4. ATUALIZAÇÃO ---
@router.patch("/items/{item_id}", response_model=ItemFilaRead)
async def update_item(
    item_id: UUID,
    update_data: ItemFilaUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    query = select(ItemFila).where(ItemFila.id == item_id, ItemFila.tenant_id == tenant_id)
    item = (await session.execute(query)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    
    data = update_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
        
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item

# --- 5. ROBÔ GET NEXT ---
@router.post("/get-next", response_model=Optional[ItemFilaRead])
async def get_next_item(
    queue_name: str,
    tenant_id: UUID = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    query = select(ItemFila).where(
        ItemFila.queue_name == queue_name,
        ItemFila.tenant_id == tenant_id,
        ItemFila.status == StatusItemFilaEnum.PENDING,
        ItemFila.locked_by == None
    ).order_by(ItemFila.priority.desc(), ItemFila.created_at.asc()).limit(1).with_for_update(skip_locked=True)
    
    result = await session.execute(query)
    item = result.scalar_one_or_none()
    
    if item:
        item.status = StatusItemFilaEnum.RUNNING # <--- RUNNING aqui também
        item.locked_until = func.now()
        session.add(item)
        await session.commit()
        await session.refresh(item)
        
    return item
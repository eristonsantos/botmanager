# backend/app/api/__init__.py
"""
API package - Endpoints REST da aplicação.
"""
from app.api.v1 import api_router


__all__ = ["api_router"]
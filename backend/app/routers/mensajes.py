# routers/mensajes.py

from fastapi import APIRouter, Depends, HTTPException
from schemas.mensaje import MensajeIn, MensajeEdit, MensajeDelete, MensajeOut
from services.mensaje import guardar_mensaje,guardar_mensaje1, obtener_mensajes, editar_mensaje, eliminar_mensaje
from utils.auth import get_current_user
from typing import List

router = APIRouter(prefix="/mensajes", tags=["mensajes"])

@router.post("/enviar", response_model=MensajeOut)
async def enviar_mensaje(data: MensajeIn, user = Depends(get_current_user)):
    try:
        return await guardar_mensaje(data, user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{sala_id}", response_model=List[MensajeOut])
async def listar_mensajes(sala_id: str):
    try:
        return await obtener_mensajes(sala_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/editar")
async def editar_mensaje_router(data: MensajeEdit, user = Depends(get_current_user)):
    try:
        return await editar_mensaje(data.sala_id, data.mensaje_id, data.nuevo_contenido, user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/eliminar")
async def eliminar_mensaje_router(data: MensajeDelete, user = Depends(get_current_user)):
    try:
        return await eliminar_mensaje(data.sala_id, data.mensaje_id, user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{sala_id}")
async def get_mensajes_sala(sala_id: str, user=Depends(get_current_user)):
    return await obtener_mensajes(sala_id)

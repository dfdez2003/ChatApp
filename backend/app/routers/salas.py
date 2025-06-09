# routers/salas.py

from fastapi import APIRouter, Depends, HTTPException
from schemas.sala import SalaCreate, ExpulsionData
from fastapi.responses import HTMLResponse, FileResponse
from services.sala import (
    crear_sala,
    crear_sala2, 
    unirse_a_sala, 
    mostrar_salas_propias, 
    mostrar_salas_random, 
    expulsar_usuario,
    eliminar_sala_completa,
    obtener_detalles_sala
)
from utils.auth import get_current_user  # esta función saca el user del token
from pydantic import BaseModel

from schemas.sala import UnirseSala

class EliminarSalaData(BaseModel):
    sala_id: str

router = APIRouter(prefix="/salas", tags=["salas"])

@router.get("/", response_class=FileResponse)
async def get_salas_page():
    return "static/salas.html"

@router.get("/detalles/{sala_id}")
async def get_detalles_sala(sala_id: str, user = Depends(get_current_user)):
    """
    Obtiene los detalles completos de una sala específica.
    """
    try:
        return await obtener_detalles_sala(sala_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/ver/{sala_id}", response_class=FileResponse)
async def ver_sala_page(sala_id: str):
    """
    Sirve la página HTML para ver los detalles de una sala.
    """
    return "static/datosala.html"

@router.post("/create")
async def crear_sala_endpoint(
    sala: SalaCreate,
    user = Depends(get_current_user)
):
    return await crear_sala2(sala, user["id"])


# routers/salas.py
@router.post("/unirse")
async def unirse_sala(data: UnirseSala, user = Depends(get_current_user)):
    try:
        return await unirse_a_sala(data, user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mias")
async def salas_usuario(user = Depends(get_current_user)):
    try:
        return await mostrar_salas_propias(user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    


@router.get("/salasrandom")
async def salas_random(user = Depends(get_current_user)):
    try:
        return await mostrar_salas_random(user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

#@router.post("/expulsar")
#async def expulsar(data: ExpulsionData, user = Depends(get_current_user)):
#    try:
#        return await expulsar_usuario(data.sala_id, data.usuario_id, user["id"])
#    except Exception as e:
#        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/eliminar")
async def eliminar_sala(data: EliminarSalaData, user = Depends(get_current_user)):
    """
    Elimina una sala completamente y todas sus referencias.
    Solo el creador de la sala puede eliminarla.
    """
    try:
        return await eliminar_sala_completa(data.sala_id, user["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

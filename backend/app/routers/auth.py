from fastapi import APIRouter, HTTPException, Depends
from schemas.usuario import UsuarioCreate, UsuarioLogin
from services.usuario import *
from utils.auth import crear_token
from utils.auth import get_current_user
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path


router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/loginchafa")
async def loginchafa():
    return FileResponse("static/login.html")
# En este otro creamos el registro, el post, se le pasa el usuario, por lo que lo crea con la funcion de servelet, y lo carga 


@router.get("/login", response_class=FileResponse)
async def login_page():
    return "static/login.html"


@router.post("/register")
async def register(usuario: UsuarioCreate):
    try:
        nuevo_usuario = await crear_usuario2(usuario)
        return {"mensaje": "Usuario registrado", "usuario": nuevo_usuario}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/registro3", response_class=HTMLResponse)
async def get_register_page():
    with open("static/registro.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)
    

# Este es el que resibe la peticion, el get qeu manda a llamar a el html
@router.get("/register", response_class=HTMLResponse)
async def get_register_page():
    html_path = Path("static/registro.html")
    return HTMLResponse(content=html_path.read_text(), status_code=200)

@router.post("/login")
async def login(data: UsuarioLogin):
    usuario = await logiar_usuario(data)
    token = crear_token({"user_id": usuario.id})
    print(f"Token: {token} Usuario:{usuario}")
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": usuario.model_dump()  # Pydantic v2 | usa .dict() si estás en v1
    }

@router.get("/me")
def quien_soy(user = Depends(get_current_user)):
    return {"id": user["id"]}



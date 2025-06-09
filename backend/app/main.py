from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, salas, mensajes, archivos,websockets
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from utils.limpieza_salas import tarea_limpieza_salas
import asyncio
app = FastAPI()

# Configuración de CORS para permitir solicitudes desde otros orígenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static",html=True), name="static")
@app.get("/login")
async def redirect_login():
    return RedirectResponse(url="/auth/login")

@app.get("/")
async def redirect_register():
    return RedirectResponse(url="/auth/register")

@app.get("/register")
async def redirect_login():
    return RedirectResponse(url="/auth/register")
@app.on_event("startup")
async def iniciar_tareas_background():
    asyncio.create_task(tarea_limpieza_salas())

# Incluir las rutas
app.include_router(auth.router)  # Rutas para autenticación
app.include_router(salas.router)  # Rutas para gestionar salas
app.include_router(mensajes.router)  # Rutas para mensajes
app.include_router(archivos.router)  # Rutas para archivos
app.include_router(websockets.router) # Ruta para los websockets
# Agregamos la de chat
# Ruta para la página principal (index)
# Ruta para login

# from websocket.chat_ws import router as chat_ws_router

# app.include_router(chat_ws_router)


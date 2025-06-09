# services/usuario_service.py

import uuid
from datetime import datetime
from passlib.context import CryptContext    # sale sale libreria para hash
from schemas.usuario import UsuarioOut
import redis.asyncio as redis
import logging
from fastapi import HTTPException
from .mongodb import *

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # hash 
r = redis.Redis()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def crear_usuario(data):
    async for key in r.scan_iter(match="usuario:*"):
        tipo = await r.type(key)

        # ✅ Validar que sea HASH antes de hacer HGET
        if tipo != b"hash":
            print(f"[DEBUG] Ignorando clave {key.decode()} de tipo {tipo.decode()}")
            continue

        email = await r.hget(key, "email")
        if email and email.decode() == data.email:
            raise Exception("Correo ya registrado")

    usuario_id = str(uuid.uuid4())
    fecha = datetime.utcnow().isoformat()
    hashed = hash_password(data.password)

    usuario_hash_key = f"usuario:{usuario_id}"
    tipo = await r.type(usuario_hash_key)
    if tipo != b"none" and tipo != b"hash":
        raise Exception(f"Conflicto de tipo en {usuario_hash_key}. Ya existe con tipo {tipo.decode()}")

    await r.hset(usuario_hash_key, mapping={
        "nombre": data.nombre,
        "surname": data.surname,
        "username": data.username,
        "email": data.email,
        "password_hash": hashed,
        "fecha_registro": fecha
    })

    print(f"[DEBUG] Usuario creado en {usuario_hash_key}")

    return {
        "id": usuario_id,
        "nombre": data.nombre,
        "email": data.email,
        "fecha_registro": fecha
    }

async def crear_usuario2(data):
    # 🔍 Verificar que no exista ya en Redis
    async for key in r.scan_iter(match="usuario:*"):
        tipo = await r.type(key)
        if tipo != b"hash":
            continue
        email = await r.hget(key, "email")
        if email and email.decode() == data.email:
            raise Exception("Correo ya registrado")

    usuario_id = str(uuid.uuid4())
    fecha = datetime.utcnow().isoformat()
    hashed = hash_password(data.password)

    mongo_doc = {
        "_id": usuario_id,
        "nombre": data.nombre,
        "surname": data.surname,
        "username": data.username,
        "email": data.email,
        "password_hash": hashed,
        "fecha_registro": fecha
    }

    usuarios_collection = coleccionUsuarios()
    usuario_hash_key = f"usuario:{usuario_id}"

    try:
        # ✅ Insertar en MongoDB
        await usuarios_collection.insert_one(mongo_doc)
        print("[DEBUG] Insertado en MongoDB")

        # ✅ Insertar en Redis
        await r.hset(usuario_hash_key, mapping=mongo_doc)
        print("[DEBUG] Insertado en Redis")

        return {
            "id": usuario_id,
            "nombre": data.nombre,
            "email": data.email,
            "fecha_registro": fecha
        }

    except Exception as e:
        print(f"[ERROR] Falló alguna inserción: {e}")

        # ⛔ Rollback MongoDB si ya se insertó
        try:
            await usuarios_collection.delete_one({"_id": usuario_id})
            print("[DEBUG] Rollback en MongoDB exitoso")
        except Exception as rollback_mongo_error:
            print(f"[ERROR] Falló rollback MongoDB: {rollback_mongo_error}")

        # ⛔ Rollback Redis si ya se insertó
        try:
            await r.delete(usuario_hash_key)
            print("[DEBUG] Rollback en Redis exitoso")
        except Exception as rollback_redis_error:
            print(f"[ERROR] Falló rollback Redis: {rollback_redis_error}")

        raise Exception("No se pudo crear el usuario completamente")


async def logiar_usuario(data):  # data tiene: username, password
    async for key in r.scan_iter(match="usuario:*"):
        tipo = await r.type(key)
        
        if tipo != b"hash":
            continue  

        username = await r.hget(key, "username")
        if username and username.decode() == data.username:
            password_hash = await r.hget(key, "password_hash")
            if password_hash and pwd_context.verify(data.password, password_hash.decode()):
                datos = await r.hgetall(key)
                usuario_dict = {k.decode(): v.decode() for k, v in datos.items()}
                 # Log de depuración
                print("\n[DEBUG] Datos del usuario desde Redis:", usuario_dict)
                usuario_out_data = {
                    "id": key.decode().split(":")[1],
                    "nombre": usuario_dict.get("nombre"),
                    "surname": usuario_dict.get("surname"),
                    "username": usuario_dict.get("username"),
                    "email": usuario_dict.get("email"),
                    "fecha_registro": usuario_dict.get("fecha_registro"),
                }
                # Log del objeto de salida
                print("[DEBUG] Objeto de salida:", usuario_out_data)
                return UsuarioOut(**usuario_out_data)

    raise Exception("Usuario o contraseña incorrectos")



async def obtener_usuario_por_id(usuario_id: str) -> UsuarioOut:
    clave = f"usuario:{usuario_id}"

    try:
        # Aseguramos que sea un hash (evita WRONGTYPE error)
        tipo = await r.type(clave)
        if tipo.decode() != "hash":
            raise HTTPException(status_code=500, detail=f"La clave {clave} no es un hash de usuario.")

        datos = await r.hgetall(clave)
        if not datos:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Redis devuelve los valores como bytes, los convertimos a str
        datos_decodificados = {k.decode(): v.decode() for k, v in datos.items()}
        datos_decodificados["id"] = usuario_id

        return UsuarioOut(**datos_decodificados)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener usuario: {str(e)}")

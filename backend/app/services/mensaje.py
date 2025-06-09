import redis.asyncio as redis
import json
import uuid
from datetime import datetime
from schemas.mensaje import MensajeOut, MensajeIn
from services.usuario import obtener_usuario_por_id  # importante
from .mongodb import coleccionMensajes

r = redis.Redis()

MAX_MENSAJES = 50

# ✅ Guardar nuevo mensaje (usa lista para mantener orden y limitar tamaño)
async def guardar_mensaje1(data: MensajeIn, usuario_id: str) -> MensajeOut:
    mensaje_id = str(uuid.uuid4())
    fecha = datetime.utcnow().isoformat()

    usuario = await obtener_usuario_por_id(usuario_id)

    mensaje = {
        "id": mensaje_id,
        "usuario_id": usuario_id,
        "sala_id": data.sala_id,
        "contenido": data.contenido,
        "fecha": fecha,
        "username": usuario.username
    }

    clave = f"sala:{data.sala_id}:mensajes"

    # Verifica tipo para evitar corrupción si antes era hash
    tipo = await r.type(clave)
    if tipo not in [b"none", b"list"]:
        raise Exception("Tipo de clave inválido para mensajes")

    await r.lpush(clave, json.dumps(mensaje))
    await r.ltrim(clave, 0, MAX_MENSAJES - 1)
    print("DEBUG RANDOM")

    return MensajeOut(**mensaje)

async def guardar_mensaje(data: MensajeIn, usuario_id: str) -> MensajeOut:
    mensaje_id = str(uuid.uuid4())
    fecha = datetime.utcnow().isoformat()

    usuario = await obtener_usuario_por_id(usuario_id)

    mensaje = {
        "_id": mensaje_id,
        "usuario_id": usuario_id,
        "sala_id": data.sala_id,
        "contenido": data.contenido,
        "fecha": fecha,
        "username": usuario.username
    }
    print(f"[DEBUG] Mensaje :{mensaje}")
    mensajes_collection = coleccionMensajes()  # 🔧 Asegúrate de definir esta función

    
    # Primero guardar en MongoDB
    try:
        await mensajes_collection.insert_one(mensaje)
        print(f"[DEBUG] Mensaje guardado en MongoDB: {mensaje_id}")
    except Exception as e:
        print(f"[ERROR] No se pudo guardar mensaje en MongoDB: {e}")
        raise Exception("Error al guardar el mensaje")
    '''
    # Guardar también en Redis (solo si Mongo fue exitoso)
    clave = f"sala:{data.sala_id}:mensajes"

    try:
        tipo = await r.type(clave)
        if tipo not in [b"none", b"list"]:
            raise Exception("Tipo de clave inválido para mensajes")

        await r.lpush(clave, json.dumps({
            "id": mensaje_id,
            "usuario_id": usuario_id,
            "sala_id": data.sala_id,
            "contenido": data.contenido,
            "fecha": fecha,
            "username": usuario.username
        }))
        await r.ltrim(clave, 0, MAX_MENSAJES - 1)
        print(f"[DEBUG] Mensaje también guardado en Redis (clave: {clave})")
    except Exception as e:
        # Rollback de Mongo si Redis falla
        await mensajes_collection.delete_one({"_id": mensaje_id})
        print(f"[ERROR] Redis falló. Mensaje revertido en MongoDB: {e}")
        raise Exception("Error al guardar el mensaje en Redis")
    ***/
    '''

    return MensajeOut(
        id=mensaje_id,
        usuario_id=usuario_id,
        sala_id=data.sala_id,
        contenido=data.contenido,
        fecha=fecha,
        username=usuario.username
    )


# ✅ Obtener últimos mensajes de la sala (máx 50)
async def obtener_mensajes(sala_id: str, limite: int = 50) -> list[MensajeOut]:
    clave = f"sala:{sala_id}:mensajes"
    tipo = await r.type(clave)
    if tipo == b"none":
        return []

    if tipo != b"list":
        raise Exception("Tipo de clave inválido para mensajes")

    mensajes_raw = await r.lrange(clave, 0, limite - 1)
    mensajes = []
    for m in mensajes:
        print(f'mesajes chat debug: {m}')
    for raw in reversed(mensajes_raw):  # del más viejo al más nuevo
        try:
            data = json.loads(raw)
            mensajes.append(MensajeOut(**data))
        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    return mensajes

async def obtener_mensajes2(sala_id: str, limite: int = 50) -> list[MensajeOut]:
    mensajes_collection = coleccionMensajes()  # 🔧 Asegúrate de tener esta función

    try:
        cursor = mensajes_collection.find(
            {"sala_id": sala_id},
            sort=[("fecha", 1)],  # orden ascendente: más antiguos primero
            limit=limite
        )
        mensajes = []
        async for doc in cursor:
            doc["id"] = doc.pop("_id")  # Mongo guarda el ID como "_id"
            mensajes.append(MensajeOut(**doc))
        return mensajes
    except Exception as e:
        print(f"[ERROR] No se pudieron obtener los mensajes de MongoDB: {e}")
        return []



## ------------------- Funciones no adaptadas aun para list


async def editar_mensaje(sala_id: str, mensaje_id: str, nuevo_contenido: str, usuario_id: str):
    clave = f"sala:{sala_id}:mensajes"
    tipo = await r.type(clave)
    if tipo != b"hash":
        raise Exception("La clave de mensajes no es de tipo hash")

    mensaje_raw = await r.hget(clave, mensaje_id)
    if not mensaje_raw:
        raise Exception("Mensaje no encontrado")

    mensaje = json.loads(mensaje_raw.decode())
    if mensaje["usuario_id"] != f"usuario:{usuario_id}":
        raise Exception("No puedes editar este mensaje")

    mensaje["contenido"] = nuevo_contenido
    await r.hset(clave, mensaje_id, json.dumps(mensaje))
    return {"mensaje": "Mensaje editado"}

async def eliminar_mensaje(sala_id: str, mensaje_id: str, usuario_id: str):
    clave = f"sala:{sala_id}:mensajes"
    tipo = await r.type(clave)
    if tipo != b"hash":
        raise Exception("La clave de mensajes no es de tipo hash")

    mensaje_raw = await r.hget(clave, mensaje_id)
    if not mensaje_raw:
        raise Exception("Mensaje no encontrado")

    mensaje = json.loads(mensaje_raw.decode())
    if mensaje["usuario_id"] != f"usuario:{usuario_id}":
        raise Exception("No puedes eliminar este mensaje")

    await r.hdel(clave, mensaje_id)
    return {"mensaje": "Mensaje eliminado"}


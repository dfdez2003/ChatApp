# services/sala_service.py

import uuid
from datetime import datetime
from passlib.context import CryptContext
import redis.asyncio as redis
from fastapi import HTTPException
from .mongodb import coleccionSalas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
r = redis.Redis()

#  Agregar un id de sala a el set de salas del usuario 
async def safe_add_sala_usuario(redis, usuario_id, sala_key): 
    key = f"usuario:{usuario_id}:salas"             # Set deciado para las salas del usuario    
    tipo = await redis.type(key)                    # Obtenemos el tipo actual de la clave en redis 
    if tipo != b"none" and tipo != b"set":          #  Verificamos, si es none o otro tipo que no sea set mandamos un esception
        raise Exception(f"Conflicto de tipo en {key}. Esperado SET, encontrado {tipo}")
    print(f"[DEBUG] Añadiendo sala {sala_key} al set {key}")
    await redis.sadd(key, sala_key)                 # si esta todo correcto agregamos la clave al set de salas 

# Agregar un id de usuario a el set de usuarios de la sala 
async def safe_add_usuario_sala(redis, sala_id,usuario_key):
    key = f"sala:{sala_id}:usuarios"                     # definimos nuestro set de usuarios 
    tipo = await redis.type(key)                        # Obtenemos el tipo actual de la clave 
    if tipo != b"none" and tipo != b"set":              # Si es diferente de none o de un tipo que sea no set mandamos el exc  
        raise Exception(f"Conflicto de tipo en {key}. Esperado SET, encontrado {tipo}")
    print(f"[DEBUG] Añadiendo usuario {usuario_key} al set {key}")
    await redis.sadd(key, usuario_key)

async def safe_srem(redis, key: str, member: str):
    # Verificar si el miembro existe en el conjunto antes de removerlo
    existe = await redis.sismember(key, member)
    if existe:
        await redis.srem(key, member)
    else:
        print(f"Advertencia: {member} no existe en {key}, no se puede eliminar de Redis.")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Crear sala blindado
async def crear_sala(data, creador_id: str):
    # 🆔 Generamos un ID único para la sala
    sala_id = str(uuid.uuid4())
    fecha = datetime.utcnow().isoformat()
    password_hash = ""
    if data.password:
        password_hash = pwd_context.hash(data.password)
    
    es_publica = "0" if password_hash else "1"
    sala_hash_key = f"sala:{sala_id}"
    sala_usuarios_key = f"sala:{sala_id}:usuarios"
    usuario_salas_key = f"usuario:{creador_id}:salas"
    usuario_key = f"usuario:{creador_id}"

    print(f"[DEBUG] Iniciando creación de sala {sala_id}")
    print(f"[DEBUG] -> HSET en {sala_hash_key}")
    print(f"[DEBUG] -> SET de usuarios en {sala_usuarios_key}")
    print(f"[DEBUG] -> SET de salas del usuario en {usuario_salas_key}")

    # ✅ Validar que no exista otra clave con tipo incompatible
    tipo_sala = await r.type(sala_hash_key)
    if tipo_sala != b"none" and tipo_sala != b"hash":
        raise Exception(f"Conflicto de tipo: {sala_hash_key} ya existe como {tipo_sala}")

    # 📝 Crear sala como HASH
    await r.hset(sala_hash_key, mapping={
        "nombre": data.nombre,
        "descripcion": data.descripcion or "",
        "tiempo_vida": str(data.tiempo_vida) if data.tiempo_vida else "0",
        "creador_id": creador_id,
        "es_publica": "1" if not data.password else "0",
        "password_hash": password_hash,
        "fecha_creacion": fecha,
    })

    # ✅ Agregar la sala al set del usuario (relación inversa)
    tipo_user_salas = await r.type(usuario_salas_key)
    if tipo_user_salas != b"none" and tipo_user_salas != b"set":
        raise Exception(f"Conflicto de tipo en {usuario_salas_key}: tipo {tipo_user_salas}")
    await r.sadd(usuario_salas_key, sala_hash_key)
    print(f"[DEBUG] Añadida sala a {usuario_salas_key} → {sala_hash_key}")

    # ✅ Agregar el usuario al set de usuarios de la sala
    tipo_sala_usuarios = await r.type(sala_usuarios_key)
    if tipo_sala_usuarios != b"none" and tipo_sala_usuarios != b"set":
        raise Exception(f"Conflicto de tipo en {sala_usuarios_key}: tipo {tipo_sala_usuarios}")
    await r.sadd(sala_usuarios_key, usuario_key)
    print(f"[DEBUG] Añadido usuario a {sala_usuarios_key} → {usuario_key}")
    # ⏳ Establecer tiempo de vida (TTL) para la sala y sus mensajes
    try:
        tiempo_vida = int(data.tiempo_vida) if data.tiempo_vida else 2  # horas
        segundos = tiempo_vida * 3600

        await r.expire(sala_hash_key, segundos)                  # expira la sala como hash
        await r.expire(f"sala:{sala_id}:usuarios", segundos)     # expira set de usuarios
        await r.expire(f"sala:{sala_id}:mensajes", segundos)     # expira historial de mensajes
        print(f"[DEBUG] TTL de sala establecido a {segundos} segundos")
    except Exception as e:
        print(f"[ERROR] No se pudo establecer TTL: {str(e)}")

    return {
        "id": sala_id,
        "nombre": data.nombre,
        "creador_id": creador_id,
        "fecha_creacion": fecha,
        "es_publica": data.es_publica
    }

async def crear_sala2(data, creador_id: str):
    # 🆔 Generar ID único
    sala_id = str(uuid.uuid4())
    fecha = datetime.utcnow().isoformat()
    password_hash = pwd_context.hash(data.password) if data.password else ""
    es_publica = not bool(password_hash)

    # 📄 Documento MongoDB
    mongo_doc = {
        "_id": sala_id,
        "nombre": data.nombre,
        "descripcion": data.descripcion or "",
        "tiempo_vida": int(data.tiempo_vida) if data.tiempo_vida else 0,
        "creador_id": creador_id,
        "es_publica": es_publica,
        "password_hash": password_hash,
        "fecha_creacion": fecha
    }

    # 🧠 Insertar en MongoDB
    try:
        salas_collection = coleccionSalas()  # asegúrate de tener esta función
        await salas_collection.insert_one(mongo_doc)
        print("[DEBUG] Sala insertada en MongoDB")
    except Exception as e:
        print(f"[ERROR] No se pudo insertar la sala en MongoDB: {e}")
        raise Exception("Error al guardar sala")

    # 🔐 Llaves Redis
    sala_hash_key = f"sala:{sala_id}"
    sala_usuarios_key = f"sala:{sala_id}:usuarios"
    usuario_salas_key = f"usuario:{creador_id}:salas"
    usuario_key = f"usuario:{creador_id}"

    # 🧠 Insertar en Redis (solo si Mongo fue exitoso)
    try:
        await r.hset(sala_hash_key, mapping={
            "nombre": data.nombre,
            "descripcion": data.descripcion or "",
            "tiempo_vida": str(data.tiempo_vida) if data.tiempo_vida else "0",
            "creador_id": creador_id,
            "es_publica": "1" if es_publica else "0",
            "password_hash": password_hash,
            "fecha_creacion": fecha,
        })

        await r.sadd(usuario_salas_key, sala_hash_key)
        await r.sadd(sala_usuarios_key, usuario_key)

        # ⏳ TTL
        segundos = (int(data.tiempo_vida) if data.tiempo_vida else 2) * 3600
        await r.expire(sala_hash_key, segundos)
        await r.expire(sala_usuarios_key, segundos)
        await r.expire(f"sala:{sala_id}:mensajes", segundos)
        print(f"[DEBUG] TTL aplicado: {segundos}s")
    except Exception as e:
        # ⚠️ Revertir MongoDB si Redis falla
        await salas_collection.delete_one({"_id": sala_id})
        print(f"[ERROR] Redis falló, sala revertida de MongoDB: {e}")
        raise Exception("Error al guardar sala en Redis")

    return {
        "id": sala_id,
        "nombre": data.nombre,
        "creador_id": creador_id,
        "fecha_creacion": fecha,
        "es_publica": es_publica
    }


async def unirse_a_sala(data, user_id: str):
    sala_key = f"sala:{data.sala_id}"

    if not await r.exists(sala_key):
        raise HTTPException(status_code=404, detail="La sala no existe")

    sala_data = await r.hgetall(sala_key)
    sala_dict = {k.decode(): v.decode() for k, v in sala_data.items()}

    # Verificación para salas privadas (con contraseña)
    if sala_dict.get("es_publica") == "0":
        if not data.password:
            raise HTTPException(status_code=403, detail="Se requiere contraseña")
        if not pwd_context.verify(data.password, sala_dict.get("password_hash", "")):
            raise HTTPException(status_code=403, detail="Contraseña incorrecta")

    # Verificación si el usuario ya está en la sala
    ya_esta = await r.sismember(f"sala:{data.sala_id}:usuarios", f"usuario:{user_id}")
    if ya_esta:
        return {"mensaje": "Ya estás en la sala"}

    # Agregar relaciones cruzadas (usuario ↔ sala)
    await safe_add_sala_usuario(r, user_id, f"sala:{data.sala_id}")
    await safe_add_usuario_sala(r, data.sala_id, f"usuario:{user_id}")

    return {"mensaje": "Te uniste a la sala", "sala_id": data.sala_id}

async def unirse_a_sala2(data, user_id: str):
    sala_key = f"sala:{data.sala_id}"

    if not await r.exists(sala_key):
        raise Exception("La sala no existe")

    sala_data = await r.hgetall(sala_key)
    sala_dict = {k.decode(): v.decode() for k, v in sala_data.items()}

    # Verificación para salas privadas (con contraseña)
    if sala_dict["es_publica"] == "0":
        if not data.password:
            raise Exception("Se requiere contraseña")
        if not pwd_context.verify(data.password, sala_dict["password_hash"]):
            raise Exception("Contraseña incorrecta")

    # Verificación si el usuario ya está en la sala
    ya_esta = await r.sismember(f"sala:{data.sala_id}:usuarios", f"usuario:{user_id}")
    if ya_esta:
        return {"mensaje": "Ya estás en la sala"}

    # Agregar la sala al set de salas del usuario y el usuario al set de usuarios de la sala
    await safe_add_sala_usuario(r, user_id, f"sala:{data.sala_id}")
    await safe_add_usuario_sala(r, data.sala_id, f"usuario:{user_id}")

    return {"mensaje": "Te uniste a la sala", "sala_id": data.sala_id}


#  Expulsar usuario blindado
async def expulsar_usuario(sala_id: str, usuario_a_expulsar: str, solicitante_id: str):
    datos = await r.hgetall(f"sala:{sala_id}")
    if not datos:
        raise Exception("La sala no existe")

    sala = {k.decode(): v.decode() for k, v in datos.items()}

    if sala["creador_id"] != solicitante_id:
        raise Exception("Solo el creador puede expulsar usuarios")

    # Validación segura antes de remover
    await safe_srem(r, f"sala:{sala_id}:usuarios", f"usuario:{usuario_a_expulsar}")
    await safe_srem(r, f"usuario:{usuario_a_expulsar}:salas", f"sala:{sala_id}")

    return {"mensaje": f"Usuario expulsado de la sala {sala_id}"}

#  Mostrar salas propias (sin riesgo de corrupción)
async def mostrar_salas_propias(user_id: str):
    claves = await r.smembers(f"usuario:{user_id}:salas")
    salas = []
    for c in claves:
        sala_id = c.decode().split(":")[1]
        datos = await r.hgetall(f"sala:{sala_id}")
        if datos:
            sala = {k.decode(): v.decode() for k, v in datos.items()}

            sala["id"] = sala_id
            #Obtener TTL en segundos
            ttl = await r.ttl(f"sala:{sala_id}")
            sala["tiempo_restante"] = ttl if ttl > 0 else None  # Si no tiene TTL, se asume permanente
            salas.append(sala)
    return {"salas": salas}

#  Mostrar salas públicas aleatorias (sin riesgo de corrupción)
async def mostrar_salas_random(user_id: str):
    salas = []
    async for k in r.scan_iter(match="sala:*"):
        if b":" in k and b"usuarios" not in k and b"mensajes" not in k:
            datos = await r.hgetall(k)
            if datos:
                sala = {k.decode(): v.decode() for k, v in datos.items()}
                # if sala.get("es_publica") == "1":
                sala_id = k.decode().split(":")[1]
                sala["id"] = sala_id
                # Obtener TTL en segundos
                ttl = await r.ttl(f"sala:{sala_id}")
                sala["tiempo_restante"] = ttl if ttl > 0 else None

                salas.append(sala)
    salas.sort(key=lambda x: x.get("fecha_creacion", ""), reverse=True)
    return {"salas": salas}

async def obtener_usuario(user_id: str):
    """
    Obtiene los datos de un usuario específico de manera segura.
    Solo accede a la clave usuario:id_user y valida el tipo de dato.
    
    Args:
        user_id (str): ID del usuario a obtener
        
    Returns:
        dict: Datos del usuario o None si no existe
    Raises:
        Exception: Si hay conflicto de tipos de datos
    """
    user_key = f"usuario:{user_id}"
    
    # Verificar el tipo de dato primero
    key_type = await r.type(user_key)
    
    # Solo permitimos hash o none (si no existe)
    if key_type != b"none" and key_type != b"hash":
        raise Exception(f"Conflicto de tipo en {user_key}. Esperado HASH, encontrado {key_type}")
    
    # Si no existe, retornar None
    if key_type == b"none":
        return None
    
    # Obtener todos los campos del hash
    user_data = await r.hgetall(user_key)
    
    # Convertir bytes a strings
    decoded_data = {k.decode(): v.decode() for k, v in user_data.items()}
    
    # Añadir el ID del usuario al resultado
    decoded_data["id"] = user_id
    
    return decoded_data

async def eliminar_sala_completa(sala_id: str, solicitante_id: str):
    """
    Elimina una sala completamente y todas sus referencias si el solicitante es el creador.
    
    Args:
        sala_id (str): ID de la sala a eliminar
        solicitante_id (str): ID del usuario que solicita la eliminación
        
    Returns:
        dict: Mensaje de confirmación
    Raises:
        Exception: Si hay errores en la validación o eliminación
    """
    # 1. Verificar que la sala existe y el solicitante es el creador
    sala_key = f"sala:{sala_id}"
    datos_sala = await r.hgetall(sala_key)
    
    if not datos_sala:
        raise Exception("La sala no existe")
    
    sala = {k.decode(): v.decode() for k, v in datos_sala.items()}
    
    if sala["creador_id"] != solicitante_id:
        raise Exception("Solo el creador puede eliminar la sala")

    try:
        # 2. Obtener todos los usuarios de la sala
        sala_usuarios_key = f"sala:{sala_id}:usuarios"
        usuarios = await r.smembers(sala_usuarios_key)
        
        # 3. Para cada usuario, eliminar la referencia a esta sala de su set de salas
        for usuario_bytes in usuarios:
            usuario_id = usuario_bytes.decode().split(":")[1]
            usuario_salas_key = f"usuario:{usuario_id}:salas"
            await safe_srem(r, usuario_salas_key, sala_key)
            print(f"✅ Eliminada referencia de sala en usuario {usuario_id}")

        # 4. Eliminar el set de usuarios de la sala
        await r.delete(sala_usuarios_key)
        print(f"✅ Eliminado set de usuarios de la sala {sala_id}")

        # 5. Eliminar el historial de mensajes de la sala
        mensajes_key = f"sala:{sala_id}:mensajes"
        await r.delete(mensajes_key)
        print(f"✅ Eliminado historial de mensajes de la sala {sala_id}")

        # 6. Finalmente, eliminar la sala en sí
        await r.delete(sala_key)
        print(f"✅ Eliminada sala {sala_id}")

        return {
            "mensaje": "Sala eliminada completamente",
            "sala_id": sala_id,
            "usuarios_afectados": len(usuarios)
        }

    except Exception as e:
        print(f"❌ Error eliminando sala: {str(e)}")
        raise Exception(f"Error al eliminar la sala: {str(e)}")

async def obtener_detalles_sala(sala_id: str):
    """
    Obtiene todos los detalles de una sala específica.
    
    Args:
        sala_id (str): ID de la sala a consultar
        
    Returns:
        dict: Datos completos de la sala
    Raises:
        Exception: Si la sala no existe
    """
    sala_key = f"sala:{sala_id}"
    
    # Verificar que la sala existe
    datos = await r.hgetall(sala_key)
    if not datos:
        raise Exception("La sala no existe")
    
    # Convertir los datos de bytes a un diccionario
    sala = {k.decode(): v.decode() for k, v in datos.items()}
    
    # Añadir el ID de la sala al resultado
    sala["id"] = sala_id
    
    # Convertir valores booleanos y numéricos
    sala["es_publica"] = sala["es_publica"] == "1"
    if "tiempo_vida" in sala:
        sala["tiempo_vida"] = int(sala["tiempo_vida"]) if sala["tiempo_vida"] else None
    
    # Eliminar datos sensibles
    if "password_hash" in sala:
        del sala["password_hash"]
        # Obtener TTL restante en segundos
    ttl = await r.ttl(sala_key)

    if ttl >= 0:
        sala["tiempo_restante"] = ttl
    else:
        sala["tiempo_restante"] = None  # No tiene expiración activa


    return sala
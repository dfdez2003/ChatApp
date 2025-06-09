import redis.asyncio as redis
import asyncio
import json
from datetime import datetime
from pymongo import DeleteOne


r = redis.Redis()

async def tarea_limpieza_salas():
    while True:
        print("🔄 Ejecutando limpieza de salas expiradas...")
        try:
            async for key in r.scan_iter("sala:*"):
                key_str = key.decode()

                # Saltar si no es la clave principal (ej: sala:{id}, no sala:{id}:mensajes)
                if ":" in key_str and not key_str.count(":") == 1:
                    continue

                tipo = await r.type(key)
                if tipo != b"hash":
                    continue

                ttl = await r.ttl(key)
                if ttl == -2:  # -2 significa que ya expiró
                    sala_id = key_str.split(":")[1]
                    print(f"🗑️ Sala expirada encontrada: {sala_id}")

                    # Eliminar la sala
                    await r.delete(key)
                    await r.delete(f"sala:{sala_id}:mensajes")

                    # Buscar usuarios que tengan esa sala
                    async for usuario_key in r.scan_iter("usuario:*:salas"):
                        tipo_salas = await r.type(usuario_key)
                        if tipo_salas != b"set":
                            continue
                        await r.srem(usuario_key, f"sala:{sala_id}")

                    print(f"✅ Sala {sala_id} eliminada correctamente.")
        except Exception as e:
            print(f"❌ Error en limpieza de salas: {e}")

        await asyncio.sleep(60)  # Espera 60 segundos antes de repetir



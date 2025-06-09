from motor.motor_asyncio import AsyncIOMotorClient

#Hola amigos aquí irá el script donde manipularemos mongodb para las inserciones o simple conexión con la bd
def conectarMDB():
    try:
        MONGO_URI = "mongodb+srv://ChatApp:chatapp123@cluster0.1qmak.mongodb.net/"
        mongo_client = AsyncIOMotorClient(MONGO_URI)
        mongo_db = mongo_client["ChatApp"]
        usuarios_collection = mongo_db["usuarios"]
        # Intenta contar documentos en la colección
        total_usuarios =  usuarios_collection.count_documents({})
        print(f"✅ Conexión exitosa a MongoDB.")
        return mongo_db
        
    except Exception as e:
        print(f"❌ Error al conectar con MongoDB: {e}")

def coleccionUsuarios():
    bd = conectarMDB()
    return bd["usuarios"]

conectarMDB()



from cohere import AsyncClientV2
from dotenv import load_dotenv
from pathlib import Path
import sys

raiz = Path(__file__).resolve().parent.parent

if str(raiz) not in sys.path:
    sys.path.append(str(raiz))

from conexion import obtener_conexion
from funciones_transacciones import obtener_info
load_dotenv()

co_client = AsyncClientV2()

async def generar_embedding(info, tipo):
    response = await co_client.embed(
        texts=[info],
        model='embed-v4.0',
        output_dimension=1024,
        embedding_types=["float"],
        input_type=tipo #Guardar registro de embedding en base de datos
    )

    return response.embeddings.float_[0]

def guardar_embedding(id, embedding):
    
    with obtener_conexion() as conexion:

        cursor = conexion.cursor()
        consulta = """INSERT INTO transacciones_embeddings(id_transaccion, embedding)
                    VALUES (%s, %s);
        """
        cursor.execute(consulta, (id, embedding))
        


def buscar_similares(id_user: int, vector: list, limite: int = 5):
    
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        consulta = """
                    SELECT te.id_transaccion, t.id_categoria, c.nombre_categoria, t.tipo_movimiento, 
                    t.monto, t.fuente, t.info, t.fecha, 
                    1-(te.embedding <=> %s::vector) AS porcentaje_similitud
                    FROM transacciones_embeddings te
                    JOIN transacciones t ON t.id = te.id_transaccion
                    JOIN categorias c ON c.id = t.id_categoria
                    WHERE t.id_usuario = %s
                    ORDER BY te.embedding <=> %s::vector ASC LIMIT %s
                    """
        
        
        cursor.execute(consulta,(vector, id_user, vector, limite))
        return cursor.fetchall()

def orquestar_embedding_guardado(id_transaccion):
    try:
        info = obtener_info(id_transaccion)
        embedding = generar_embedding(info, "search_document")
        
        guardar_embedding(id_transaccion, embedding)
        return True
    except Exception as e:
        print(f"Error al guardar embedding:{e}")
        return False
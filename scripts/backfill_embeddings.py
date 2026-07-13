import sys
from pathlib import Path

raiz = Path(__file__).resolve().parent.parent

if str(raiz) not in sys.path:
    sys.path.append(str(raiz))

from conexion import obtener_conexion
from services.embeddings import orquestar_embedding_guardado

def actualizar_tabla_embeddings():
    
    with obtener_conexion() as conexion, conexion.cursor() as cursor:

        consulta = """
                    SELECT t.id FROM transacciones t
                    LEFT JOIN transacciones_embeddings te ON te.id_transaccion = t.id
                    WHERE te.id_transaccion IS NULL;
                    """
        cursor.execute(consulta)
        resultados = cursor.fetchall()
        ids_sin_embedding = [r[0] for r in resultados]

        exitosos = 0
        fallos = 0

        for id_trans in ids_sin_embedding:
            try:   
                orquestar_embedding_guardado(id_trans)
                exitosos += 1
            except Exception as e:
                print(f"Error al procesar ID {id_trans}")
                fallos += 1
                continue

    
    print(f"Migracion completada: {exitosos} con exito | {fallos} fallaron")

actualizar_tabla_embeddings()
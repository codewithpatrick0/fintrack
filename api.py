from fastapi import FastAPI
import psycopg2
from conexion import str_conexion
from transacciones_modelo import Transacciones

app = FastAPI()

@app.get('/transacciones', response_model=list[Transacciones])
def obtener_transacciones():

    conexion = psycopg2.connect(str_conexion)
    cursor = conexion.cursor()

    consulta = "SELECT id, id_usuario, id_categoria, tipo_movimiento, monto, fuente, info FROM transacciones"

    cursor.execute(consulta)
    filas = cursor.fetchall()

    transacciones = [Transacciones(
        id=fila[0],
        id_usuario=fila[1],
        id_categoria=fila[2],
        tipo_movimiento=fila[3],
        monto=fila[4],
        fuente=fila[5],
        info=fila[6]
        )
    for fila in filas]

    cursor.close()
    conexion.close()
    
    return transacciones

@app.post('/transacciones', response_model=Transacciones)
def crear_transaccion(transaccion: Transacciones):
    
    datos_transaccion = transaccion.model_dump()

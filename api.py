from fastapi import FastAPI, HTTPException
import psycopg2
from conexion import str_conexion
from transacciones_modelo import TransaccionLeer, TransaccionCrear

app = FastAPI()

@app.get('/transacciones', response_model=list[TransaccionLeer])
def obtener_transacciones():

    conexion = psycopg2.connect(str_conexion)
    cursor = conexion.cursor()

    consulta = "SELECT id, id_usuario, id_categoria, tipo_movimiento, monto, fuente, info FROM transacciones"

    cursor.execute(consulta)
    filas = cursor.fetchall()

    transacciones = [TransaccionLeer(
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

@app.post('/transacciones', response_model=TransaccionLeer) #sale
def crear_transaccion(transaccion: TransaccionCrear): #entra
    
    id_usuario_input = transaccion.id_usuario
    id_categoria_input = transaccion.id_categoria
    tipo_movimiento_input = transaccion.tipo_movimiento
    monto_input = transaccion.monto
    fuente_input = transaccion.fuente
    info_input = transaccion.info

    if monto_input <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
    
    if id_categoria_input is None:
        raise HTTPException(status_code=400, detail="La categoria no puede estar vacía")
    
    if tipo_movimiento_input not in ['gasto', 'ingreso', 'ahorro']:
        raise HTTPException(status_code=400, detail="El tipo de movimiento ingresado no es válido")
    conexion = psycopg2.connect(str_conexion)
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO transacciones(id_usuario, id_categoria, tipo_movimiento, monto, fuente, info)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
    """, (id_usuario_input, id_categoria_input, tipo_movimiento_input,
           monto_input, fuente_input, info_input))
    resultado = cursor.fetchone()
    id_generado = resultado[0] if resultado else None
    conexion.commit()

    cursor.close()
    conexion.close()

    return TransaccionLeer(
        id=id_generado,
        id_usuario=id_usuario_input,
        id_categoria=id_categoria_input,
        tipo_movimiento=tipo_movimiento_input,
        monto=monto_input,
        fuente=fuente_input,
        info=info_input
    )

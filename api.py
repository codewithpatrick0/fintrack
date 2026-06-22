from fastapi import FastAPI, HTTPException
import psycopg2
from conexion import str_conexion
from transacciones_modelo import TransaccionLeer, TransaccionCrear
from usuarios_modelo import UsuarioCrear, UsuarioLeer
from passlib.context import CryptContext


app = FastAPI()

pwd_context = CryptContext(schemes=["argon2"], deprecated='auto')

@app.get('/transacciones', response_model=list[TransaccionLeer])
def obtener_transacciones():

    conexion = psycopg2.connect(str_conexion)
    cursor = conexion.cursor()

    consulta = """SELECT t.id, t.id_usuario, t.id_categoria, t.tipo_movimiento, t.monto, t.fuente, t.info 
                FROM transacciones t
                JOIN usuarios u ON u.id = t.id_usuario
                WHERE u.activo = true;
                """

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
    id_asignado = resultado[0] if resultado else None
    conexion.commit()

    cursor.close()
    conexion.close()

    return TransaccionLeer(
        id=id_asignado,
        id_usuario=id_usuario_input,
        id_categoria=id_categoria_input,
        tipo_movimiento=tipo_movimiento_input,
        monto=monto_input,
        fuente=fuente_input,
        info=info_input
    )

@app.get('/usuarios/{id_user}/transacciones', response_model=list[TransaccionLeer])
def obtener_transacciones_por_id(id_user: int):

    conexion = psycopg2.connect(str_conexion)
    cursor = conexion.cursor()

    consulta = """ SELECT t.id, t.id_usuario, t.id_categoria, t.tipo_movimiento, t.monto, t.fuente, t.info 
                FROM transacciones t
                JOIN usuarios u ON u.id = t.id_usuario
                WHERE u.activo = true AND t.id_usuario = %s
                """
    
    cursor.execute(consulta, (id_user,))
    resultados = cursor.fetchall()

    cursor.close()
    conexion.close()

    if resultados:
        transacciones = [TransaccionLeer(
            id=r[0],
            id_usuario=r[1],
            id_categoria=r[2],
            tipo_movimiento=r[3],
            monto=r[4],
            fuente=r[5],
            info=r[6]
        )
        for r in resultados]
        return transacciones
    
    return []

@app.post('/usuarios/registro', response_model=UsuarioLeer)
def registrar_usuario(u: UsuarioCrear):

    nombre_input = u.nombre
    telefono_input = u.telefono
    contraseña = u.contraseña
    
    if len(nombre_input) < 3 or len(nombre_input) > 12:
        raise HTTPException(status_code=400, detail='El nombre supera el límite de caractéres')
    
    if not nombre_input.strip().replace(" ","").isalpha():
        raise HTTPException(status_code=400, detail='El nombre contiene caractéres inválidos')
    
    if len(telefono_input) != 9 or not telefono_input.isdigit():
        raise HTTPException(status_code=400, detail='Teléfono inválido')
    
    contraseña_hasheada = pwd_context.hash(contraseña)

    conexion = psycopg2.connect(str_conexion)
    cursor = conexion.cursor()

    consulta = """
                    INSERT INTO usuarios (nombre, telefono, hash_password)
                    VALUES (%s, %s, %s) RETURNING id;
                """

    cursor.execute(consulta, (nombre_input, telefono_input, contraseña_hasheada))
    resultado = cursor.fetchone()
    id_asignado = resultado[0] if resultado else None
    
    conexion.commit()

    cursor.close()
    conexion.close()


    return UsuarioLeer(
        id=id_asignado,
        nombre=nombre_input,
        telefono=telefono_input,
        activo=True
    )
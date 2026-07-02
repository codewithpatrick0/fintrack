from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from conexion import obtener_conexion
from transacciones_modelo import TransaccionLeer, TransaccionCrear
from usuarios_modelo import UsuarioCrear, UsuarioLeer, UsuarioLogin
from token_modelo import TokenMostrar
from passlib.context import CryptContext
from funciones_tokens import crear_token_acceso,verificar_token_acceso
import jwt


app = FastAPI()

pwd_context = CryptContext(schemes=["argon2"], deprecated='auto')

@app.get("/")
def read_root():
    return {"message": "Fintrack FastApi Activa"}

@app.get('/transacciones', response_model=list[TransaccionLeer])
def obtener_transacciones(id_user: int = Depends(verificar_token_acceso)):

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()

        consulta = """SELECT t.id, t.id_usuario, t.id_categoria, t.tipo_movimiento, t.monto, t.fuente, t.info
                    FROM transacciones t
                    JOIN usuarios u ON u.id = t.id_usuario
                    WHERE u.activo = true;
                    """

        cursor.execute(consulta)
        filas = cursor.fetchall()
        cursor.close()

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

    return transacciones

@app.post('/transacciones', response_model=TransaccionLeer)
def crear_transaccion(transaccion: TransaccionCrear, id_user: int = Depends(verificar_token_acceso)):

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

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO transacciones(id_usuario, id_categoria, tipo_movimiento, monto, fuente, info)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """, (id_usuario_input, id_categoria_input, tipo_movimiento_input,
                monto_input, fuente_input, info_input))
        resultado = cursor.fetchone()
        id_asignado = resultado[0] if resultado else None

        cursor.close()

    return TransaccionLeer(
        id=id_asignado,
        id_usuario=id_usuario_input,
        id_categoria=id_categoria_input,
        tipo_movimiento=tipo_movimiento_input,
        monto=monto_input,
        fuente=fuente_input,
        info=info_input
    )

@app.get('/usuarios/{id_tarnsaccion_user}/transacciones', response_model=list[TransaccionLeer])
def obtener_transacciones_por_id(id_transaccion_user: int, id_user: int = Depends(verificar_token_acceso)):

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()

        consulta = """ SELECT t.id, t.id_usuario, t.id_categoria, t.tipo_movimiento, t.monto, t.fuente, t.info
                    FROM transacciones t
                    JOIN usuarios u ON u.id = t.id_usuario
                    WHERE u.activo = true AND t.id_usuario = %s
                    """

        cursor.execute(consulta, (id_transaccion_user,))
        resultados = cursor.fetchall()
        cursor.close()

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

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()

        consulta = """
                        INSERT INTO usuarios (nombre, telefono, hash_password)
                        VALUES (%s, %s, %s) RETURNING id;
                    """

        cursor.execute(consulta, (nombre_input, telefono_input, contraseña_hasheada))
        resultado = cursor.fetchone()
        id_asignado = resultado[0] if resultado else None
        cursor.close()

    return UsuarioLeer(
        id=id_asignado,
        nombre=nombre_input,
        telefono=telefono_input,
        activo=True
    )


@app.post('/login', response_model=TokenMostrar)
def ingresar(form_data: OAuth2PasswordRequestForm = Depends()):
    
    nombre_input = form_data.username
    pass_input = form_data.password

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()

        consulta = "SELECT id, activo, hash_password FROM usuarios WHERE nombre = %s"
        cursor.execute(consulta, (nombre_input,))

        resultado = cursor.fetchone()
        id_obtenida = resultado[0] if resultado else None
        activo_obtenido = resultado[1] if resultado else None
        hash_obtenida = resultado[2] if resultado else None
        cursor.close()

    error_credenciales_incorrectas = HTTPException(status_code=401, detail="Credenciales incorrectas")
    if id_obtenida is None:
        raise error_credenciales_incorrectas

    if not activo_obtenido:
        raise HTTPException(status_code=401, detail="Usuario inactivo, no puede ingresar")

    if pwd_context.verify(pass_input, hash_obtenida):
        token = crear_token_acceso(id_obtenida, activo_obtenido)
        return TokenMostrar(
            access_token=token,
            token_type="bearer"
        )

    raise error_credenciales_incorrectas

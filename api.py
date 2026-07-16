from fastapi import FastAPI, HTTPException, Depends, status, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.concurrency import run_in_threadpool
from conexion import obtener_conexion
from transacciones_modelo import TransaccionLeer, TransaccionCrear, TransaccionSimilar
from usuarios_modelo import UsuarioCrear, UsuarioLeer
from token_modelo import TokenMostrar
from passlib.context import CryptContext
from funciones_tokens import crear_token_acceso,verificar_token_acceso
import psycopg2
import logging
from balance_modelo import BalanceMostrar, Desglose
from datetime import datetime
from categorias_modelo import CategoriaMostrar, CategoriaCrear, CategoriaEditar
from services.categorizer import deducir_categoria
from funciones_categorias import obtener_categorias_usuario
from services.embeddings import orquestar_embedding_guardado, generar_embedding, buscar_similares

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

pwd_context = CryptContext(schemes=["argon2"], deprecated='auto')

@app.get("/")
def read_root():
    return {"message": "Fintrack FastApi Activa"}

@app.get('/transacciones', response_model=list[TransaccionLeer])
def obtener_transacciones(tipo_movimiento: str | None=None,
                            id_categoria: int | None=None,
                            page: int = 1,
                            page_size: int = 10,
                            id_user: int = Depends(verificar_token_acceso)):
    
    #str de limite y lista de valores dinámica
    limite = " ORDER BY id DESC LIMIT %s OFFSET %s;"
    valores = [id_user]

    offset = (page - 1) * page_size
    
    consulta_principal = """
                SELECT id, id_usuario, id_categoria, tipo_movimiento, monto, fuente, info, fecha FROM transacciones 
                WHERE id_usuario = %s
                """
    
    consulta_categoria = "SELECT id FROM categorias WHERE id = %s;"

    if tipo_movimiento:
        if tipo_movimiento not in ["ingreso", "gasto", "ahorro"]:
            raise HTTPException(status_code=400, detail='El tipo de movimiento es inválido, ingresa otro')
        else:
            consulta_principal += " AND tipo_movimiento = %s"
            valores.append(tipo_movimiento)

    
    with obtener_conexion() as conexion, conexion.cursor() as cursor:
        if id_categoria:
            cursor.execute(consulta_categoria, (id_categoria,))
            resultado = cursor.fetchone()

            id_categoria_obtenida = resultado[0] if resultado else None

            if not id_categoria_obtenida:   
                raise HTTPException(status_code=400, detail='La categoria ingresada no existe')

            if id_categoria_obtenida:     
                consulta_principal += " AND id_categoria = %s"
                valores.append(id_categoria_obtenida)

        consulta_principal += limite
        valores.extend([page_size, offset])

        cursor.execute(consulta_principal, valores)
        resultados = cursor.fetchall()

        transacciones = [TransaccionLeer(
            id=r[0],
            id_usuario=r[1],
            id_categoria=r[2],
            tipo_movimiento=r[3],
            monto=r[4],
            fuente=r[5],
            info=r[6],
            fecha=r[7]
        ) for r in resultados]

        return transacciones

@app.post('/transacciones', response_model=TransaccionLeer)
async def crear_transaccion(
    transaccion: TransaccionCrear, 
    background_tasks: BackgroundTasks,
    id_user: int = Depends(verificar_token_acceso),
    ):

    id_categoria_input = transaccion.id_categoria
    tipo_movimiento_input = transaccion.tipo_movimiento
    monto_input = transaccion.monto
    fuente_input = transaccion.fuente
    info_input = transaccion.info
    fecha_input = transaccion.fecha #None

    if monto_input <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

    if id_categoria_input is None:
        lista_categorias = await run_in_threadpool(obtener_categorias_usuario, id_user)
        respuesta = await deducir_categoria(info_input, lista_categorias)
        id_categoria_input = respuesta.get("id_categoria")

    if tipo_movimiento_input not in ['gasto', 'ingreso', 'ahorro']:
        raise HTTPException(status_code=400, detail="El tipo de movimiento ingresado no es válido")

    with obtener_conexion() as conexion, conexion.cursor() as cursor:

        columnas = ["id_usuario", "id_categoria", "tipo_movimiento", "monto", "fuente", "info"]
        valores = [id_user, id_categoria_input, tipo_movimiento_input, monto_input, fuente_input,info_input]

        if fecha_input is not None:
            columnas.append("fecha")
            valores.append(fecha_input)
            

        consulta = f"INSERT INTO transacciones ({', '.join(columnas)}) VALUES ({', '.join(['%s'] * len(valores))}) RETURNING id, fecha"

        cursor.execute(consulta, valores)
        resultado = cursor.fetchone()
        id_asignado = resultado[0] if resultado else None
        fecha_recibida = resultado[1] if resultado else None

    if id_asignado:
        background_tasks.add_task(orquestar_embedding_guardado, id_asignado)

    return TransaccionLeer(
        id=id_asignado,
        id_usuario=id_user,
        id_categoria=id_categoria_input,
        tipo_movimiento=tipo_movimiento_input,
        monto=monto_input,
        fuente=fuente_input,
        info=info_input,
        fecha=fecha_recibida
    )

@app.post('/usuarios/registro', response_model=UsuarioLeer)
def registrar_usuario(u: UsuarioCrear):

    nombre_input = u.nombre
    nombre_usuario_input = u.nombre_usuario
    telefono_input = u.telefono
    contraseña = u.contraseña

    if len(nombre_input) < 3 or len(nombre_input) > 12:
        raise HTTPException(status_code=400, detail='El nombre supera el límite de caractéres')

    if not nombre_input.strip().replace(" ","").isalpha():
        raise HTTPException(status_code=400, detail='El nombre contiene caractéres inválidos')

    if len(telefono_input) != 9 or not telefono_input.isdigit():
        raise HTTPException(status_code=400, detail='Teléfono inválido')

    contraseña_hasheada = pwd_context.hash(contraseña)

    try:
        with obtener_conexion() as conexion, conexion.cursor() as cursor:

            consulta = """
                            INSERT INTO usuarios (nombre, nombre_usuario, telefono, hash_password)
                            VALUES (%s, %s, %s, %s) RETURNING id;
                        """

            cursor.execute(consulta, (nombre_input, nombre_usuario_input, telefono_input, contraseña_hasheada))
            resultado = cursor.fetchone()
            id_asignado = resultado[0] if resultado else None

        return UsuarioLeer(
            id=id_asignado,
            nombre=nombre_input,
            nombre_usuario=nombre_usuario_input,
            telefono=telefono_input,
            activo=True
        )
    except psycopg2.errors.UniqueViolation as e: # Retorna psycopg2.errors.UniqueViolation 
        logger.info(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail='Nombre de usuario o teléfono ya existente')

@app.post('/login', response_model=TokenMostrar)
def ingresar(form_data: OAuth2PasswordRequestForm = Depends()):
    
    nombre_usuario_input = form_data.username
    pass_input = form_data.password

    with obtener_conexion() as conexion, conexion.cursor() as cursor:

        consulta = "SELECT id, activo, hash_password FROM usuarios WHERE nombre_usuario = %s"
        cursor.execute(consulta, (nombre_usuario_input,))

        resultado = cursor.fetchone()
        id_obtenida = resultado[0] if resultado else None
        activo_obtenido = resultado[1] if resultado else None
        hash_obtenida = resultado[2] if resultado else None

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

@app.get('/balance', response_model=BalanceMostrar)
def obtener_balance(fecha_inicio: datetime, fecha_final: datetime, id_user: int = Depends(verificar_token_acceso)):
    
    if fecha_inicio > fecha_final:
        raise HTTPException(status_code=400, detail="La fecha de inicio no puede ser posterior a la fecha final.")

    with obtener_conexion() as conexion, conexion.cursor() as cursor:

        consulta = "SELECT tipo_movimiento, SUM(monto) AS Total FROM transacciones WHERE id_usuario = %s AND fecha BETWEEN %s AND %s GROUP BY tipo_movimiento;"
        cursor.execute(consulta, (id_user, fecha_inicio, fecha_final))
        resultado = cursor.fetchall()

        balance = 0
        desglose = []
        if resultado:
            for r in resultado:
                tipo_movimiento = r[0]
                total= r[1]

                if tipo_movimiento == "ingreso":
                    balance += total
            
                if tipo_movimiento == "gasto":
                    balance -= total
                desglose.append(Desglose(tipo_movimiento=tipo_movimiento, monto_total=total))
            
            return BalanceMostrar(desglose=desglose, balance=balance)
    
        return BalanceMostrar(desglose=[], balance=0.0)
    
@app.get('/categorias', response_model=list[CategoriaMostrar])
def mostrar_categorias(id: int = Depends(verificar_token_acceso)):

    consulta = "SELECT id, id_usuario, nombre_categoria FROM categorias WHERE (id_usuario IS NULL OR id_usuario = %s) AND activo = TRUE;"
    
    with obtener_conexion() as conexion, conexion.cursor() as cursor:
        cursor.execute(consulta, (id,))

        resultados = cursor.fetchall()
    
        categorias = [CategoriaMostrar(
            id=r[0],
            id_usuario=r[1],
            nombre_categoria=r[2]
        ) for r in resultados]

        return categorias

@app.post('/categorias', response_model= CategoriaMostrar)
def crear_categoria(c: CategoriaCrear, id: int = Depends(verificar_token_acceso)):

    nombre_categoria_input = c.nombre_categoria

    consulta = "INSERT INTO categorias(id_usuario, nombre_categoria) VALUES (%s, %s) RETURNING id;"
    valores = [id, nombre_categoria_input]

    try:
        with obtener_conexion() as conexion, conexion.cursor() as cursor:
            cursor.execute(consulta, valores)
            resultados = cursor.fetchone()

            id_obtenido = resultados[0] if resultados else None

            return CategoriaMostrar(
                id=id_obtenido,
                id_usuario=id,
                nombre_categoria=nombre_categoria_input
            )
        
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail='Ya tienes una categoría creada con ese nombre')
    
@app.put('/categorias', response_model=CategoriaMostrar)
def editar_categoria(c: CategoriaEditar, id_user: int = Depends(verificar_token_acceso)):
    nombre_a_buscar = c.nombre_categoria
    nuevo_nombre = c.nuevo_nombre_categoria
    consulta = "UPDATE categorias SET nombre_categoria = %s WHERE nombre_categoria = %s AND id_usuario = %s RETURNING id;"

    with obtener_conexion() as conexion, conexion.cursor() as cursor:
        cursor.execute(consulta, (nuevo_nombre, nombre_a_buscar, id_user))

        resultado = cursor.fetchone()

        if not resultado:
            raise HTTPException(status_code=404, detail='La categoría no existe o no te pertenece')
        
        id_extraido = resultado[0] if resultado else None

        return CategoriaMostrar(
            id=id_extraido,
            id_usuario=id_user,
            nombre_categoria=nuevo_nombre
        )
    
@app.delete('/categorias/{nombre}')
def eliminar_categoria(nombre:str, id: int = Depends(verificar_token_acceso)):

    consulta_id_sin_categoria = """
                    SELECT id FROM categorias WHERE nombre_categoria = 'Sin categoria' AND id_usuario IS NULL;
                            """
    consulta_one = """
                    UPDATE transacciones AS t SET id_categoria = %s
                    FROM categorias AS c WHERE t.id_categoria = c.id AND
                    c.nombre_categoria = %s AND t.id_usuario = %s;
                    """
    consulta_two = """UPDATE categorias SET activo = FALSE WHERE activo = TRUE 
                    AND (nombre_categoria = %s  AND id_usuario = %s) RETURNING nombre_categoria;
                    """
    
    with obtener_conexion() as conexion, conexion.cursor() as cursor:
        cursor.execute(consulta_id_sin_categoria)
        resultado = cursor.fetchone()
        id_sin_categoria=resultado[0] if resultado else None

        valores_one = [id_sin_categoria, nombre, id]
        valores_two = [nombre, id]

        cursor.execute(consulta_one, valores_one)

        cursor.execute(consulta_two, valores_two)
        resultado = cursor.fetchone()

        if resultado is None:
            raise HTTPException(status_code=404, detail='El nombre de la categoria no existe')

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
@app.get('/transacciones/obtener-transacciones', response_model=list[TransaccionSimilar])
def obtener_similares(similar: str, límite: int = 5, id_user: int = Depends(verificar_token_acceso)):
    
    vector_consulta = generar_embedding(similar, "search_query")
    resultado = buscar_similares(id_user, vector_consulta, límite)

    if not resultado:
        return []

    similares = [TransaccionSimilar(
        id=r[0],
        id_usuario=id_user,
        id_categoria=r[1],
        nombre_categoria=r[2],
        tipo_movimiento=r[3],
        monto=r[4],
        fuente=r[5],
        info=r[6],
        fecha=r[7],
        porcentaje_similitud=r[8]
    ) for r in resultado]

    return similares
from conexion import obtener_conexion

def obtener_categorias_usuario(id: int):
    consulta = "SELECT id, nombre_categoria FROM CATEGORIAS WHERE (id_usuario IS NULL OR id_usuario = %s) AND activo = TRUE;"

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute(consulta, (id,))
        resultado = cursor.fetchall()
        
        return resultado


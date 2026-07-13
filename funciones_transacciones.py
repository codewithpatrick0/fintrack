from conexion import obtener_conexion

def obtener_info(id_transaccion):

    with obtener_conexion() as conexion:
        cursor = conexion.cursor()

        consulta = """
                    SELECT c.nombre_categoria, t.info, t.tipo_movimiento
                    FROM categorias c
                    JOIN transacciones t ON c.id = t.id_categoria
                    WHERE t.id = %s;
                    """
        
        cursor.execute(consulta,(id_transaccion,))
        resultado = cursor.fetchone()

        if resultado:
            categoria, info, tipo_movimiento = resultado
            texto_embedding = f"Transacción con tipo de movimiento de {tipo_movimiento} en la categoría {categoria}: {info}"
            return texto_embedding
        #Manejar en api.py 
        raise ValueError(f"No se encontró información con ese ID de transacción")


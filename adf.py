limite = " ORDER BY t.id DESC LIMIT %s OFFSET %s"

    
consulta_principal = """
                SELECT t.id, t.id_usuario, u.nombre, t.id_categoria, c.nombre_categoria, 
                t.tipo_movimiento, t.monto, t.fuente, t.info, t.fecha FROM transacciones t
                JOIN categorias c ON c.id = t.id_categoria,
                JOIN usuarios u ON u.id = t.id_usuario WHERE t.id_usuario = %s;
                """
consulta_principal += " AND t.tipo_movimiento = %s"
        

consulta_principal += " AND t.id_categoria = %s"
        
        
consulta_principal += limite

print(consulta_principal)
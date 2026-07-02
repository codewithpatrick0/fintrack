from dotenv import load_dotenv
import os
from contextlib import contextmanager
import psycopg2
import logging
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
str_conexion = os.getenv('STRING_NEON_FINTRACK')

@contextmanager
def obtener_conexion():
    conexion = psycopg2.connect(str_conexion)
    try:
        #Pausamos función cogiendo la conexión obtenida
        yield conexion
        
        #Al volver guardamos cambios si se realizó la acción correctamente
        conexion.commit()
    except Exception as e:
        logger.error(f"Error en la base de datos: {e}", exc_info=True)
        #Revierte cambios si en caso no se pudo realizar de manera corercta la acción
        conexion.rollback()
        
        raise HTTPException(status_code=500, detail='Error en la base de datos')
    finally:
        conexion.close()
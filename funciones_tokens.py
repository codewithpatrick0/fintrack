from fastapi import Depends, HTTPException
import logging
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone, timedelta
import jwt
from credenciales_login import SECRET_KEY, ALGORITHM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def crear_token_acceso(id: int, activo: bool) -> str:
    payload = {
        #Datos que viajan dentro del token
        "sub": str(id),
        "activo": activo,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token_acceso(token: str = Depends(oauth2_scheme)):
    error_token = HTTPException(status_code=401, detail='Token inválido o expirado')
    
    try:
        #Decodificar el token
        datos = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        #Obtener el valor de sub dentro del payload
        id = datos.get("sub")

        if id:
            return id
        raise error_token
    except Exception as e:
        logger.info(f"{e}: Error al verificar el token", exc_info=True)
        raise error_token



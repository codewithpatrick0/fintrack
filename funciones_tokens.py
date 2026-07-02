from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone, timedelta
import jwt
from credenciales_login import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def crear_token_acceso(id: int, activo: bool) -> str:
    payload = {
        #Datos que viajan dentro del token
        "sub": str(id),
        "activo": activo,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(token: str = Depends(oauth2_scheme)):
    #Decodificar el token
    jwt.decode(token)


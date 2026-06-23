from pydantic import BaseModel

class TokenMostrar(BaseModel):
    acceso_token: str
    tipo_token: str
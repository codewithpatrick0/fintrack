from pydantic import BaseModel

class TokenMostrar(BaseModel):
    access_token: str
    token_type: str
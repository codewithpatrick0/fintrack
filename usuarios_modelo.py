from pydantic import BaseModel

class UsuarioCrear(BaseModel):
    nombre: str
    telefono: str
    activo: bool
    hash_password: str

class UsuarioLeer(BaseModel):
    id: int
    nombre: str
    telefono: str
    contraseña: str
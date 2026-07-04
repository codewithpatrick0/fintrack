from pydantic import BaseModel

class UsuarioCrear(BaseModel):
    nombre: str
    nombre_usuario: str
    telefono: str
    contraseña: str

class UsuarioLeer(BaseModel):
    id: int
    nombre: str
    nombre_usuario: str
    telefono: str
    activo: bool


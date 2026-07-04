from pydantic import BaseModel

class CategoriaMostrar(BaseModel):
    id: int
    id_usuario: int | None = None
    nombre_categoria: str

class CategoriaCrear(BaseModel):
    nombre_categoria: str
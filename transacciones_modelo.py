from pydantic import BaseModel

class TransaccionLeer(BaseModel):
    id: int
    id_usuario: int
    id_categoria: int
    tipo_movimiento: str
    monto: float
    fuente: str | None=None
    info: str | None=None

class TransaccionCrear(BaseModel):
    id_usuario: int
    id_categoria: int
    tipo_movimiento: str
    monto: float
    fuente: str | None = None
    info: str | None = None
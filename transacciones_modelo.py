from pydantic import BaseModel

class Transacciones(BaseModel):
    id: int
    id_usuario: int
    id_categoria: int
    tipo_movimiento: str
    monto: float
    fuente: str | None=None
    info: str | None=None

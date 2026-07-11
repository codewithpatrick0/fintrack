from pydantic import BaseModel
import datetime

class TransaccionLeer(BaseModel):
    id: int
    id_usuario: int
    id_categoria: int
    tipo_movimiento: str
    monto: float
    fuente: str | None=None
    info: str | None=None
    fecha: datetime.datetime | None=None

class TransaccionCrear(BaseModel):
    id_categoria: int | None = None
    tipo_movimiento: str
    monto: float
    fuente: str | None = None
    info: str | None = None
    fecha: datetime.datetime | None=None
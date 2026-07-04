from pydantic import BaseModel
from datetime import datetime
class BalancePedir(BaseModel):
    fecha_inicio: datetime
    fecha_final: datetime

class Desglose(BaseModel):
    tipo_movimiento: str
    monto_total: float

class BalanceMostrar(BaseModel):
    desglose = list[Desglose]
    balance = float



from pydantic import BaseModel

class Desglose(BaseModel):
    tipo_movimiento: str
    monto_total: float

class BalanceMostrar(BaseModel):
    desglose: list[Desglose]
    balance: float



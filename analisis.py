from sqlalchemy import create_engine
from conexion import str_conexion
import pandas as pd


engine = create_engine(str_conexion)

consulta_transacciones = "SELECT * FROM transacciones"
consulta_categorias = "SELECT * FROM categorias WHERE id_usuario IS NULL"
consulta_usuarios = "SELECT * FROM usuarios WHERE activo = TRUE"

df_trans = pd.read_sql(consulta_transacciones, con=engine, parse_dates='fecha')
df_cat = pd.read_sql(consulta_categorias, con=engine)
df_users = pd.read_sql(consulta_usuarios, con=engine)

#REPORTE 1:
df_trans['mes'] = df_trans['fecha'].dt.to_period('M')

def obtener_balance_por_mes():
    df_reporte = pd.merge(df_trans, df_users, left_on='id_usuario', right_on='id', how='inner')
    df_reporte = (
        df_reporte.groupby(['id_usuario', 'nombre', 'mes', 'tipo_movimiento'])['monto'].sum()
        .unstack(fill_value=0)
        )
    
    df_reporte['balance'] = df_reporte['ingreso'] - df_reporte['gasto']
    df_reporte.columns.name=None
    print(df_reporte)

obtener_balance_por_mes()

#REPORTE 2
def obtener_montos_por_categoria():
    df_reporte = pd.merge(df_trans, df_cat, left_on='id_categoria', right_on='id', how='inner', suffixes=['_t', '_c'])
    df_reporte = (
        df_reporte.groupby(['id_usuario_t', 'mes', 'nombre_categoria', 'tipo_movimiento'])['monto'].sum()
        .unstack(fill_value=0)
        )
    
    df_reporte.columns.name=None
    print(df_reporte)

obtener_montos_por_categoria()
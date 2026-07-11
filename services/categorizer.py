from groq import AsyncGroq, APIConnectionError, APITimeoutError, APIError
import logging
import sys
from dotenv import load_dotenv
from pathlib import Path
import json
import asyncio
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

raiz = Path(__file__).resolve().parent.parent
if str(raiz) not in sys.path:
    sys.path.append(str(raiz))

from funciones_categorias import obtener_categorias_usuario

client = AsyncGroq()

async def deducir_categoria(info_transaccion : str, lista_categorias : list[tuple[int, str]]):

    prompt_structured = f"""
    # ROL
    eres un deductor de categorías según la lista de categorías que tienes en memoria, la deducción se basa en la info de la transacción ingresada por el usuario en la fastapi de FinTrack
    
    # CONTEXTO
    los usuarios que usan la api de fintrack para registrar sus movimientos (ingresos | ahorros | gastos) a veces solo ponen información y no saben a qué categoría pertenece su transacción, entonces tú tienes que categorizar la transacción según la lista de categorías del usuario
    
    # lista de categorias
    las únicas categorías disponibles son las predeterminadas que la tiene todo usuario y las creadas por el usuario mismo que es distinta según la creación de categorías de cada usuario
    - {lista_categorias}

    #Información ESENCIAL
    La información que debes evaluar y categorizar es {info_transaccion} que es la información ingresada por el usuario para la transacción que creó
    # REGLAS ESTRICTAS
    1. lee estrictamente la información de la transacción del usuario, relaciona las categorías con cada info ingresada, si no se relaciona con alguna de estas establece la categoría predeterminada 'SIN CATEGORIA'
    2. responde EXCLUSIVAMENTE CON UN OBJETO JSON que cumpla en el esquema requerido. NO AÑADAS NADA DEMÁS NI INTRODUCCIONES, ABSOLUTAMENTE NADA, SOLO LA SALIDA QUE TE PIDO (EL OBJETO JSON)

    # ESQUEMA DE SALIDA REQUERIDO (JSON)
    {{"id_categoria": 0}}

    #EJEMPLO
    Sebastián (Usuario de FinTrack) ingresa una transacción con la info que describe que le pagaron en un trabajo de freelance, entonces analizamos eso con las categorías de la lista de categorias y en la lista existe un ID 11 para Trabajo/Ingresos: como retorno:
    {{"id_categoria": 11}}
"""
    id_sin_categoria = next((id for id, nombre_categoria in lista_categorias if nombre_categoria == "Sin categoria"), None)
    
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_structured}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        resultado =  json.loads(response.choices[0].message.content)

        ids_validos = {id for id, _ in lista_categorias}

        if resultado.get("id_categoria") not in ids_validos:
            logger.warning(f"LLM devolvió un ID inválido: {resultado}")
            return {"id_categoria": id_sin_categoria}
        
        return resultado

    except (APIConnectionError, APITimeoutError) as e:
        logger.error(f"Error de conexión con Groq: {e}")
        return {"id_categoria": id_sin_categoria}
    except APIError as e:
        logger.error(f"Error de la API de Groq: {e}")
        return {"id_categoria": id_sin_categoria}
    except json.JSONDecodeError as e:
        logger.error(f"Respuesta de Groq no es JSON válido: {e}")
        return {"id_categoria": id_sin_categoria}
            
lista = obtener_categorias_usuario(4)
respuesta = asyncio.run(deducir_categoria("netflix mensual", lista))
print(respuesta)
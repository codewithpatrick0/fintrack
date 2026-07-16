Case study es · MD
# FinTrack — Estudio de Caso
 
## Descripción general
 
FinTrack es una API REST de finanzas personales construida con FastAPI y PostgreSQL, diseñada para ayudar a los usuarios a rastrear y comprender sus ingresos, ahorros y gastos. Más allá de la funcionalidad CRUD básica, el proyecto evolucionó para incluir categorización automatizada y búsqueda semántica potenciadas por IA, junto con un enfoque de machine learning clásico evaluado (y finalmente no expuesto).
 
Este documento recorre cómo se construyó el proyecto, las decisiones tomadas en el camino, y lo que se aprendió — incluyendo las partes que no funcionaron tan bien como se esperaba.
 
---
 
## El Problema
 
El proyecto nació de mi propia dificultad para llevar el control de mis gastos personales — registraba una transacción y después nunca volvía a categorizarla, lo que hacía inútil cualquier intento posterior de reporte o análisis. Ese es un punto de falla común en el seguimiento de finanzas personales en general: los usuarios registran un gasto pero no lo etiquetan, o son inconsistentes al hacerlo. FinTrack se propuso resolver dos cosas a la vez: darle a los usuarios un lugar confiable y seguro para registrar sus transacciones, y reducir la fricción de categorizarlas — idealmente sin requerir entrada manual cada vez.
 
---
 
## Enfoque Técnico
 
### Fundamento: API y modelo de datos
 
El proyecto comenzó con las dos operaciones más básicas: crear y listar transacciones. Construir eso primero expuso el siguiente requisito real — las transacciones necesitaban pertenecer a un usuario específico y autenticado en lugar de ser visibles globalmente. Eso llevó a implementar autenticación basada en JWT con hashing de contraseñas Argon2, seguido de endpoints de registro e inicio de sesión de usuarios.
 
A partir de ahí, las transacciones se mantuvieron en creación y listado (POST, GET), mientras que se construyó un CRUD completo (POST, GET, PUT, DELETE) para categorías. Mientras se implementaba la eliminación de categorías, surgió un problema de integridad de datos: eliminar una categoría que ya tenía transacciones vinculadas a ella dejaría esas transacciones huérfanas o requeriría eliminaciones en cascada que destruyen el historial. La solución fue un patrón de soft-delete (borrado suave): eliminar una categoría reasigna sus transacciones vinculadas a una categoría por defecto `Sin categoria` y marca la categoría original como inactiva, en lugar de eliminarla de la tabla. Esta misma categoría de respaldo volvió a ser relevante más adelante en el experimento de ML (ver abajo).
 
### Pipeline de datos: fintrack-etl
 
Una vez que la API tenía suficientes datos reales de transacciones, se construyó un proyecto separado — [`fintrack-etl`](https://github.com/codewithpatrick0/fintrack-etl) — para convertir esas transacciones crudas en reportes agregados. Es un pipeline Extract-Transform-Load usando Pandas y SQLAlchemy: lee las transacciones de la base de datos principal, calcula resúmenes mensuales y por categoría, y los escribe de vuelta en dos tablas de reporting dedicadas (`reportes_mensuales`, `reportes_categorias`).
 
El pipeline corre automáticamente vía cron dentro de un contenedor Docker, orquestado con Docker Compose. Lograr que esa automatización funcionara de verdad sacó a la luz varios bugs reales de infraestructura que vale la pena mencionar: un salto de línea faltante al final del archivo crontab impedía silenciosamente que el job corriera; un desfase de zona horaria (UTC vs. hora local) hacía que el job se disparara a la hora equivocada; faltaba el campo de usuario en el formato del archivo `/etc/cron.d/`; y el `$PATH` mínimo de cron no incluía `/usr/local/bin`, lo que rompía la invocación de Python. Ninguno de estos aparece en pruebas locales — solo se manifiestan cuando el job corre desatendido dentro de un contenedor, lo cual fue en sí mismo una lección útil sobre la diferencia entre "funciona cuando yo lo corro" y "funciona en un horario, sin que yo esté mirando".
 
### IA aplicada: tres enfoques, tres compensaciones distintas
 
**1. Categorización basada en LLM (Groq / Llama).**
La primera funcionalidad de IA agregada fue la sugerencia automática de categoría al crear una transacción. Cuando un usuario crea una transacción sin especificar categoría, el sistema envía la descripción de la transacción a un LLM vía Groq, usando prompting estructurado para forzar una respuesta JSON mapeada contra las categorías reales del usuario (no inventadas). La respuesta se valida contra los IDs de categoría reales del usuario antes de confiar en ella — la salida cruda del modelo nunca se inserta directamente en la base de datos. Esto corre de forma asíncrona para no bloquear la solicitud.
 
**2. Búsqueda semántica con RAG (Cohere + pgvector).**
La segunda funcionalidad de IA permite buscar transacciones por significado en lugar de coincidencia exacta de texto — por ejemplo, buscar "suscripciones de streaming" debería mostrar una transacción descrita como "netflix mensual" aunque las palabras no coincidan. Esto se implementó generando embeddings (Cohere `embed-v4.0`, 1024 dimensiones) para la descripción de cada transacción y almacenándolos en PostgreSQL mediante la extensión `pgvector`. Una consulta de búsqueda se convierte en embedding de la misma manera y se compara contra los vectores almacenados usando similitud coseno. La generación de embeddings corre como tarea en segundo plano al crear la transacción, y se escribió un script de backfill para poblar embeddings de datos históricos.
 
**3. ML clásico (scikit-learn) — evaluado, no desplegado.**
Como punto de comparación, se construyó un pipeline de ML clásico para predecir categorías de transacciones usando vectorización TF-IDF y un clasificador Multinomial Naive Bayes, entrenado sobre las propias transacciones categorizadas del usuario (excluyendo `Sin categoria`, ya que no tiene un patrón semántico real que aprender). El modelo se evaluó correctamente con una división estratificada train/test — con la vectorización ajustada solo sobre el conjunto de entrenamiento para evitar fuga de datos (data leakage) — y se midió con `classification_report` y una matriz de confusión, no solo con la exactitud general.
 
---
 
## Decisiones y Compensaciones
 
- **Groq sobre otros proveedores de LLM**: para un proyecto de escala de portafolio, el nivel gratuito y la baja latencia de Groq lo hicieron una elección práctica para prototipar llamadas LLM estructuradas. Esta fue una decisión de costo/disponibilidad en el momento de la implementación, no una afirmación de que Groq sea inherentemente el mejor modelo para la tarea.
- **Soft delete sobre hard delete para categorías**: preserva el historial de transacciones y evita claves foráneas huérfanas, a costa de un poco de lógica adicional en el endpoint de eliminación.
- **Validar la salida del LLM contra datos reales**: la categoría sugerida por el LLM nunca se confía ciegamente — se verifica contra los IDs de categoría reales del usuario, con un respaldo a `Sin categoria` si la sugerencia no coincide con nada real.
- **Mantener el modelo de ML como script independiente, no como endpoint de API**: esta fue la decisión de compensación más importante del proyecto. La evaluación mostró que el modelo no era lo suficientemente confiable para exponerlo a usuarios reales (ver Resultados abajo), y entregar una predicción visiblemente inexacta sería peor que no ofrecer la funcionalidad en absoluto.
---
 
## Resultados y Limitaciones Honestas
 
**RAG / búsqueda semántica** funciona bien para su propósito principal: encontrar la transacción más relevante para una descripción dada logra mostrar de forma confiable la coincidencia correcta en el primer lugar. El ranking más allá del primer resultado es notablemente más débil con descripciones de transacciones cortas, y la búsqueda se degrada aún más cuando la consulta se formula como una pregunta conversacional ("¿cuántas veces me enfermé?") en lugar de una frase descriptiva ("compras en farmacia") — lo cual tiene sentido, ya que los embeddings se construyeron para representar descripciones de transacciones, no para interpretar preguntas.
 
**ML clásico vs. LLM** produjo la comparación más útil del proyecto. Con un dataset real pero modesto (aproximadamente 50 ejemplos por categoría tras la augmentación), el modelo Naive Bayes funcionó bien en categorías con vocabulario distintivo (`comida`, `trabajo`: precisión y recall de 1.00) pero falló en categorías con vocabulario superpuesto o genérico — notablemente `educacion`, que el modelo sobre-predijo como cajón de sastre cada vez que estaba inseguro, y `entretenimiento`, que nunca predijo correctamente (recall de 0.00).
 
La razón subyacente es simple: TF-IDF + Naive Bayes no tiene una comprensión real del significado — depende enteramente de qué palabras son estadísticamente distintivas por categoría en los datos de entrenamiento. Con un dataset pequeño, esa señal estadística es débil e inconsistente. El LLM, en cambio, realiza la misma tarea de categorización zero-shot, sin necesitar datos de entrenamiento en absoluto, porque ya cuenta con un conocimiento amplio del mundo sobre lo que típicamente significan cosas como "Netflix" o "visita al dentista".
 
La conclusión no es que el ML clásico no funcione — sistemas en producción a gran escala usan exactamente este tipo de enfoque con éxito, pero están entrenados con datasets órdenes de magnitud más grandes que lo que un proyecto de portafolio de un solo usuario puede generar realísticamente. Para este proyecto, eso hizo que el enfoque LLM fuera la opción más práctica hoy, mientras que el experimento de ML demuestra la mecánica subyacente y por qué existe esa compensación.
 
---
 
## Limitaciones Conocidas / Próximos Pasos
 
- La plantilla de texto usada para construir los embeddings mezcla texto estructural repetitivo con la descripción real de la transacción, lo que probablemente diluye la señal semántica — vale la pena probar un formato más compacto.
- Las consultas conversacionales (ej. "¿en qué gasté más?") no están soportadas por la configuración actual de RAG, ya que eso requiere agregación más generación de lenguaje natural, no solo búsqueda por similitud — una funcionalidad futura razonable, pero arquitectónicamente distinta de lo que existe hoy.
- Varias llamadas a la base de datos en la API usan el driver síncrono `psycopg2` dentro de endpoints async sin delegarlas a un thread pool, lo que podría bloquear el event loop bajo carga concurrente. Una migración a `asyncpg` resolvería esto correctamente; usar `run_in_threadpool` como parche más rápido también fue evaluado. Pospuesto por no ser crítico para la escala actual del proyecto.

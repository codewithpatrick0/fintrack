# FinTrack API
 
FinTrack is a personal finance tracking system that lets you register and monitor your financial transactions (income, expenses, savings), helping you reach your economic goals efficiently. Beyond basic tracking, it also uses AI to automatically categorize transactions and to search them by meaning instead of exact text.
 
📄 **[Read the full case study](./CASE_STUDY.md)** — the reasoning behind the architecture, the AI approaches evaluated (LLM, RAG, classical ML), and honest results and limitations.
 
## Tech Stack
 
- Python + FastAPI
- PostgreSQL (Neon cloud) + `pgvector` extension for embeddings
- JWT authentication (python-jose)
- Argon2 password hashing (passlib)
- Groq (Llama 3.3) for LLM-based transaction categorization
- Cohere (`embed-v4.0`) for semantic search embeddings
- scikit-learn for a classical ML categorization experiment (evaluated, kept as a standalone script — see case study)
## Available Endpoints
 
| Method | Endpoint | Description | Auth required |
|---|---|---|---|
| POST | `/usuarios/registro` | Register a new user | No |
| POST | `/login` | Login and get JWT token | No |
| GET | `/transacciones` | Get user's transactions (optional filters: `tipo_movimiento`, `id_categoria`, `page`, `page_size`) | Yes |
| POST | `/transacciones` | Create a new transaction. If `id_categoria` is omitted, an LLM (Groq) automatically suggests one based on the transaction's description, validated against the user's real categories | Yes |
| GET | `/transacciones/obtener-transacciones` | Semantic search: given a free-text query (`similar`), returns the user's transactions ranked by meaning-based similarity (Cohere embeddings + pgvector cosine distance), not exact text match | Yes |
| GET | `/balance` | Get income/expense/savings totals for a date range (`fecha_inicio`, `fecha_final`) | Yes |
| GET | `/categorias` | Get system and user's own categories | Yes |
| POST | `/categorias` | Create a custom category | Yes |
| PUT | `/categorias` | Edit a custom category name | Yes |
| DELETE | `/categorias/{nombre}` | Soft-delete a custom category (reassigns transactions to "Sin categoria") | Yes |
 
## AI Features
 
- **Automatic categorization (LLM)**: on transaction creation, if no category is provided, Groq (Llama 3.3) suggests one via structured JSON prompting. The suggestion is validated against the user's actual categories before being trusted, with a fallback to "Sin categoria" if the model's response can't be matched.
- **Semantic search (RAG)**: transaction descriptions are embedded with Cohere and stored in PostgreSQL via `pgvector`. Searches use cosine similarity to find the most relevant transactions by meaning, even without exact keyword matches. Embeddings are generated automatically as a background task on transaction creation, with a backfill script available for historical data (`scripts/backfill_embeddings.py`).
- **Classical ML comparison (scikit-learn)**: a TF-IDF + Naive Bayes classifier was built and evaluated as a comparison point against the LLM approach (`services/categorizer_ml.py`). It's not exposed as an API endpoint — see the [case study](./CASE_STUDY.md) for why, and what the evaluation revealed.
## Running with Docker
 
Make sure you have Docker installed.
 
Required environment variables (create a `.env` file in the project root):
 
```
STRING_NEON_FINTRACK=your_postgresql_connection_string
SECRET_KEY=your_jwt_secret_key
ALGORITHM=HS256
GROQ_API_KEY=your_groq_api_key
COHERE_API_KEY=your_cohere_api_key
```
 
Steps:
 
1. Clone the repository
2. Build the image:
```
   docker build -t fintrack-api .
```
3. Run the container:
```
   docker run -p 8000:8000 --env-file .env fintrack-api
```
 
## Try it live
 
API documentation available at:
https://web-production-46941.up.railway.app/docs
 

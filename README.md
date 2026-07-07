# FinTrack API

FinTrack is a personal finance tracking system that lets you register and monitor 
your financial transactions (income, expenses, savings), helping you reach your 
economic goals efficiently.

## Tech Stack

- Python + FastAPI
- PostgreSQL (Neon cloud)
- JWT authentication (python-jose)
- Argon2 password hashing (passlib)

## Available Endpoints

| Method | Endpoint | Description | Auth required |
|--------|----------|-------------|---------------|
| POST | `/usuarios/registro` | Register a new user | No |
| POST | `/login` | Login and get JWT token | No |
| GET | `/transacciones` | Get user's transactions (optional filters: `tipo_movimiento`, `id_categoria`, `page`, `page_size`) | Yes |
| POST | `/transacciones` | Create a new transaction | Yes |
| GET | `/balance` | Get income/expense/savings totals for a date range (`fecha_inicio`, `fecha_final`) | Yes |
| GET | `/categorias` | Get system and user's own categories | Yes |
| POST | `/categorias` | Create a custom category | Yes |
| PUT | `/categorias` | Edit a custom category name | Yes |
| DELETE | `/categorias/{nombre}` | Soft-delete a custom category (reassigns transactions to "Sin categoria") | Yes |

## Running with Docker

Make sure you have Docker installed.

**Required environment variables** (create a `.env` file in the project root):

STRING_NEON_FINTRACK=your_postgresql_connection_string
SECRET_KEY=your_jwt_secret_key
ALGORITHM=HS256

**Steps:**

1. Clone the repository
2. Build the image:
```bash
   docker build -t fintrack-api .
```
3. Run the container:
```bash
   docker run -p 8000:8000 --env-file .env fintrack-api
```

## Try it live

API documentation available at:  
[https://web-production-46941.up.railway.app/docs](https://web-production-46941.up.railway.app/docs)
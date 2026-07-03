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
| GET | `/transacciones` | Get all transactions | Yes |
| POST | `/transacciones` | Create a new transaction | Yes |
| GET | `/usuarios/{id}/transacciones` | Get transactions by user | Yes |

## Try it live

API documentation available at:  
[https://web-production-46941.up.railway.app/docs](https://web-production-46941.up.railway.app/docs)
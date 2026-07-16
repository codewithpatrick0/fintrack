# FinTrack — Case Study
 
## Overview
 
FinTrack is a personal finance REST API built with FastAPI and PostgreSQL, designed to help users track and understand their income, savings, and expenses. Beyond basic CRUD functionality, the project evolved to include automated categorization and semantic search powered by AI, along with an evaluated (and ultimately unexposed) classical machine learning approach.
 
This document walks through how the project was built, the decisions made along the way, and what was learned — including the parts that didn't work as well as hoped.
 
---
 
## The Problem
 
The project grew out of my own struggle to keep track of my personal expenses — I'd log a transaction and then never bother going back to categorize it, which made any later attempt at reporting or analysis useless. That's a common failure point in personal finance tracking in general: users log an expense but don't label it, or they're inconsistent about it. FinTrack set out to solve two things at once: give users a reliable, secure place to record their transactions, and reduce the friction of categorizing them — ideally without requiring manual input every time.
 
---
 
## Technical Approach
 
### Foundation: API and data model
 
The project started with the two most basic operations: creating and listing transactions. Building those first exposed the next real requirement — transactions needed to belong to a specific, authenticated user rather than being globally visible. That led to implementing JWT-based authentication with Argon2 password hashing, followed by user registration and login endpoints.
 
From there, transactions were kept to creation and listing (POST, GET), while a full CRUD (POST, GET, PUT, DELETE) was built for categories. While implementing category deletion, a data-integrity problem came up: deleting a category that already had transactions linked to it would either orphan those transactions or require cascading deletes that destroy historical data. The fix was a soft-delete pattern — deleting a category reassigns its linked transactions to a default `Sin categoria` ("Uncategorized") category and marks the original category as inactive, instead of removing it from the table. This same fallback category later became relevant again in the ML experiment (see below).
 
### Data pipeline: fintrack-etl
 
Once the API had enough real transaction data, a separate project — [`fintrack-etl`](https://github.com/codewithpatrick0/fintrack-etl) — was built to turn raw transactions into aggregated reports. It's an Extract-Transform-Load pipeline using Pandas and SQLAlchemy: it reads transactions from the main database, computes monthly and per-category summaries, and writes them back into two dedicated reporting tables (`reportes_mensuales`, `reportes_categorias`).
 
The pipeline runs automatically via cron inside a Docker container, scheduled with Docker Compose. Getting that automation actually working surfaced a handful of real infrastructure bugs worth mentioning: a missing trailing newline in the crontab file silently prevented the job from running at all, a UTC-vs-local timezone mismatch caused the job to fire at the wrong hour, the user field was missing from the `/etc/cron.d/` file format, and cron's minimal `$PATH` didn't include `/usr/local/bin`, breaking the Python invocation. None of these show up in local testing — they only appear once the job runs unattended inside a container, which was itself a useful lesson in the gap between "works when I run it" and "works on a schedule, without me watching."
 
### Applied AI: three approaches, three different trade-offs
 
**1. LLM-based categorization (Groq / Llama).**
The first AI feature added was automatic category suggestion on transaction creation. When a user creates a transaction without specifying a category, the system sends the transaction's description to an LLM via Groq, using structured prompting to force a JSON response mapped against the user's real categories (not invented ones). The response is validated against the user's actual category IDs before being trusted — the model's raw output is never inserted directly into the database. This runs asynchronously so it doesn't block the request.
 
**2. Semantic search with RAG (Cohere + pgvector).**
The second AI feature enables searching transactions by meaning rather than exact text match — e.g., searching "streaming subscriptions" should surface a transaction described as "netflix mensual" even though the words don't overlap. This was implemented by generating embeddings (Cohere `embed-v4.0`, 1024 dimensions) for each transaction's description and storing them in PostgreSQL via the `pgvector` extension. A search query is embedded the same way and compared against stored vectors using cosine similarity. Embedding generation runs as a background task on transaction creation, and a backfill script was written to populate embeddings for historical data.
 
**3. Classical ML (scikit-learn) — evaluated, not deployed.**
As a comparison point, a classical ML pipeline was built to predict transaction categories using TF-IDF vectorization and a Multinomial Naive Bayes classifier, trained on the user's own categorized transactions (excluding `Sin categoria`, since it has no real semantic pattern to learn). The model was properly evaluated with a stratified train/test split — with vectorization fit only on the training set to avoid data leakage — and measured with `classification_report` and a confusion matrix, not just overall accuracy.
 
---
 
## Decisions and Trade-offs
 
- **Groq over other LLM providers**: for a portfolio-scale project, Groq's free tier and low latency made it a practical choice for prototyping structured LLM calls. This was a cost/availability decision at the time of implementation, not a claim that Groq is inherently the best model for the task.
- **Soft delete over hard delete for categories**: preserves transaction history and avoids orphaned foreign keys, at the cost of a small amount of extra logic in the delete endpoint.
- **Validating LLM output against real data**: the LLM's suggested category is never trusted blindly — it's checked against the user's actual category IDs, with a fallback to `Sin categoria` if the suggestion doesn't match anything real.
- **Keeping the ML model as a standalone script, not an API endpoint**: this was the most important trade-off decision in the project. The evaluation showed the model was not reliable enough to expose to real users (see Results below), and shipping a visibly inaccurate prediction would be worse than not offering the feature at all.
---
 
## Results and Honest Limitations
 
**RAG / semantic search** works well for its core purpose: finding the most relevant transaction for a given description reliably surfaces the correct top match. Ranking beyond the top result is noticeably weaker with short transaction descriptions, and the search degrades further when the query is phrased as a conversational question ("how many times did I get sick?") rather than a descriptive phrase ("pharmacy purchases") — which makes sense, since the embeddings were built to represent transaction descriptions, not to interpret questions.
 
**Classical ML vs. LLM** produced the most useful comparison in the project. With a real but modest dataset (roughly 50 examples per category after augmentation), the Naive Bayes model performed well on categories with distinctive vocabulary (`comida`, `trabajo`: precision and recall of 1.00) but failed on categories with overlapping or generic vocabulary — notably `educacion`, which the model over-predicted as a catch-all whenever it was uncertain, and `entretenimiento`, which it never predicted correctly (recall of 0.00). 
 
The underlying reason is straightforward: TF-IDF + Naive Bayes has no real understanding of meaning — it relies entirely on which words are statistically distinctive per category in the training data. With a small dataset, that statistical signal is weak and inconsistent. The LLM, by contrast, performs the same categorization task zero-shot, with no training data required at all, because it already has broad world knowledge about what things like "Netflix" or "dentist visit" typically mean.
 
The conclusion isn't that classical ML doesn't work — production systems at scale use exactly this kind of approach successfully, but they're trained on datasets orders of magnitude larger than what a single-user portfolio project can realistically generate. For this project, that made the LLM approach the more practical choice today, while the ML experiment demonstrates the underlying mechanics and why the trade-off exists.
 
---
 
## Known Limitations / Next Steps
 
- The text template used to build embeddings mixes structural boilerplate with the actual transaction description, which likely dilutes the semantic signal — a more compact format is worth testing.
- Conversational queries (e.g., "what did I spend the most on?") aren't supported by the current RAG setup, since that requires aggregation plus natural-language generation, not similarity search alone — a reasonable next feature, but architecturally distinct from what exists today.
- Several database calls in the API use the synchronous `psycopg2` driver inside async endpoints without offloading to a thread pool, which could block the event loop under concurrent load. A migration to `asyncpg` would resolve this properly; using `run_in_threadpool` as a faster patch was also evaluated. Deferred as non-critical for the current project scale.

# Flask Service (Layered, Production-Ready Skeleton)

## Structure
- `app/routes`: Controllers (Flask Blueprints)
- `app/services`: Business use-cases
- `app/repositories`: Persistence layer
- `app/models`: SQLAlchemy ORM models
- `app/schemas`: Marshmallow validation/serialization

## Endpoints
- `GET /health`
- `GET /api/items`
- `GET /api/items/{id}`
- `POST /api/items` (JSON: `{ "name": "example" }`)

## Run locally
1. Create venv + install deps:
   - `python -m venv .venv`
   - `./.venv/Scripts/pip install -r requirements.txt`
2. Set env (PowerShell):
   - `Copy-Item .env.example .env`
   - `setx APP_ENV development`
   - `setx DATABASE_URL "sqlite:///./app.db"`
3. Start:
   - `./.venv/Scripts/python -c "from app import create_app; app=create_app(); app.run(port=8000)"`

## MongoDB (NoSQL)

This project can run without SQL by using MongoDB.

1. Start MongoDB (example with Docker):
   - `docker run --name lotto-mongo -p 27017:27017 -d mongo:7`

2. Set env:
   - `setx DB_BACKEND mongo`
   - `setx MONGODB_URI "mongodb://localhost:27017"`
   - `setx MONGODB_DB "lotto_number_maker"`

3. Import official draws into MongoDB:
   - `./.venv/Scripts/python scripts/import_draws_mongo.py --skip-existing`

### Migrate existing SQL data to Mongo

If you already have data in SQLite/Postgres and want to move it into MongoDB:
- `./.venv/Scripts/python scripts/migrate_sql_to_mongo.py --skip-existing`

Use `--drop-target` only if you want to clear Mongo collections first.

4. Start:
   - `./.venv/Scripts/python -c "from app import create_app; app=create_app(); app.run(port=8000)"`

## Gunicorn (production)
- `gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app`

Notes:
- Tables are created automatically on startup for this example.
- In production, use migrations (e.g., Alembic) instead of `create_all`.

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

## Gunicorn (production)
- `gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app`

Notes:
- Tables are created automatically on startup for this example.
- In production, use migrations (e.g., Alembic) instead of `create_all`.

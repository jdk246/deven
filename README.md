# trust-trace

Chunk 1 sets up a minimal monorepo with:

- `backend/` for the FastAPI API
- `frontend/` for the Vite React TypeScript app

## Local Development

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API starts at `http://localhost:8000`, exposes `GET /health`, and creates its SQLite tables on startup.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend starts at `http://localhost:5173`.

### Docker Compose

```powershell
docker compose up
```

## Demo Flow

Prepare the backend demo data:

```powershell
cd backend
python scripts/prepare_demo_backend.py --reset-db
```

Then start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal you can exercise the public agent API:

```bash
bash backend/scripts/demo_agent_api.sh
```

That demo flow now includes KOL historical alignment refresh plus example agent questions about KOL rankings and track records.

See [backend/API_CONTRACT.md](backend/API_CONTRACT.md) for the API contract used by the frontend, Telegram client, and external integrations.

## Monorepo Layout

```txt
backend/
  app/
    config.py
    db.py
    main.py
    models.py
    schemas.py
  clients/
  data/
  jobs/
  routers/
  services/
  tests/
frontend/
  src/
    api/
    components/
    lib/
    pages/
```

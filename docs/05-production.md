# Phase 5 — Productionization & Vercel Deployment

## Target Architecture: Vercel Serverless
The system is optimized for Vercel deployment:
- **Python Backend**: Executed via Vercel Python Serverless Functions using the entry point `api/index.py` configured in `vercel.json`.
- **Static Frontend**: Pre-built static HTML, CSS, and JS served directly from the `public/` directory via Vercel's Edge static asset CDN.

## `vercel.json` Configuration
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "public/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "public/$1"
    }
  ]
}
```

## Environment Separation & Variables
Configuration is injected via environment variables (documented in `.env.example`):
- `AUTO_RESPOND_CONFIDENCE`: Gate threshold (default `0.70`).
- `DATABASE_URL`: SQLite connection string (default `sqlite:///data/chargebacks.db`).
- `LOG_LEVEL`: Structured log verbosity (`INFO`, `DEBUG`).

## Observability & Health Checks
- **Health Endpoint**: `GET /api/health` returns HTTP 200 with service status.
- **Monitoring Log**: Append-only `results/monitoring_log.jsonl` tracks inference timestamps, confidence scores, evidence scores, and decision distribution.
- **Audit Log**: `decision_audit_logs` table in SQLite maintains permanent record of every decision.

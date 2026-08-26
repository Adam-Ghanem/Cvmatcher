# CVMatcher API

This FastAPI service provides the Phase 1 operational API foundation. Run it from the repository root after copying `.env.example` to `.env` and applying migrations:

```bash
cd services/api
uvicorn app.main:app --reload
```

The service has no CV ingestion, matching, OpenAI, or billing endpoints in Phase 1.

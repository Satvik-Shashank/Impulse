# ADR-001: SQLite with SQLAlchemy ORM for Persistence

## Context
The Chargeback Intelligence Platform requires persistent storage for incoming disputes, generated representment packages, and decision audit logs. The system must support both local development and Vercel serverless deployment without requiring complex infrastructure setup.

## Decision
We choose **SQLite** managed via **SQLAlchemy ORM** (`src/api/storage.py` and `src/db/models.py`).

## Alternatives Considered
1. **PostgreSQL / MySQL**: Require external database provisioning, connection pool management, and credentials management. Over-engineered for local evaluation and serverless demos.
2. **Raw JSON Files**: Lack querying, indexing, and transactional guarantees. Hard to paginate efficiently.

## Consequences
- **Positive**: Zero configuration; zero external dependencies; clean schema definition via SQLAlchemy models; fast read/write operations.
- **Negative**: Concurrency is limited under multi-writer serverless workloads (mitigated via thread-safe connection pooling and gracefully handling database locks).

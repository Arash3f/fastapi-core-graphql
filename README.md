# FastAPI Core GraphQL

A production-oriented Clean Architecture **GraphQL API** starter built with FastAPI, Strawberry, SQLAlchemy, PostgreSQL, and Python. It provides JWT authentication, refresh-token rotation, role-based access control, centralized GraphQL error responses, validated configuration, a committed schema, Docker development, and unit/integration/end-to-end tests.

The FastAPI counterpart of [nestJs-core-graphql](https://github.com/Arash3f/nestJs-core-graphql). Built from [fastapi-core-clean](https://github.com/Arash3f/fastapi-core-clean) with GraphQL-only presentation (health remains on plain HTTP). Patterns follow [family-tree-backend](https://github.com/Arash3f/family-tree-backend).

[![CI](https://github.com/Arash3f/fastapi-core-graphql/actions/workflows/ci.yml/badge.svg)](https://github.com/Arash3f/fastapi-core-graphql/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Highlights

- Clean Architecture layers: domain, application (use cases), infrastructure, and presentation
- GraphQL via Strawberry (GraphiQL outside production); plain HTTP health check
- Signed access and refresh JWTs with independently configured expiration times
- Refresh-token rotation with only the Argon2id hash stored in PostgreSQL
- Device fingerprint binding on login/refresh (User-Agent) to reduce token replay across clients
- Self-service password change (`changeMyPassword`) plus admin password reset
- Public member registration plus admin/member authorization guards
- A single GraphQL error format with stable codes and English/Persian messages in `extensions`
- Auth operation throttling (SlowAPI), database-backed health checks, boot-time development seeding
- Committed `schema.graphql` with CI drift check
- Docker Compose, Poetry, pre-commit (Ruff / mypy / Bandit), and CI on `main` / `develop`

## Technology

| Area | Choice |
|------|--------|
| Runtime | Python 3.11+ |
| Framework | FastAPI + Uvicorn |
| Architecture | Clean Architecture (ports and adapters) |
| GraphQL | Strawberry |
| ORM | SQLAlchemy 2 (asyncio) + asyncpg |
| Migrations | Alembic |
| Authentication | python-jose (JWT) + passlib Argon2 |
| Validation | Pydantic v2 |
| Config | pydantic-settings |
| Testing | Pytest + pytest-asyncio + httpx |
| Tooling | Poetry, Ruff, mypy, Bandit, Commitizen, pre-commit |

## Architecture

```
GraphQL request
  -> Trace ID middleware
  -> Auth throttle (login / register / refresh)
  -> Resolver + guards
  -> Application use case
  -> Domain ports
  -> Infrastructure adapters (SQLAlchemy, JWT, Argon2)
  -> PostgreSQL

Any AppException
  -> normalized GraphQL error extensions

HTTP GET /health
  -> plain HTTP readiness (not GraphQL)
```

```
app/
  domain/           # entities, exceptions, repository ports, value objects
  application/      # use cases, DTOs, interfaces (UoW, TokenService)
  infrastructure/   # SQLAlchemy models/repos, JWT/Argon2, seed
  presentation/
    graphql/        # Strawberry schema, resolvers, types, auth helpers
    common/         # shared error/language helpers when present
  core/             # settings, throttle
  utils/            # AppException, ErrorCode
migrations/
tests/
  unit/
  integration/
  e2e/
schema.graphql      # committed GraphQL schema (regenerate via scripts/export_schema.py)
```

## API

GraphQL is served at `/graphql`. Outside production, GraphiQL is available at the same path. The committed schema lives at `schema.graphql`.

| Operation | Type | Access | Purpose |
|-----------|------|--------|---------|
| me | Query | Logged in | Read the current profile |
| users | Query | Admin | Filter, sort, and paginate users |
| login | Mutation | Public, throttled | Create an access/refresh token pair |
| register | Mutation | Public, throttled | Register a member and sign in |
| refreshToken | Mutation | Public, throttled | Rotate a valid refresh token |
| logout | Mutation | Logged in | Revoke the stored refresh token |
| changeMyPassword | Mutation | Logged in | Replace the caller's password after verifying the current one |
| changePassword | Mutation | Admin | Replace a user's password and revoke refresh access |
| updateMe | Mutation | Logged in | Change the current user's name or username |
| createUser | Mutation | Admin | Create a member or admin |
| updateUser | Mutation | Admin | Change profile, role, or active state |
| deleteUser | Mutation | Admin | Soft-delete a user and revoke refresh access |

Plain HTTP:

| Method | Path | Access | Purpose |
|--------|------|--------|---------|
| GET | /health | Public | Process and database readiness |

Send `Authorization: Bearer <access_token>` on GraphQL requests. Device binding uses the `User-Agent` header.

`users` accepts an optional `input` with filters and pagination:

| Argument | Field | Type | Behavior |
|----------|-------|------|----------|
| input.filters | username | string | Optional filter |
| input.filters | name | string | Optional filter |
| input.filters | role | Admin or Member | Optional exact role |
| input.filters | active | boolean | Optional exact active state |
| input | page | number | Page number; default 1 |
| input | pageSize | number | Page size; default 20 |

Example:

```graphql
query {
  users(
    input: {
      filters: { role: Member, active: true }
      page: 1
      pageSize: 20
    }
  ) {
    total
    page
    pageSize
    items {
      id
      username
      role
    }
  }
}
```

### Shared responses

Health:

```json
{
  "status": "ok",
  "database": "ok",
  "timestamp": "2026-01-01T00:00:00+00:00"
}
```

Domain errors are normalized into GraphQL error extensions (including a Persian translation):

```json
{
  "message": "The username or password is incorrect",
  "extensions": {
    "path": "/graphql",
    "statusCode": 400,
    "code": "INVALID_CREDENTIALS",
    "message": "The username or password is incorrect",
    "persianTranslation": "...",
    "timestamp": "2026-01-01T00:00:00+00:00"
  }
}
```

GraphiQL / introspection tooling is disabled when `APP_ENV=production`.

## Authentication model

1. Login or registration issues an access token and a longer-lived refresh token.
2. Both tokens contain the user ID, username, role, and device fingerprint and are verified with the configured JWT secret.
3. Resolver guards query the database to enforce the user's current active state and role.
4. Refresh validates the JWT, current user state, device fingerprint, and stored Argon2id hash before rotating the pair.
5. Logout, password replacement (admin or self-service), and soft deletion clear the stored refresh-token hash.

The current schema stores one refresh-token hash per user, so a later login replaces the previous refresh session. Access tokens are stateless and remain valid until expiry unless the user is deactivated. Use TLS everywhere and keep access-token lifetimes short.

Default auth throttling uses `THROTTLE_TTL_SECONDS` / `THROTTLE_LIMIT`. Throttling is skipped automatically when `APP_ENV=test`.

## Getting started

### Prerequisites

- Python 3.11+
- Poetry 2+ (or pip + `requirements.txt`)
- PostgreSQL 15 or newer, unless using Docker
- Docker Engine with Compose, for the container workflow

### Local development

```bash
git clone https://github.com/Arash3f/fastapi-core-graphql.git
cd fastapi-core-graphql
poetry run python scripts/setup_dev.py
```

`setup_dev.py` runs `poetry install`, creates `.env` from `.env.example` when missing, and installs Git hooks (`pre-commit`, `pre-push`, `commit-msg`) into this clone.

Set `APP_ENV=development`, replace `JWT_SECRET`, configure the database values, and review all seed credentials in `.env`. Never deploy the sample admin/member passwords.

```bash
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Default local URLs:

- GraphQL (GraphiQL): `http://localhost:8000/graphql`
- Health: `http://localhost:8000/health`

Default seeded users (when `SEED_ON_BOOT=true` and users are missing):

| Username | Password | Role |
|----------|----------|------|
| admin | admin | Admin |
| member | member | Member |

Seed only **creates** missing users; it does not overwrite existing passwords on every boot.

### Docker

```bash
cp .env.example .env
docker compose up --build
```

Root compose publishes API on **8002** and Postgres on **5434**.

### Docker development (hot reload)

```bash
cp docker/develop/.docker.dev.sample.env docker/develop/.docker.dev.env
cp docker/develop/.env.docker.dev.sample docker/develop/.env.docker.dev
docker compose -f docker/develop/docker-compose-develop.yml up -d --build
```

API: `http://localhost:8002` · Postgres host port: `5439` · GraphQL: `http://localhost:8002/graphql` · Health: `http://localhost:8002/health`.

```bash
docker compose -f docker/develop/docker-compose-develop.yml logs -f
docker compose -f docker/develop/docker-compose-develop.yml down
```

To remove the development database volume as well:

```bash
docker compose -f docker/develop/docker-compose-develop.yml down -v
```

## Environment variables

The application validates configuration through pydantic-settings. Templates: `.env.example` and `.env.test.example`.

| Group | Variables |
|-------|-----------|
| Runtime | `APP_ENV`, `APP_VERSION`, `SERVER_HOST`, `SERVER_PORT` |
| Browser access | `CORS_ORIGINS` |
| Throttling | `THROTTLE_TTL_SECONDS`, `THROTTLE_LIMIT` |
| JWT | `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| Database | `POSTGRES_*` and `POSTGRES_*_TEST` |
| Seed | `SEED_ON_BOOT`, `SUPER_USER_*`, `MEMBER_USER_*` |

`APP_ENV` must be one of `development`, `production`, or `test`. `CORS_ORIGINS` accepts `*` or a comma-separated list. Keep `SEED_ON_BOOT=false` in production unless startup seeding is deliberately required. GraphiQL is disabled when `APP_ENV=production`.

Regenerate the committed schema after GraphQL type changes:

```bash
poetry run python scripts/export_schema.py
```

## Commands

| Command | Purpose |
|---------|---------|
| `poetry run uvicorn app.main:app --reload` | Development server |
| `poetry run alembic upgrade head` | Apply migrations |
| `poetry run python scripts/export_schema.py` | Regenerate `schema.graphql` |
| `poetry run pytest` | Run all tests with coverage |
| `poetry run ruff check app tests` | Lint |
| `poetry run mypy app` | Type check |
| `poetry run bandit -r app -ll` | Security scan |
| `poetry run cz commit` | Commitizen / gitmoji commit |
| `poetry run python scripts/setup_dev.py` | Install deps, `.env`, and Git hooks |

## Testing

```bash
cp .env.test.example .env.test
poetry run python scripts/create_test_db.py
poetry run alembic upgrade head
poetry run pytest
```

Prepare a dedicated disposable test database. Never point `.env.test` at development or production data.

- **Unit** — mocked Unit of Work; no database required (`tests/unit`)
- **Integration** — real PostgreSQL test database (`tests/integration`)
- **E2E** — full ASGI app over httpx against `/graphql` (`tests/e2e`)

When `schema.graphql` changes, regenerate and commit it:

```bash
poetry run python scripts/export_schema.py
```

CI regenerates the schema and fails if it drifts from the committed file, then runs Ruff, mypy, Bandit, and Pytest on `main` and `develop`.

## Production readiness notes

This project is a strong starter, not a complete production platform. Before deploying it publicly:

- Add a production container/build target, deployment manifests, graceful shutdown, and a real secrets manager
- Disable boot seeding and replace every sample credential and secret
- Restrict CORS and configure proxy trust for the exact deployment topology
- Add issuer/audience JWT claims, key rotation, and a session table if concurrent sessions are required
- Add refresh-token reuse detection and an access-token revocation strategy where the risk model requires immediate logout
- Tune GraphQL depth/complexity limits for your schema and traffic profile
- Add structured logs, metrics/tracing, dependency scanning, and automated backups
- Add account recovery, email verification, MFA, audit logs, and explicit account lockout according to product requirements

## Related projects

| Project | Description |
|---------|-------------|
| [fastapi-core-clean](https://github.com/Arash3f/fastapi-core-clean) | Same core, REST + GraphQL |
| [fastapi-core-rest](https://github.com/Arash3f/fastapi-core-rest) | Same core, REST only |
| [nestJs-core-graphql](https://github.com/Arash3f/nestJs-core-graphql) | NestJS GraphQL counterpart |
| [family-tree-backend](https://github.com/Arash3f/family-tree-backend) | Full FastAPI product built on these patterns |

## Contributing

1. Create a focused branch
2. Add or update tests with the change
3. Run Ruff, mypy, and the relevant tests
4. Regenerate `schema.graphql` when GraphQL types change
5. Use Commitizen (`poetry run cz commit`)
6. Open a pull request against `develop` or `main`

See [CONTRIBUTING.md](CONTRIBUTING.md) for details. CI validates pushes and pull requests to `main` and `develop`.

## License

Released under the MIT License.

## Author

Arash Alfooneh — [@Arash3f](https://github.com/Arash3f)

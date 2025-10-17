# AI Hedge Fund Platform - Architecture

## System Overview

A production-grade financial data platform combining:
- **Public Data API**: SEC EDGAR data normalization and delivery (FinancialDatasets.ai clone)
- **AI Hedge Fund Dashboard**: Strategy development, backtesting, and portfolio management
- **Execution Layer**: IBKR paper/live trading with risk controls

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
├─────────────────┬──────────────────┬────────────────────────────┤
│  Next.js Web    │  AI Dashboard    │   Admin Portal             │
│  (Public Site)  │  (Strategies)    │   (Internal)               │
└────────┬────────┴────────┬─────────┴─────────┬──────────────────┘
         │                 │                   │
         └─────────────────┼───────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────────┐
│                      API Gateway Layer                            │
├───────────────────────────────────────────────────────────────────┤
│  FastAPI (v1)  │  Auth/JWT  │  Rate Limiting  │  Usage Metering  │
└────────┬───────┴────────────────────────────────────────────────┬┘
         │                                                         │
┌────────┴─────────────────────────────────────────────────┬──────┴─┐
│               Application Services                        │        │
├───────────────────────────────────────────────────────────┤        │
│ Companies  │ Filings  │ Statements │ 13F │ Signals       │ Billing│
└────────┬───────────────────────────────────────────────────┬──────┘
         │                                                    │
┌────────┴────────────────────────────────┬─────────────────┴───────┐
│          Data Layer                     │    External Services    │
├─────────────────────────────────────────┼─────────────────────────┤
│ Postgres (primary)                      │ Stripe (billing)        │
│ Redis (cache/queues)                    │ SEC EDGAR APIs          │
│ S3 (raw filings)                        │ IBKR (execution)        │
└─────────────────────────────────────────┴─────────────────────────┘
         ▲
         │
┌────────┴────────────────────────────────────────────────────────┐
│                    Background Workers                            │
├──────────────────────────────────────────────────────────────────┤
│ Ingestor  │ Parser  │ Backfill  │ Signals  │ Webhooks  │ Cleanup │
└──────────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Frontend
- **Framework**: Next.js 14 (App Router, TypeScript)
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: React Query (TanStack Query)
- **Auth**: NextAuth.js (OAuth + JWT)
- **Charts**: Recharts / TradingView Lightweight

### Backend API
- **Framework**: FastAPI (Python 3.11+)
- **Validation**: Pydantic v2
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **Auth**: PyJWT + API keys
- **API Docs**: OpenAPI 3.1 (auto-generated)

### Data Layer
- **Primary DB**: Postgres 15+ (with pgvector optional)
- **Cache**: Redis 7+
- **Storage**: S3-compatible (MinIO for dev, AWS S3 for prod)
- **Search**: Postgres full-text search (upgrade to Elasticsearch if needed)

### Workers
- **Queue**: Redis + RQ (simple) or Celery (if complex workflows)
- **Scheduler**: APScheduler or cron
- **Jobs**: Ingestion, parsing, signals, backfills, webhooks

### Infrastructure
- **IaC**: Terraform (modules per resource)
- **Containers**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: OpenTelemetry + Prometheus + Grafana
- **Logging**: Structured JSON logs + Loki
- **Secrets**: GitHub Secrets (dev), AWS Secrets Manager (prod)

### Third-Party Integrations
- **SEC EDGAR**: Direct API access (rate-limited, cached)
- **Stripe**: Subscriptions + usage-based metering
- **IBKR**: TWS API via ib_insync
- **Dexter** (optional): Function-calling agent framework

## Data Model

### Core Entities

**Companies**
- CIK (primary key from SEC)
- Name, tickers (array), SIC, entity type
- Metadata: filing counts, last updated

**Filings**
- Accession number (unique)
- Form type (10-K, 10-Q, 8-K, 13F, S-1, etc.)
- Filing date, period end date
- URLs: raw HTML, XBRL, exhibits
- Processing status

**Statements** (normalized financial line items)
- Company + filing reference
- Statement type: income, balance, cashflow, equity
- Line item, value, unit, currency
- Fiscal year/quarter, as-of date
- Source: XBRL path or parsed location

**Holdings (13F)**
- Filing reference
- CUSIP, issuer name, ticker (mapped)
- Shares, market value, put/call flag
- Change from prior quarter

**Signals** (derived insights)
- Filing-level events
- Score/confidence, signal type
- Metadata JSON (e.g., late filing, restatement, insider buys)

**Users & Billing**
- Users: email, hashed password, OAuth IDs
- API Keys: user-owned, scoped, rate-limited
- Plans: Free/Pro/Enterprise tiers
- Usage Events: metered API calls, rows returned
- Stripe: customer_id, subscription_id, webhook events

**Trading (OMS)**
- Accounts: IBKR account mapping, paper vs live flag
- Positions: symbol, qty, avg_price, last_updated
- Orders: type, status, timestamps, fills
- Executions: trade details, commissions
- Risk Limits: max position, max notional, blocklists

## API Design

### Versioning
- URL-based: `/v1/...`
- Major version bumps for breaking changes
- Deprecation headers for sunsetting endpoints

### Authentication
- **API Keys**: `X-API-Key` header
- **OAuth/JWT**: `Authorization: Bearer <token>`
- Per-key rate limits + plan entitlements

### Rate Limiting
- Tiered by plan: Free (100/day), Pro (10k/day), Enterprise (unlimited)
- Burst allowance with token bucket
- Return `429 Too Many Requests` with `Retry-After` header

### Pagination
- Cursor-based for large datasets
- `?limit=100&cursor=<token>`
- Response includes `next_cursor`, `has_more`

### Filtering & Sorting
- Query params: `?cik=0001318605&form=10-K&from_date=2020-01-01`
- Support multiple values: `?form=10-K&form=10-Q`
- Sort: `?sort_by=filing_date&order=desc`

### Response Format
```json
{
  "data": [...],
  "meta": {
    "count": 100,
    "next_cursor": "abc123",
    "has_more": true
  },
  "request_id": "uuid"
}
```

### Error Format
```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid CIK format",
    "details": {...}
  },
  "request_id": "uuid"
}
```

## Key Endpoints (v1)

### Companies
- `GET /v1/companies/search?q=<query>` - Search by name/ticker/CIK
- `GET /v1/companies/{cik}` - Company details
- `GET /v1/companies/{cik}/filings` - Company's filings

### Filings
- `GET /v1/filings?cik=&form=&from=&to=` - List filings
- `GET /v1/filings/{accession}` - Filing details + metadata
- `GET /v1/filings/{accession}/raw` - Redirect to raw filing

### Statements
- `GET /v1/statements?cik=&stmt=income&fy=2023&fq=Q1` - Financial statements
- `GET /v1/statements/{filing_id}` - All statements for a filing

### Holdings (13F)
- `GET /v1/holdings/13f?cik=&from=&to=` - 13F holdings
- `GET /v1/holdings/13f/{filing_id}` - Specific 13F

### Signals
- `GET /v1/signals?cik=&kind=&from=&to=` - Derived signals
- `GET /v1/signals/{filing_id}` - Signals for filing

### Factors (computed)
- `GET /v1/factors?cik=&date=&factors=pe,roe,debt_to_equity` - Factor scores

### Usage
- `GET /v1/usage` - Current user's usage stats

## Ingestion Pipeline

### Phases

**1. Discovery**
- Daily cron: fetch new submissions from SEC
- Parse master index for recent filings
- Filter by form types of interest

**2. Download**
- Fetch filing HTML, XBRL, exhibits
- Store raw to S3: `s3://bucket/filings/{cik}/{accession}/`
- Rate limit: 10 req/sec per SEC guidelines
- Retry with exponential backoff

**3. Parsing**
- XBRL: Extract facts using xbrl library
- HTML: BeautifulSoup for 13F tables, 8-K items
- Normalize to internal schema
- Handle multiple GAAP taxonomies

**4. Validation**
- Schema validation (Pydantic models)
- Completeness checks (required fields)
- Duplicate detection (accession + period)

**5. Persistence**
- Upsert to Postgres (idempotent)
- Update company metadata
- Trigger signal computations

**6. Signals**
- Derived metrics: late filings, restatements, abnormal 13F flows
- Store to signals table with scores

### Backfill Strategy
- Start with S&P 500 CIKs
- Last 10 years of 10-K/10-Q
- Last 5 years of 13F (major holders)
- Parallel workers (10-20) with rate limiting coordination (Redis lock)

## Billing & Usage Metering

### Plans
| Tier       | Price    | Requests/day | Rows/response | Features           |
|------------|----------|--------------|---------------|--------------------|
| Free       | $0       | 100          | 100           | Basic API          |
| Pro        | $99/mo   | 10,000       | 1,000         | Full API + support |
| Enterprise | Custom   | Unlimited    | Unlimited     | SLA + webhooks     |

### Metering
- Track per API key: `(key_id, endpoint, count, rows, timestamp)`
- Batch write to Postgres every 1 min
- Report to Stripe Metering API (if usage-based pricing)

### Webhooks (Stripe)
- `customer.subscription.created` → provision API key
- `customer.subscription.updated` → adjust limits
- `customer.subscription.deleted` → revoke key
- `invoice.payment_failed` → suspend account

## Security

### Auth
- Passwords: bcrypt hashed (12 rounds)
- API keys: random 32-byte hex, prefixed (`aihf_live_...`)
- JWT: RS256, 1-hour expiry, refresh tokens (7 days)

### RBAC
- Roles: `user`, `admin`, `internal`
- Permissions: scoped to resources (own data vs all data)

### Secrets
- Never commit to repo
- `.env.example` with placeholders
- Use GitHub Secrets for CI/CD
- AWS Secrets Manager / HashiCorp Vault for prod

### Compliance
- SEC fair use: proper User-Agent, rate limiting, caching
- Data attribution: link to SEC source
- PII: avoid storing user PII beyond email
- Audit logs: track key actions (key creation, plan changes, data access)

## Observability

### Metrics
- **API**: request rate, latency (p50/p95/p99), error rate
- **Workers**: job duration, success/failure rate, queue depth
- **DB**: query time, connection pool usage
- **Cache**: hit rate, eviction rate

### Logging
- Structured JSON: `{"level": "info", "message": "...", "trace_id": "...", ...}`
- Correlation IDs across services
- Levels: DEBUG (dev), INFO (prod), ERROR (always)

### Tracing
- OpenTelemetry SDK
- Trace ingestion → Jaeger (dev) or DataDog (prod)
- Spans: API handlers, DB queries, external calls

### Alerts
- API error rate > 5% for 5min
- Ingestion job failed 3x in a row
- Stripe webhook processing delay > 10min
- DB connections > 80% of pool

## Deployment

### Local Development
```bash
make up              # Start all services (docker-compose)
make migrate         # Run DB migrations
make seed            # Load sample data
make test            # Run test suite
```

### Environments
- **Dev**: Local Docker Compose
- **Staging**: Fly.io or Render (single instance)
- **Prod**: AWS ECS/Fargate (multi-AZ, autoscaling)

### CI/CD
- **PR**: Lint, type-check, unit tests
- **Merge to main**: Integration tests, build Docker images, push to registry
- **Tag (vX.Y.Z)**: Deploy to staging → manual approval → prod

### Infra as Code
- Terraform modules: `infra/terraform/{vpc,db,redis,s3,ecs}`
- State: S3 backend with locking (DynamoDB)
- Secrets: AWS Secrets Manager, injected at runtime

## Repo Structure (Monorepo)

```
AIHedgeFund/
├── apps/
│   ├── web/                 # Next.js public site
│   ├── api/                 # FastAPI backend
│   ├── workers/             # Background jobs
│   └── dashboard/           # AI hedge fund UI (virattt/ai-hedge-fund fork)
├── packages/
│   ├── edgar/               # SEC EDGAR client
│   ├── parsers/             # Filing parsers (XBRL, HTML, 13F)
│   ├── db/                  # Database models + migrations
│   ├── shared/              # Shared utilities (types, validation)
│   └── ibkr/                # IBKR connector
├── infra/
│   ├── terraform/           # IaC modules
│   ├── docker/              # Dockerfiles
│   └── k8s/                 # Kubernetes manifests (if needed)
├── docs/
│   ├── api/                 # API reference (OpenAPI)
│   ├── guides/              # Integration guides
│   └── runbooks/            # Operational runbooks
├── scripts/                 # Utility scripts (seed, backfill, etc.)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── .github/
│   └── workflows/           # CI/CD pipelines
├── docker-compose.yml       # Local dev environment
├── Makefile                 # Common tasks
├── README.md
├── ARCHITECTURE.md          # This file
└── .env.example
```

## Design Decisions

### Why Monorepo?
- Simplified dependency management
- Atomic commits across frontend/backend
- Easier refactoring and type sharing
- Single CI/CD pipeline

### Why FastAPI?
- Native async support (high concurrency)
- Auto-generated OpenAPI docs
- Pydantic validation (type-safe)
- Strong Python ecosystem for data processing
- Compatibility with virattt repos

### Why Postgres?
- ACID guarantees for financial data
- Rich indexing (B-tree, GiST, GIN)
- JSON support for flexible fields
- Mature tooling (pgAdmin, Alembic)
- Optional pgvector for future ML features

### Why Redis?
- Fast caching (API responses, rate limits)
- Simple queue (RQ) for background jobs
- Pub/sub for real-time features (optional)

### Why S3?
- Durable storage for raw filings
- Cost-effective for archives
- Standard interface (MinIO for local dev)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SEC rate limits | High | Aggressive caching, backoff, multiple IPs |
| XBRL complexity | High | Start with key facts, expand iteratively |
| Data quality | Medium | Validation layer, manual QA on samples |
| Stripe integration bugs | Medium | Thorough webhook testing, idempotency |
| IBKR API instability | Low | Paper trading first, extensive error handling |
| Cost overruns | Low | Set budget alerts, optimize queries |

## Future Enhancements
- Real-time filing alerts (WebSockets)
- Alternative data sources (Twitter sentiment, satellite, etc.)
- Advanced ML models (earnings prediction, default risk)
- Multi-broker support (Alpaca, TD Ameritrade)
- Mobile app (React Native)
- Collaborative features (shared strategies, leaderboards)
- Institutional features (white-label, custom data feeds)

## References
- SEC EDGAR: https://www.sec.gov/edgar/sec-api-documentation
- FinancialDatasets.ai: https://www.financialdatasets.ai
- virattt/ai-hedge-fund: https://github.com/virattt/ai-hedge-fund
- virattt/dexter: https://github.com/virattt/dexter
- IBKR API: https://interactivebrokers.github.io/tws-api/

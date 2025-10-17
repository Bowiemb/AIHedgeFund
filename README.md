# AI Hedge Fund Platform

A production-grade AI-powered hedge fund platform combining:
- **Public Data API**: SEC EDGAR data normalization and delivery (FinancialDatasets.ai clone)
- **AI Hedge Fund Dashboard**: Strategy development, backtesting, and portfolio management
- **Execution Layer**: IBKR paper/live trading with risk controls

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- Make (optional, for convenience commands)

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/Bowiemb/AIHedgeFund.git
cd AIHedgeFund

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
make up

# 4. Run database migrations (in another terminal)
make migrate

# 5. Load seed data (optional)
make seed
```

**Services will be available at:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Web: http://localhost:3000
- Adminer (DB UI): http://localhost:8080
- MinIO Console: http://localhost:9001

## 📁 Project Structure

```
AIHedgeFund/
├── apps/
│   ├── web/                 # Next.js public site & dashboard
│   ├── api/                 # FastAPI backend
│   ├── workers/             # Background jobs (ingestion, parsing)
│   └── dashboard/           # AI hedge fund UI (virattt/ai-hedge-fund)
├── packages/
│   ├── edgar/               # SEC EDGAR client
│   ├── parsers/             # Filing parsers (XBRL, HTML, 13F)
│   ├── db/                  # Database models + migrations
│   ├── shared/              # Shared utilities
│   └── ibkr/                # IBKR connector
├── infra/
│   ├── terraform/           # Infrastructure as Code
│   ├── docker/              # Dockerfiles
│   └── k8s/                 # Kubernetes manifests
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── tests/                   # Test suites
└── .github/workflows/       # CI/CD pipelines
```

## 🏗️ Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system design.

**High-level overview:**
```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)  │  Dashboard  │  Admin Portal         │
└──────────────────────┴─────────────┴───────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│  FastAPI (v1)  │  Auth  │  Rate Limiting  │  Usage Meter   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│  Postgres  │  Redis  │  S3  │  Stripe  │  SEC  │  IBKR    │
└───────────────────────────────────────────────────────────── ┘
```

## 🔌 API Endpoints

### Companies
- `GET /v1/companies/search?q=<query>` - Search companies
- `GET /v1/companies/{cik}` - Get company details
- `GET /v1/companies/{cik}/filings` - Get company filings

### Filings
- `GET /v1/filings?cik=&form=&from=&to=` - List filings
- `GET /v1/filings/{accession}` - Get filing details

### Statements
- `GET /v1/statements?cik=&stmt=&fy=&fq=` - Financial statements
- `GET /v1/statements/{filing_id}` - Statements for filing

### 13F Holdings
- `GET /v1/holdings/13f?cik=&from=&to=` - List 13F holdings
- `GET /v1/holdings/13f/{filing_id}` - Holdings for filing

### Signals
- `GET /v1/signals?cik=&kind=` - Derived signals
- `GET /v1/signals/{filing_id}` - Signals for filing

### Usage
- `GET /v1/usage` - Current usage stats

See full API docs at http://localhost:8000/docs after starting the services.

## 📊 Database Schema

**Core Tables:**
- `companies` - SEC registered companies (CIK, name, tickers)
- `filings` - SEC filings (10-K, 10-Q, 8-K, 13F, etc.)
- `statements` - Normalized financial line items
- `holdings_13f` - Institutional holdings
- `signals` - Derived insights

**Auth & Billing:**
- `users` - User accounts
- `api_keys` - API access keys
- `plans` - Subscription tiers
- `subscriptions` - User subscriptions
- `usage_events` - API usage tracking

**Trading:**
- `trading_accounts` - IBKR accounts
- `positions` - Current positions
- `orders` - Trade orders

## 🛠️ Development

### Available Commands

```bash
make help              # Show all available commands
make up                # Start all services
make down              # Stop all services
make migrate           # Run database migrations
make migrate-create    # Create new migration
make seed              # Load sample data
make test              # Run all tests
make lint              # Run linters
make format            # Format code
make clean             # Clean up generated files
```

### Running Individual Services

```bash
# API only
make dev-api

# Web only
make dev-web

# Workers only
make dev-workers
```

### Creating Database Migrations

```bash
# Create a new migration
make migrate-create MSG="add user preferences"

# Apply migrations
make migrate

# Rollback one migration
cd apps/api && alembic downgrade -1
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test suites
make test-unit
make test-integration
make test-e2e

# Run with coverage
pytest --cov=apps --cov=packages --cov-report=html
```

## 📦 Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind, shadcn/ui |
| Backend API | FastAPI, Python 3.11, Pydantic v2 |
| Database | Postgres 15, Redis 7, S3 (MinIO) |
| Workers | RQ (Redis Queue) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Auth | JWT + API Keys |
| Payments | Stripe |
| Trading | IBKR (ib-insync) |
| Infra | Docker, Terraform |
| CI/CD | GitHub Actions |
| Monitoring | OpenTelemetry, Prometheus, Grafana |

## 🔐 Security

- Passwords hashed with bcrypt
- API keys securely hashed
- JWT tokens with RS256 (production)
- HTTPS only in production
- Rate limiting per plan tier
- RBAC for resource access
- Audit logging for key actions

## 🌍 Deployment

### Staging
```bash
make deploy-staging
```

### Production
```bash
make deploy-prod
```

See [docs/deployment.md](./docs/deployment.md) for detailed deployment instructions.

## 📈 Roadmap

### Milestone 1: Foundation ✅
- [x] Repo structure & Docker setup
- [x] Database schema & migrations
- [x] FastAPI backend with core endpoints
- [x] OpenAPI documentation

### Milestone 2: SEC EDGAR Ingestion (In Progress)
- [ ] SEC EDGAR client with rate limiting
- [ ] Ingestion workers (companies, filings)
- [ ] XBRL parser for 10-K/10-Q
- [ ] 13F holdings parser
- [ ] Backfill last 10 years

### Milestone 3: Public API
- [ ] Authentication (JWT + API keys)
- [ ] Rate limiting & usage metering
- [ ] Stripe integration
- [ ] API documentation site
- [ ] Example notebooks

### Milestone 4: Web Frontend
- [ ] Landing page
- [ ] Pricing & subscription flows
- [ ] Dataset catalog
- [ ] API explorer
- [ ] User dashboard

### Milestone 5: AI Hedge Fund Dashboard
- [ ] Integrate virattt/ai-hedge-fund
- [ ] Strategy modules
- [ ] Backtesting engine
- [ ] Portfolio analytics
- [ ] Factor library

### Milestone 6: Trading Execution
- [ ] IBKR connector
- [ ] Paper trading
- [ ] Risk management
- [ ] Order management system
- [ ] Live trading (with safeguards)

### Milestone 7: Production Hardening
- [ ] CI/CD pipeline
- [ ] Monitoring & alerting
- [ ] Load testing
- [ ] Security audit
- [ ] Documentation complete

## 🤝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines.

## 📄 License

MIT License - see [LICENSE](./LICENSE)

## 🔗 References

- [SEC EDGAR APIs](https://www.sec.gov/edgar/sec-api-documentation)
- [FinancialDatasets.ai](https://www.financialdatasets.ai)
- [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund)
- [virattt/dexter](https://github.com/virattt/dexter)
- [IBKR TWS API](https://interactivebrokers.github.io/tws-api/)

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

**Built with ❤️ for the AI & finance community**

# RecoverAI — Autonomous Payment Recovery Agent

**AI-powered payment recovery system** that predicts recovery probability, recommends recovery actions, applies safety controls, and measures recovered revenue across batches.

Built for the **Razorpay AI Buildathon — Track 03: AI Revenue Recovery**.

## Problem

Merchants lose revenue when payment attempts fail. Without intelligent intervention, these failures simply stop — and revenue slips away.

## Solution

RecoverAI implements the full recovery loop:

```
Failed Payment → Diagnose → Predict → AI Decision → Safety Gate → Execute → Measure
```

- **ML Prediction**: Binary classifier predicts recovery probability using transaction features
- **AI Recovery Agent**: LLM-powered agent recommends optimal recovery action (RETRY, SEND_PAYMENT_LINK, SEND_REMINDER, ESCALATE, NO_ACTION)
- **Policy Engine**: Deterministic safety controls — amount limits, retry limits, human approval requirements, idempotency
- **Audit Trail**: Every decision, prediction, and action is logged with correlation IDs
- **Analytics**: Measures recovered revenue, recovery rate, and model performance

## Architecture

```
DATA → ML PREDICTION → AI REASONING → POLICY/SAFETY → AUTO ACTION / HUMAN REVIEW → OUTCOME → ANALYTICS
```

- **Backend**: Python + Flask + SQLAlchemy
- **Database**: SQLite by default (PostgreSQL supported)
- **ML**: scikit-learn (Logistic Regression, Random Forest, Gradient Boosting)
- **AI**: Configurable LLM with deterministic fallback
- **Payments**: Razorpay integration (real TEST_API when keys configured, transparently labeled SIMULATED otherwise)
- **Frontend**: Responsive premium fintech UI (Bootstrap 5 + Chart.js + vanilla JS)

## Features

- Premium responsive app shell: sidebar drawer, topbar, notification badge, user footer (320→1920px)
- Marketing landing page + split-screen auth
- Merchant dashboard with live KPIs and Chart.js visualizations
- **Upload & Auto-Recover**: download a sample CSV, upload your own failed-transaction data, and RecoverAI ingests it, runs prediction → recommendation → policy, auto-executes eligible recoveries, and reports the reason for every case (`GET /api/transactions/sample-csv`, `POST /api/transactions/auto-recover`)
- **Upload batches (data isolation)**: every CSV upload is tagged with its own batch name (custom or auto-named from the file), existing data is never overwritten (duplicate `transaction_id`s are skipped), and you can view each batch **side by side** (transactions, value, recovered, at-risk) or **filter to only that batch** in Transactions (`GET /api/transactions/import-batches`, `?source=<batch>`)
- Transaction listing with search, filter, sort, pagination and ML recovery scores
- Transaction detail with prediction, recommendation, customer profile and action timeline
- AI-powered recovery recommendations with approval/execute workflow
- Deterministic policy engine with stopping rules (amount/retry limits, human approval)
- Recovery queue with status tabs and per-action controls
- Analytics: failure reasons, revenue recovery, model metrics, batch report, action outcomes
- Immutable audit trail with expandable event details (admin only, RBAC enforced)
- Notifications inbox with unread badge + mark-read
- Hash-chained ledger verification (`/api/ledger/verify`) and predunning scan
- Transparency labels: SIMULATED / TEST_API execution mode, AI/Rule decision source
- Synthetic dataset generator and batch experiment runner

## Quick Start

### 1. Setup

```bash
cd recoverai
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Database

The app runs on **SQLite out of the box** (absolute path configured via `.env`). PostgreSQL is supported for production.

```bash
# Seed the database with demo users, customers, and transactions
python scripts/seed.py

# OR: seeding is fully automatic on deploy — run.py seeds an EMPTY database
# on first boot (idempotent; never touches existing data). Demo login:
# admin@recoverai.com / admin123   (reviewer@recoverai.com / reviewer123)

# Generate a larger synthetic dataset + train the ML model
python scripts/generate_dataset.py
python -c "from app.ml.train import train_model; train_model()"
```

### 3. Generate Dataset & Train Model

```bash
# Generate synthetic dataset
python scripts/generate_dataset.py

# Train ML model
python -c "from app.ml.train import train_model; train_model()"
```

### 4. Run

```bash
python run.py
```

Visit `http://localhost:5000`### 5. Demo Credentials

- **Admin**: admin@recoverai.com / admin123
- **Reviewer**: reviewer@recoverai.com / reviewer123

## Run Batch Experiment

```bash
python scripts/run_batch_experiment.py 500
```

## Run Tests

```bash
pytest
```

## API Endpoints

### Authentication
- `POST /api/auth/register` — Register
- `POST /api/auth/login` — Login
- `POST /api/auth/logout` — Logout
- `GET /api/auth/me` — Current user

### Transactions
- `GET /api/transactions` — List (paginated, filterable)
- `GET /api/transactions/<id>` — Detail
- `POST /api/transactions/import` — CSV import
- `POST /api/transactions/<id>/analyze` — Run prediction + AI analysis

### Predictions
- `GET /api/predictions/<id>` — Get prediction
- `POST /api/predictions/<id>` — Generate prediction

### Recovery
- `GET /api/recovery` — List recovery queue
- `GET /api/recovery/<id>` — Recovery detail
- `POST /api/recovery/<id>/recommend` — Get AI recommendation
- `POST /api/recovery/<id>/approve` — Approve action
- `POST /api/recovery/<id>/reject` — Reject action
- `POST /api/recovery/<id>/execute` — Execute action

### Analytics
- `GET /api/analytics/overview` — Overview metrics
- `GET /api/analytics/recovery` — Recovery analytics
- `GET /api/analytics/model` — Model metrics
- `GET /api/analytics/batch-report` — Batch report

### Audit
- `GET /api/audit-logs` — Audit logs (admin only)

### Notifications
- `GET /api/notifications` — List notifications
- `PATCH /api/notifications/<id>/read` — Mark read
- `PATCH /api/notifications/read-all` — Mark all read

### Ledger & Predunning
- `GET /api/ledger/verify` — Verify hash-chain integrity
- `GET /api/ledger/entries` — List ledger entries
- `GET /api/ledger/predunning` — Run predunning scan

### Frontend Pages
- `/` landing, `/login`, `/register`
- `/dashboard`, `/transactions`, `/transactions/<id>`
- `/recovery`, `/analytics`, `/audit-logs`, `/notifications`

### Health
- `GET /health` — Health check

## Environment Variables

See `.env.example` for all configuration options. Key variables:

- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — Flask secret key
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` — Razorpay test credentials
- `LLM_API_KEY` — LLM API key (optional, falls back to rule-based)
- `MAX_AUTOMATIC_ACTION_AMOUNT` — Amount limit for auto-actions (default: 10000)
- `MAX_AUTOMATIC_RETRY_COUNT` — Retry limit (default: 1)

## Project Structure

```
recoverai/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── extensions.py        # Flask extensions
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # API & frontend routes
│   ├── services/            # Business logic
│   ├── ai/                  # AI agent & prompts
│   ├── ml/                  # ML pipeline
│   └── integrations/        # Razorpay integration
├── templates/               # Jinja2 templates
├── static/                  # CSS & JS
├── scripts/                 # Seed, dataset generation, experiments
├── tests/                   # Test suite
├── data/                    # Generated data & models
├── run.py                   # Entry point
├── requirements.txt
└── .env.example
```

## Evaluation

The project produces real measurements from reproducible experiments:

### Model Metrics
- Precision, Recall, F1, ROC-AUC
- Confusion matrix
- Model comparison (Logistic Regression vs Random Forest vs Gradient Boosting)

### Business Metrics
- Recovered Revenue
- Recovery Rate
- Revenue Recovery Rate
- Action Success Rate

### Safety Metrics
- Policy-blocked cases
- Escalated cases
- Idempotency violations (should be 0)

## License

MIT

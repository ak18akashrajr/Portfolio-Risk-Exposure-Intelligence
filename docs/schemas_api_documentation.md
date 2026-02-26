

# 🗄️ DATABASE SCHEMA

**Portfolio Exposure & Risk Intelligence Platform (India-Focused)**

Relational model (MySQL / PostgreSQL friendly)

---

## 1️⃣ Core Entities Overview

| Domain             | Tables                                |
| ------------------ | ------------------------------------- |
| User & Portfolio   | `users`, `portfolios`                 |
| Asset Master       | `assets`                              |
| Transactions       | `transactions`                        |
| Holdings Snapshot  | `holdings`                            |
| Exposure Analytics | `exposures`                           |
| Risk Metrics       | `risk_metrics`                        |
| Risk Limits        | `risk_limits`, `risk_breaches`        |
| Stress Testing     | `stress_scenarios`, `stress_results`  |
| Benchmarks         | `benchmarks`, `benchmark_performance` |
| Alerts & Insights  | `alerts`                              |
| LLM Intelligence   | `llm_queries`, `llm_responses`        |

---

## 2️⃣ User & Portfolio

### `users`

```sql
users (
  id UUID PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(150) UNIQUE,
  created_at TIMESTAMP
)
```

---

### `portfolios`

```sql
portfolios (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  name VARCHAR(100),
  base_currency VARCHAR(10) DEFAULT 'INR',
  created_at TIMESTAMP
)
```

---

## 3️⃣ Asset Master (India-Aware)

### `assets`

```sql
assets (
  id UUID PRIMARY KEY,
  symbol VARCHAR(30),                 -- e.g. RELIANCE, NIFTYBEES
  exchange VARCHAR(10),               -- NSE / BSE / NASDAQ
  asset_type VARCHAR(30),             -- Equity / ETF / MF / Gold
  sector VARCHAR(50),                 -- NSE sector classification
  market_cap_bucket VARCHAR(20),      -- Large / Mid / Small
  currency VARCHAR(10),               -- INR / USD
  geography VARCHAR(30),              -- India / Global
  created_at TIMESTAMP
)
```

> Acts as **single source of truth** for enrichment during ingestion.

---

## 4️⃣ Portfolio Transactions

### `transactions`

```sql
transactions (
  id UUID PRIMARY KEY,
  portfolio_id UUID REFERENCES portfolios(id),
  asset_id UUID REFERENCES assets(id),
  transaction_date DATE,
  quantity DECIMAL(18,6),
  price DECIMAL(18,4),
  transaction_type VARCHAR(10),       -- BUY / SELL
  created_at TIMESTAMP
)
```

---

## 5️⃣ Holdings Snapshot (Derived)

### `holdings`

```sql
holdings (
  id UUID PRIMARY KEY,
  portfolio_id UUID,
  asset_id UUID,
  quantity DECIMAL(18,6),
  avg_cost DECIMAL(18,4),
  market_value DECIMAL(18,4),
  snapshot_date DATE
)
```

> Updated daily or post-upload
> Used as the **base layer for analytics**

---

## 6️⃣ Exposure Analytics

### `exposures`

```sql
exposures (
  id UUID PRIMARY KEY,
  portfolio_id UUID,
  exposure_type VARCHAR(30),     -- Sector / AssetClass / Currency / Geography
  exposure_key VARCHAR(50),      -- IT / Banking / INR / India
  exposure_value DECIMAL(6,2),   -- Percentage
  snapshot_date DATE
)
```

Used for:

* Sector exposure
* Currency exposure
* Market-cap exposure
* Single-stock concentration

---

## 7️⃣ Risk Metrics

### `risk_metrics`

```sql
risk_metrics (
  id UUID PRIMARY KEY,
  portfolio_id UUID,
  volatility DECIMAL(8,4),
  beta DECIMAL(6,3),
  max_drawdown DECIMAL(6,2),
  var_95 DECIMAL(8,4),
  snapshot_date DATE
)
```

> All deterministic, reproducible metrics
> Benchmarked against NIFTY where applicable

---

## 8️⃣ Risk Limits & Governance

### `risk_limits`

```sql
risk_limits (
  id UUID PRIMARY KEY,
  portfolio_id UUID,
  limit_type VARCHAR(30),        -- Sector / SingleStock / Drawdown / Volatility
  limit_key VARCHAR(50),         -- IT / RELIANCE / PORTFOLIO
  threshold DECIMAL(6,2),
  created_at TIMESTAMP
)
```

---

### `risk_breaches`

```sql
risk_breaches (
  id UUID PRIMARY KEY,
  portfolio_id UUID,
  limit_id UUID REFERENCES risk_limits(id),
  actual_value DECIMAL(6,2),
  breach_date DATE,
  severity VARCHAR(20)           -- INFO / WARNING / CRITICAL
)
```

---

## 9️⃣ Stress Testing (India-Relevant)

### `stress_scenarios`

```sql
stress_scenarios (
  id UUID PRIMARY KEY,
  name VARCHAR(100),
  scenario_type VARCHAR(50),     -- Market / Sector / Currency
  shock_value DECIMAL(6,2),      -- -20%, -10%, etc
  description TEXT
)
```

---

### `stress_results`

```sql
stress_results (
  id UUID PRIMARY KEY,
  portfolio_id UUID,
  scenario_id UUID REFERENCES stress_scenarios(id),
  estimated_loss DECIMAL(18,4),
  impact_percentage DECIMAL(6,2),
  snapshot_date DATE
)
```

---

## 🔟 Benchmarks

### `benchmarks`

```sql
benchmarks (
  id UUID PRIMARY KEY,
  name VARCHAR(50),              -- NIFTY50 / NIFTY500
  symbol VARCHAR(30)
)
```

---

### `benchmark_performance`

```sql
benchmark_performance (
  id UUID PRIMARY KEY,
  benchmark_id UUID,
  return_percentage DECIMAL(6,2),
  volatility DECIMAL(6,2),
  period VARCHAR(20)             -- 1M / 3M / 1Y
)
```

---

## 1️⃣1️⃣ Alerts & Insights

### `alerts`

```sql
alerts (
  id UUID PRIMARY KEY,
  portfolio_id UUID,
  alert_type VARCHAR(50),        -- RiskBreach / Concentration / Stress
  message TEXT,
  severity VARCHAR(20),
  created_at TIMESTAMP,
  acknowledged BOOLEAN DEFAULT FALSE
)
```

---

## 1️⃣2️⃣ LLM Intelligence (Strict RAG)

### `llm_queries`

```sql
llm_queries (
  id UUID PRIMARY KEY,
  portfolio_id UUID,
  query TEXT,
  created_at TIMESTAMP
)
```

---

### `llm_responses`

```sql
llm_responses (
  id UUID PRIMARY KEY,
  query_id UUID REFERENCES llm_queries(id),
  response TEXT,
  data_sources TEXT,             -- metrics used
  created_at TIMESTAMP
)
```

---

# 🌐 API DESIGN (FastAPI – Reference)

---

## Portfolio & Upload

```
POST   /portfolios
POST   /portfolios/{id}/upload-csv
GET    /portfolios/{id}/holdings
```

---

## Exposure & Risk

```
GET /portfolios/{id}/exposures
GET /portfolios/{id}/risk-metrics
GET /portfolios/{id}/risk-breaches
```

---

## Risk Limits

```
POST /portfolios/{id}/risk-limits
GET  /portfolios/{id}/risk-limits
```

---

## Stress Testing

```
GET  /stress-scenarios
POST /portfolios/{id}/run-stress
GET  /portfolios/{id}/stress-results
```

---

## Benchmarking

```
GET /benchmarks
GET /portfolios/{id}/benchmark-comparison
```

---

## Alerts

```
GET /portfolios/{id}/alerts
POST /alerts/{id}/acknowledge
```

---

## LLM Portfolio Intelligence

```
POST /portfolios/{id}/ask
GET  /portfolios/{id}/llm-history
```

> Internally:

* Pull metrics
* Inject structured context
* Generate constrained response

---

# 🧠 Why This Works (Strategically)

* Schema is **normalized but analytics-friendly**
* Easy to extend (derivatives, options, debt)
* RAG-safe (LLM cannot hallucinate)
* Sprint-ready (each module = sprint deliverable)
* Resume-safe (looks institutional, not hobby)

---

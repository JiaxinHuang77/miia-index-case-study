# MIIA Index — Market Infrastructure & Index Analytics

**A quantitative index case study** | Equal-weighted, quarterly-rebalanced, USD Total Return  
Base 100 · 4 January 2021 → 2 October 2026 · Benchmark: SPDR S&P 500 ETF (SPY)

*Prepared by Jiaxin Huang · October 2026*

---

## Overview

The **MIIA Index** tracks eight US-listed companies that form the backbone of global capital markets — exchanges, clearinghouses, index providers, and financial data firms. This repository provides a reproducible educational index build workflow: from raw price data acquisition through index computation, performance analytics, and a client-style PDF factsheet.

The project demonstrates core competencies relevant to index product development:
- Index methodology design (universe, weighting, rebalancing)
- Automated data quality controls
- Daily index level and weight simulation
- Performance and risk comparison against a broad-market benchmark
- Automated two-page PDF factsheet generation

---

## Repository Structure

```
miia-index-case-study/
├── README.md                  ← You are here
├── methodology.md             ← Full index methodology document
├── requirements.txt           ← Python dependencies
├── src/
│   └── build_project.py       ← End-to-end build script (main entry point)
├── results/
│   ├── constituents.csv       ← Index constituents & target weights
│   ├── performance_metrics.csv← Key performance statistics vs. SPY
│   └── rebalance_turnover.csv ← Quarterly rebalance turnover history
└── docs/
    └── MIIA_Index_Project.pdf ← Client-style PDF factsheet
```

> **Note:** Raw price data (`data/adjusted_close.csv`) is excluded from version control via `.gitignore`. Run `build_project.py` once to download and cache it locally via Yahoo Finance.

---

## Index Constituents

Eight US-listed market infrastructure companies, each at a **12.5% target weight**:

| Ticker | Company                    | Primary Business          |
|--------|----------------------------|---------------------------|
| CME    | CME Group                  | Derivatives exchange      |
| ICE    | Intercontinental Exchange  | Multi-asset exchange      |
| NDAQ   | Nasdaq Inc.                | Exchange & technology     |
| CBOE   | Cboe Global Markets        | Options exchange          |
| SPGI   | S&P Global Inc.            | Ratings & index data      |
| MSCI   | MSCI Inc.                  | Index & analytics         |
| FDS    | FactSet Research Systems   | Financial data            |
| MORN   | Morningstar Inc.           | Investment research        |

---

## Performance Summary (Jan 2021 – Oct 2026)

| Metric                    | MIIA Index | SPY (Benchmark) |
|---------------------------|:----------:|:---------------:|
| Total Return              |  +58.64%   |   +125.31%      |
| Annualised Return         |   8.39%    |    15.24%       |
| Annualised Volatility     |  18.73%    |    16.61%       |
| Sharpe Ratio (rf = 0%)    |   0.448    |     0.917       |
| Max Drawdown              |  −27.93%   |    −24.50%      |
| Calmar Ratio              |   0.300    |     0.622       |
| Tracking Error vs SPY     |  15.92%    |       —         |
| Information Ratio         |  −0.430    |       —         |

> **Interpretation:** MIIA underperformed SPY over the backtest period while exhibiting higher volatility and drawdown. This is consistent with the concentrated exposure of a thematic basket compared with a diversified broad-market benchmark. The current prototype does not include formal performance attribution or valuation analysis, so no causal conclusion is drawn.

---

## Methodology Highlights

| Parameter          | Specification                                                     |
|--------------------|-------------------------------------------------------------------|
| Weighting          | Equal weight — each constituent 1/N = 12.5%                      |
| Rebalance freq.    | Quarterly — first business day of Jan, Apr, Jul, Oct             |
| Return type        | Total return (dividends reinvested via adjusted prices)           |
| Base date / value  | 4 January 2021 / 100                                              |
| Data source        | Yahoo Finance adjusted closing prices (`yfinance`)               |
| Benchmark          | SPDR S&P 500 ETF Trust (SPY)                                      |

**Daily index level formula:**

$$\text{Index}_t = \text{Index}_{t-1} \times \sum_{i} w_{i,t-1} \cdot \frac{P_{i,t}}{P_{i,t-1}}$$

At each quarterly rebalance date $t^*$, weights reset to $w_i = 1/N$. Between rebalances, weights drift with price performance.

For the full methodology including data quality controls and known limitations, see [`methodology.md`](methodology.md).

---

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/JiaxinHuang77/miia-index-case-study.git
cd miia-index-case-study
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the build pipeline

```bash
python src/build_project.py
```

**What this does:**
1. Downloads adjusted-close prices from Yahoo Finance (cached to `data/adjusted_close.csv`)
2. Runs data-quality checks (missing values, ±25% return outliers, stale prices)
3. Computes the daily MIIA index level and constituent weights
4. Rebases SPY to 100 on the base date as a benchmark
5. Calculates all performance metrics
6. Exports results CSVs to `results/`
7. Generates a two-page PDF factsheet to `docs/`

> First run requires an internet connection. Subsequent runs use the local cache.

---

## Pre-computed Results

| File | Description |
|------|-------------|
| [`results/constituents.csv`](results/constituents.csv) | Index constituents with target weights |
| [`results/performance_metrics.csv`](results/performance_metrics.csv) | Full performance statistics for MIIA and SPY |
| [`results/rebalance_turnover.csv`](results/rebalance_turnover.csv) | One-way turnover at each of the 23 quarterly rebalances |
| [`docs/MIIA_Index_Project.pdf`](docs/MIIA_Index_Project.pdf) | Client-ready PDF factsheet |

---

## Known Limitations

1. **Survivorship bias** — the static universe only includes companies that remained listed throughout.
2. **Look-ahead bias** — universe defined retrospectively with knowledge of survival.
3. **No transaction costs** — rebalance turnover is reported but no execution costs are deducted.
4. **No point-in-time data** — production systems require point-in-time classification databases (e.g., CRSP).
5. **Single data source** — Yahoo Finance adjusted prices may diverge from official vendor data.
6. **Zero risk-free rate** — Sharpe ratio computed without a risk-free rate deduction.

See [`methodology.md`](methodology.md) §8 for the full limitations discussion and §9 for next steps toward a production-grade index.

---

## Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| `pandas` | ≥ 2.0 | Data manipulation & time series |
| `numpy` | ≥ 1.24 | Numerical computation |
| `yfinance` | ≥ 0.2 | Yahoo Finance data download |
| `reportlab` | ≥ 4.0 | PDF factsheet generation |

---

## License

This project is prepared for **educational and illustrative purposes only**. It does not constitute investment advice or a registered financial benchmark.

---

*Jiaxin Huang · October 2026*

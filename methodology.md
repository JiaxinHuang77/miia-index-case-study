# Market Infrastructure & Index Analytics (MIIA) Index — Methodology

**Version 1.0 | October 2026 | Prepared by Jiaxin Huang**

---

## 1. Index Concept and Rationale

The Market Infrastructure & Index Analytics (MIIA) Index tracks eight US-listed companies that
form the backbone of global capital markets: exchanges, clearinghouses, index providers, and
financial data firms. These companies benefit from secular trends in financial data monetisation,
passive-investing growth, and derivatives volume, yet they are often underrepresented in standard
sector classifications.

The index is designed as a simple, transparent, equally weighted, total-return benchmark that can
serve as a starting point for a thematic index product, a building block for an ETF, or a
performance reference for an active strategy with exposure to market infrastructure.

---

## 2. Universe Definition

### 2.1 Eligible Instruments

- Primary-listing equity securities on a US national exchange (NYSE or NASDAQ).
- Companies that derive the majority of revenue from at least one of:
  - Exchange and clearing operations
  - Index calculation, licensing, and analytics
  - Financial market data and analytics
- Market capitalisation above USD 1 billion at the time of each review.
- Minimum average daily trading value of USD 1 million over the prior three months.

### 2.2 Fixed Illustrative Universe

For this educational prototype the universe is held **static** at the following eight names:

| Ticker | Company                     | Primary Business         |
|--------|-----------------------------|--------------------------|
| CME    | CME Group                   | Derivatives exchange     |
| ICE    | Intercontinental Exchange   | Multi-asset exchange     |
| NDAQ   | Nasdaq Inc.                 | Exchange & technology    |
| CBOE   | Cboe Global Markets         | Options exchange         |
| SPGI   | S&P Global Inc.             | Ratings & index data     |
| MSCI   | MSCI Inc.                   | Index & analytics        |
| FDS    | FactSet Research Systems    | Financial data           |
| MORN   | Morningstar Inc.            | Investment research      |

---

## 3. Weighting Scheme

**Equal weighting**: each constituent receives a target weight of 1/N = 12.5% at every quarterly
rebalance date. Equal weighting avoids concentration in the largest names and makes the methodology
simple to explain and audit.

---

## 4. Review Schedule

| Review type      | Frequency | Date convention                        |
|------------------|-----------|----------------------------------------|
| Composition      | Quarterly | First business day of Jan, Apr, Jul, Oct |
| Rebalance        | Quarterly | Same as composition review             |
| Extraordinary    | Ad hoc    | Corporate events (merger, delisting)   |

At each rebalance the portfolio weights are reset to 1/N. Between rebalances weights drift with
price performance.

---

## 5. Index Calculation

### 5.1 Base Date and Base Value

- Base date: **4 January 2021** (first business day of 2021)
- Base value: **100.00**

### 5.2 Total-Return Calculation

The index uses **split- and dividend-adjusted closing prices** sourced from Yahoo Finance via the
yfinance library. Because adjusted prices already capitalise dividend reinvestment, the
total-return series is constructed directly from adjusted price relatives.

**Daily index level:**

```
Index_t = Index_{t-1} * sum_i [ w_{i,t-1} * (AdjClose_{i,t} / AdjClose_{i,t-1}) ]
```

where:
- w_{i,t-1} = weight of constituent i at the end of the prior day
- AdjClose = adjusted closing price

At each rebalance date t*:

```
w_{i,t*} = 1/N   for all i
```

Between rebalances, weights drift:

```
w_{i,t} = w_{i,t-1} * (AdjClose_{i,t} / AdjClose_{i,t-1}) / sum_j [ w_{j,t-1} * (AdjClose_{j,t} / AdjClose_{j,t-1}) ]
```

### 5.3 Benchmark

The **SPDR S&P 500 ETF Trust (SPY)** is used as the broad-market benchmark proxy, rebased to 100
on the same base date.

---

## 6. Data and Quality Controls

| Check | Description |
|-------|-------------|
| Missing prices | Forward-fill up to 5 consecutive days; flag if exceeded |
| Stale prices | Alert if price unchanged for > 3 consecutive days |
| Return outliers | Flag daily returns beyond +/-25% for manual review |
| Gap check | Verify no gaps > 5 business days in the time series |

---

## 7. Performance Metrics

| Metric | Definition |
|--------|------------|
| Total return | (End level / 100) - 1 |
| Annualised return | (1 + total return)^(252/n_days) - 1 |
| Annualised volatility | Std(daily log-returns) * sqrt(252) |
| Sharpe ratio | Annualised return / Annualised volatility (risk-free rate = 0%) |
| Max drawdown | Max peak-to-trough decline in index level |
| Calmar ratio | Annualised return / abs(max drawdown) |
| Tracking error | Annualised std of daily return differences vs SPY |
| Information ratio | Active return / tracking error |

---

## 8. Known Limitations and Biases

1. **Survivorship bias**: the static universe only includes companies that survived and remained listed.
2. **Look-ahead bias**: the universe was defined with full knowledge of which companies remained listed.
3. **No point-in-time data**: production systems use point-in-time classification databases.
4. **No transaction costs**: rebalance turnover is reported but no costs are deducted.
5. **No corporate-action rules**: spin-offs, rights issues, and mergers require explicit treatment.
6. **Single data source**: Yahoo Finance adjusted prices may differ from official vendor data.
7. **Risk-free rate**: the Sharpe ratio uses a zero risk-free rate for simplicity.

---

## 9. Next Steps for a Production Index

- Adopt a point-in-time constituency database (e.g., CRSP, Compustat).
- Define formal free-float and liquidity screens.
- Implement corporate-action rules.
- Add an independent calculation agent.
- Establish formal index committee governance.
- Register with a recognised index standards body (IOSCO Principles).

---

*This document is prepared for educational and illustrative purposes only.*

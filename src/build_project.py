"""
build_project.py
================
Market Infrastructure & Index Analytics (MIIA) Index — end-to-end build script.

Steps performed
---------------
1. Download (or load from cache) adjusted-close price data via yfinance.
2. Run data-quality checks.
3. Compute the quarterly-rebalanced, equal-weighted MIIA total-return index.
4. Compute the SPY benchmark rebased to 100.
5. Calculate performance metrics.
6. Export CSV result files.
7. Generate a two-page PDF factsheet via ReportLab.

Usage
-----
    python3 build_project.py

Dependencies
------------
    pip install pandas numpy yfinance reportlab

Author:  Jiaxin Huang
Version: 1.0  |  October 2026
"""

# ── Standard library ──────────────────────────────────────────────────────────
import os
import sys
import warnings
from datetime import datetime, date
from pathlib import Path

# ── Third-party ───────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

# ─────────────────────────────────────────────────────────────────────────────
# 0.  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Index constituents
CONSTITUENTS = {
    "CME":  "CME Group",
    "ICE":  "Intercontinental Exchange",
    "NDAQ": "Nasdaq Inc.",
    "CBOE": "Cboe Global Markets",
    "SPGI": "S&P Global Inc.",
    "MSCI": "MSCI Inc.",
    "FDS":  "FactSet Research Systems",
    "MORN": "Morningstar Inc.",
}
BENCHMARK_TICKER = "SPY"
ALL_TICKERS      = list(CONSTITUENTS.keys()) + [BENCHMARK_TICKER]

BASE_DATE  = "2021-01-04"   # first business day of 2021
END_DATE   = date.today().isoformat()
BASE_VALUE = 100.0

# Paths — ROOT is the repo root (one level above src/)
ROOT        = Path(__file__).resolve().parents[1]
DATA_DIR    = ROOT / "data"
RESULTS_DIR = ROOT / "results"
PDF_DIR     = ROOT / "docs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILE  = DATA_DIR / "adjusted_close.csv"
PDF_OUT     = PDF_DIR  / "MIIA_Index_Project.pdf"


# ─────────────────────────────────────────────────────────────────────────────
# 1.  DATA DOWNLOAD & CACHE
# ─────────────────────────────────────────────────────────────────────────────

def download_prices() -> pd.DataFrame:
    """Download adjusted-close prices from Yahoo Finance and cache locally."""
    if CACHE_FILE.exists():
        print(f"[data]  Loading cached prices from {CACHE_FILE}")
        prices = pd.read_csv(CACHE_FILE, index_col=0, parse_dates=True)
        return prices

    print("[data]  Downloading prices from Yahoo Finance …")
    try:
        import yfinance as yf
    except ImportError:
        sys.exit(
            "yfinance is required: pip install yfinance\n"
            "Alternatively, provide data/adjusted_close.csv manually."
        )

    raw = yf.download(
        ALL_TICKERS,
        start=BASE_DATE,
        end=END_DATE,
        auto_adjust=True,   # returns adjusted prices in the 'Close' column
        progress=False,
    )

    # yfinance returns a multi-level column index when multiple tickers are
    # requested: level-0 = field, level-1 = ticker
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"][ALL_TICKERS]
    else:
        prices = raw[["Close"]].rename(columns={"Close": ALL_TICKERS[0]})

    prices.index.name = "Date"
    prices.to_csv(CACHE_FILE)
    print(f"[data]  Saved {len(prices)} rows to {CACHE_FILE}")
    return prices


# ─────────────────────────────────────────────────────────────────────────────
# 2.  DATA QUALITY CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def quality_checks(prices: pd.DataFrame) -> pd.DataFrame:
    """Run QA checks and return the cleaned price frame."""
    print("\n[qa]    Running data-quality checks …")
    constituent_prices = prices[list(CONSTITUENTS.keys())]

    # --- Missing values ---
    missing = prices.isnull().sum()
    if missing.any():
        print(f"[qa]    WARNING – missing values:\n{missing[missing > 0]}")
    else:
        print("[qa]    No missing values before forward-fill.")

    # Forward-fill up to 5 business days
    prices_filled = prices.ffill(limit=5)

    # Flag any remaining NaNs
    still_missing = prices_filled.isnull().sum()
    if still_missing.any():
        print(f"[qa]    ERROR – unfillable NaNs remain:\n{still_missing[still_missing > 0]}")
    else:
        print("[qa]    All gaps filled (limit = 5 days).")

    # --- Return outliers ±25% ---
    daily_ret = prices_filled.pct_change()
    outliers  = (daily_ret.abs() > 0.25).stack()
    outliers  = outliers[outliers]
    if not outliers.empty:
        print(f"[qa]    WARNING – {len(outliers)} daily return(s) exceed ±25%:")
        print(outliers.index.tolist())
    else:
        print("[qa]    No return outliers > ±25%.")

    # --- Stale prices (unchanged > 3 consecutive days) ---
    for ticker in list(CONSTITUENTS.keys()) + [BENCHMARK_TICKER]:
        col = prices_filled[ticker]
        stale = (col.diff() == 0).rolling(3).sum() >= 3
        n_stale = stale.sum()
        if n_stale:
            print(f"[qa]    WARNING – {ticker}: {n_stale} day(s) with price unchanged for ≥ 3 days.")

    print("[qa]    Quality checks complete.\n")
    return prices_filled


# ─────────────────────────────────────────────────────────────────────────────
# 3.  REBALANCE SCHEDULE
# ─────────────────────────────────────────────────────────────────────────────

def build_rebalance_schedule(index: pd.DatetimeIndex) -> list:
    """
    Return a list of DatetimeIndex dates that are quarterly rebalance dates:
    the first business day of January, April, July, and October.
    The base date is always included as the first rebalance.
    """
    rebalance_months = {1, 4, 7, 10}
    # All business days in the price series
    bdays = pd.Series(index, index=index)

    schedule = []
    years = range(index[0].year, index[-1].year + 1)
    for year in years:
        for month in rebalance_months:
            # First business day of this month/year
            month_days = bdays[(bdays.index.year == year) & (bdays.index.month == month)]
            if len(month_days):
                schedule.append(month_days.index[0])

    # Filter to dates within the price series
    schedule = [d for d in schedule if d >= index[0] and d <= index[-1]]
    return sorted(set(schedule))


# ─────────────────────────────────────────────────────────────────────────────
# 4.  INDEX CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def compute_index(prices: pd.DataFrame) -> tuple:
    """
    Compute the MIIA equal-weighted total-return index.

    Returns
    -------
    index_levels  : pd.Series  – daily index level (base = 100)
    weights_df    : pd.DataFrame – daily weight of each constituent
    rebalance_df  : pd.DataFrame – turnover at each rebalance date
    """
    tickers  = list(CONSTITUENTS.keys())
    n        = len(tickers)
    eq_wt    = 1.0 / n

    # Slice constituent prices, start from base date
    px = prices[tickers].copy()
    px = px[px.index >= BASE_DATE].dropna(how="all")

    rebalance_dates = build_rebalance_schedule(px.index)
    print(f"[calc]  {len(rebalance_dates)} rebalance dates identified "
          f"({rebalance_dates[0].date()} → {rebalance_dates[-1].date()})")

    # --- Initialise ---
    index_levels = pd.Series(index=px.index, dtype=float, name="MIIA")
    weights_df   = pd.DataFrame(index=px.index, columns=tickers, dtype=float)

    # Set base date
    t0   = px.index[0]
    index_levels.iloc[0] = BASE_VALUE
    weights_df.iloc[0]   = eq_wt

    # Turnover tracking
    turnover_records = []

    # --- Daily loop ---
    for i in range(1, len(px)):
        t_prev = px.index[i - 1]
        t_curr = px.index[i]

        prev_wts   = weights_df.loc[t_prev].values
        price_prev = px.loc[t_prev].values
        price_curr = px.loc[t_curr].values

        # Price relatives (handle zeros / NaN)
        with np.errstate(invalid="ignore", divide="ignore"):
            relatives = np.where(
                (price_prev > 0) & np.isfinite(price_prev),
                price_curr / price_prev,
                1.0,
            )

        # Portfolio return for the day
        port_ret = np.dot(prev_wts, relatives)

        # Drift weights
        drift_wts_raw = prev_wts * relatives
        drift_wts     = drift_wts_raw / drift_wts_raw.sum()

        # Check if today is a rebalance date
        if t_curr in rebalance_dates:
            new_wts = np.full(n, eq_wt)
            turnover = np.abs(new_wts - drift_wts).sum() / 2.0
            turnover_records.append({
                "rebalance_date": t_curr.date(),
                "one_way_turnover": round(turnover, 6),
            })
            weights_df.loc[t_curr] = new_wts
        else:
            weights_df.loc[t_curr] = drift_wts

        index_levels.iloc[i] = index_levels.iloc[i - 1] * port_ret

    rebalance_df = pd.DataFrame(turnover_records)
    return index_levels, weights_df, rebalance_df


# ─────────────────────────────────────────────────────────────────────────────
# 5.  BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

def compute_benchmark(prices: pd.DataFrame) -> pd.Series:
    """Rebase SPY to 100 on the base date."""
    spy  = prices[BENCHMARK_TICKER].copy()
    spy  = spy[spy.index >= BASE_DATE].dropna()
    spy  = spy / spy.iloc[0] * BASE_VALUE
    spy.name = "SPY"
    return spy


# ─────────────────────────────────────────────────────────────────────────────
# 6.  PERFORMANCE METRICS
# ─────────────────────────────────────────────────────────────────────────────

def performance_metrics(
    index_levels: pd.Series,
    benchmark   : pd.Series,
) -> pd.DataFrame:
    """Compute and return a summary performance-metrics table."""

    def _metrics(series: pd.Series, label: str) -> dict:
        log_ret     = np.log(series / series.shift(1)).dropna()
        n_days      = len(log_ret)
        total_ret   = series.iloc[-1] / series.iloc[0] - 1.0
        ann_ret     = (1 + total_ret) ** (252.0 / n_days) - 1.0
        ann_vol     = log_ret.std() * np.sqrt(252)
        sharpe      = ann_ret / ann_vol if ann_vol != 0 else np.nan
        roll_max    = series.cummax()
        drawdown    = (series - roll_max) / roll_max
        max_dd      = drawdown.min()
        calmar      = ann_ret / abs(max_dd) if max_dd != 0 else np.nan
        return {
            "series"            : label,
            "start_date"        : series.index[0].date(),
            "end_date"          : series.index[-1].date(),
            "n_days"            : n_days,
            "total_return_pct"  : round(total_ret  * 100, 2),
            "ann_return_pct"    : round(ann_ret     * 100, 2),
            "ann_volatility_pct": round(ann_vol     * 100, 2),
            "sharpe_ratio"      : round(sharpe,           3),
            "max_drawdown_pct"  : round(max_dd      * 100, 2),
            "calmar_ratio"      : round(calmar,           3),
        }

    # Align series on common dates
    combined = pd.concat([index_levels, benchmark], axis=1).dropna()
    miia_s   = combined["MIIA"]
    spy_s    = combined["SPY"]

    miia_m   = _metrics(miia_s, "MIIA")
    spy_m    = _metrics(spy_s,  "SPY")

    # Tracking error and information ratio
    active_ret     = (miia_s.pct_change() - spy_s.pct_change()).dropna()
    tracking_error = active_ret.std() * np.sqrt(252) * 100        # in %
    active_ann     = miia_m["ann_return_pct"] - spy_m["ann_return_pct"]
    info_ratio     = active_ann / tracking_error if tracking_error != 0 else np.nan

    miia_m["tracking_error_pct"] = round(tracking_error, 2)
    miia_m["information_ratio"]  = round(info_ratio, 3)
    spy_m["tracking_error_pct"]  = np.nan
    spy_m["information_ratio"]   = np.nan

    return pd.DataFrame([miia_m, spy_m])


# ─────────────────────────────────────────────────────────────────────────────
# 7.  EXPORT RESULTS
# ─────────────────────────────────────────────────────────────────────────────

def export_results(
    index_levels : pd.Series,
    benchmark    : pd.Series,
    rebalance_df : pd.DataFrame,
    metrics_df   : pd.DataFrame,
) -> None:
    """Write CSV outputs to the results/ directory."""

    # 7a. Index levels
    levels = pd.concat([index_levels, benchmark], axis=1).dropna()
    levels.index.name = "Date"
    levels.to_csv(RESULTS_DIR / "index_levels.csv")
    print(f"[out]   Saved index levels → {RESULTS_DIR / 'index_levels.csv'}")

    # 7b. Rebalance turnover
    rebalance_df.to_csv(RESULTS_DIR / "rebalance_turnover.csv", index=False)
    print(f"[out]   Saved rebalance turnover → {RESULTS_DIR / 'rebalance_turnover.csv'}")

    # 7c. Performance metrics
    metrics_df.to_csv(RESULTS_DIR / "performance_metrics.csv", index=False)
    print(f"[out]   Saved performance metrics → {RESULTS_DIR / 'performance_metrics.csv'}")

    # 7d. Constituents table
    constituents = pd.DataFrame(
        [
            {"ticker": t, "company": c, "target_weight_pct": round(100.0 / len(CONSTITUENTS), 4)}
            for t, c in CONSTITUENTS.items()
        ]
    )
    constituents.to_csv(RESULTS_DIR / "constituents.csv", index=False)
    print(f"[out]   Saved constituents → {RESULTS_DIR / 'constituents.csv'}")


# ─────────────────────────────────────────────────────────────────────────────
# 8.  PDF FACTSHEET
# ─────────────────────────────────────────────────────────────────────────────

def build_pdf(metrics_df: pd.DataFrame, rebalance_df: pd.DataFrame) -> None:
    """Generate a two-page client-style PDF factsheet using ReportLab."""
    try:
        from reportlab.lib             import colors
        from reportlab.lib.pagesizes   import A4
        from reportlab.lib.styles      import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units       import cm
        from reportlab.platypus        import (
            BaseDocTemplate, Frame, PageTemplate,
            Paragraph, Spacer, Table, TableStyle, HRFlowable,
        )
    except ImportError:
        print("[pdf]   ReportLab not found – skipping PDF generation.")
        print("        Install with: pip install reportlab")
        return

    # ── Colour palette ───────────────────────────────────────────────────────
    NAVY   = colors.HexColor("#0D1F3C")
    BLUE   = colors.HexColor("#1B4FBF")
    SILVER = colors.HexColor("#D6DCE4")
    WHITE  = colors.white
    LGRAY  = colors.HexColor("#F5F7FA")

    # ── Styles ───────────────────────────────────────────────────────────────
    ss = getSampleStyleSheet()

    def sty(name, **kwargs):
        base = ss["Normal"]
        return ParagraphStyle(name, parent=base, **kwargs)

    h1      = sty("H1", fontSize=20, textColor=WHITE, fontName="Helvetica-Bold",
                  spaceAfter=4, leading=24)
    h2      = sty("H2", fontSize=11, textColor=NAVY, fontName="Helvetica-Bold",
                  spaceAfter=4, spaceBefore=12, leading=14)
    body    = sty("Body", fontSize=8.5, textColor=NAVY, leading=13)
    caption = sty("Cap",  fontSize=7.5, textColor=colors.grey, leading=11)
    small   = sty("Sm",   fontSize=8, textColor=NAVY, leading=12)

    # ── Document ─────────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        str(PDF_OUT),
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
    )
    frame  = Frame(doc.leftMargin, doc.bottomMargin,
                   doc.width, doc.height, id="normal")
    page_t = PageTemplate(id="base", frames=[frame])
    doc.addPageTemplates([page_t])

    # ── Helper: section header band ──────────────────────────────────────────
    def section(title):
        return [
            HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=2),
            Paragraph(title, h2),
        ]

    # ── Helper: coloured table ────────────────────────────────────────────────
    def styled_table(data, col_widths=None):
        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0),  NAVY),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0),  8),
            ("FONTSIZE",     (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1),(-1, -1), [LGRAY, WHITE]),
            ("GRID",         (0, 0), (-1, -1), 0.25, SILVER),
            ("ALIGN",        (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        return tbl

    # ── Content ──────────────────────────────────────────────────────────────
    story = []

    # --- Cover banner ---
    banner_data = [[Paragraph("Market Infrastructure &amp; Index Analytics Index", h1)]]
    banner = Table(banner_data, colWidths=[doc.width])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.3*cm))

    # Sub-header line
    story.append(Paragraph(
        "Ticker: MIIA  |  Equal-weighted, quarterly-rebalanced, USD Total Return  "
        "|  Base 100 on 4 Jan 2021",
        caption,
    ))
    story.append(Spacer(1, 0.4*cm))

    # --- Objective ---
    story += section("Index Objective")
    story.append(Paragraph(
        "The MIIA Index provides transparent, equal-weighted exposure to eight US-listed companies "
        "that form the infrastructure layer of global capital markets: exchanges, index providers, "
        "and financial data analytics firms.  The index is rebalanced quarterly to equal weights "
        "and is expressed as a USD total-return series.",
        body,
    ))
    story.append(Spacer(1, 0.3*cm))

    # --- Constituents table ---
    story += section("Index Constituents (as of base date)")
    c_data = [["Ticker", "Company", "Business", "Target Weight"]]
    biz = {
        "CME":  "Derivatives exchange",
        "ICE":  "Multi-asset exchange",
        "NDAQ": "Exchange & technology",
        "CBOE": "Options exchange",
        "SPGI": "Ratings & index data",
        "MSCI": "Index & analytics",
        "FDS":  "Financial data",
        "MORN": "Investment research",
    }
    for tkr, name in CONSTITUENTS.items():
        c_data.append([tkr, name, biz[tkr], "12.50%"])
    w = doc.width / 4
    story.append(styled_table(c_data, [w*0.5, w*1.5, w*1.2, w*0.8]))
    story.append(Spacer(1, 0.3*cm))

    # --- Performance summary ---
    story += section("Performance Summary")
    miia_row = metrics_df[metrics_df["series"] == "MIIA"].iloc[0]
    spy_row  = metrics_df[metrics_df["series"] == "SPY"].iloc[0]

    perf_data = [
        ["Metric", "MIIA", "SPY (Benchmark)"],
        ["Start date",              str(miia_row.start_date),    str(spy_row.start_date)],
        ["End date",                str(miia_row.end_date),      str(spy_row.end_date)],
        ["Total return",            f"{miia_row.total_return_pct:.1f}%",   f"{spy_row.total_return_pct:.1f}%"],
        ["Annualised return",       f"{miia_row.ann_return_pct:.1f}%",     f"{spy_row.ann_return_pct:.1f}%"],
        ["Annualised volatility",   f"{miia_row.ann_volatility_pct:.1f}%", f"{spy_row.ann_volatility_pct:.1f}%"],
        ["Sharpe ratio (rf = 0%)",  f"{miia_row.sharpe_ratio:.2f}",        f"{spy_row.sharpe_ratio:.2f}"],
        ["Max drawdown",            f"{miia_row.max_drawdown_pct:.1f}%",   f"{spy_row.max_drawdown_pct:.1f}%"],
        ["Calmar ratio",            f"{miia_row.calmar_ratio:.2f}",        f"{spy_row.calmar_ratio:.2f}"],
        ["Tracking error vs SPY",   f"{miia_row.tracking_error_pct:.1f}%", "—"],
        ["Information ratio",       f"{miia_row.information_ratio:.2f}",   "—"],
    ]
    col_w = [doc.width * 0.5, doc.width * 0.25, doc.width * 0.25]
    story.append(styled_table(perf_data, col_w))
    story.append(Spacer(1, 0.3*cm))

    # --- Methodology summary ---
    story += section("Methodology at a Glance")
    meth_data = [
        ["Parameter", "Specification"],
        ["Universe",          "8 US-listed market infrastructure & index companies"],
        ["Weighting",         "Equal weight (12.5% each)"],
        ["Review frequency",  "Quarterly — first business day of Jan, Apr, Jul, Oct"],
        ["Return type",       "Total return (dividends reinvested via adjusted prices)"],
        ["Base date",         "4 January 2021  |  Base value: 100"],
        ["Benchmark",         "SPDR S&P 500 ETF Trust (SPY)"],
        ["Data source",       "Yahoo Finance (adjusted closing prices)"],
    ]
    col_w2 = [doc.width * 0.38, doc.width * 0.62]
    story.append(styled_table(meth_data, col_w2))
    story.append(Spacer(1, 0.3*cm))

    # --- Rebalance turnover snapshot ---
    if len(rebalance_df):
        story += section("Indicative Rebalance Turnover (most recent 4)")
        t_data = [["Rebalance Date", "One-Way Turnover"]]
        for _, row in rebalance_df.tail(4).iterrows():
            t_data.append([str(row["rebalance_date"]),
                           f"{row['one_way_turnover']*100:.2f}%"])
        story.append(styled_table(t_data, [doc.width*0.5, doc.width*0.5]))
        story.append(Spacer(1, 0.3*cm))

    # --- Limitations ---
    story += section("Important Limitations")
    limitations = [
        "Survivorship &amp; look-ahead bias: universe defined retrospectively; acquired or delisted names excluded.",
        "No transaction costs, taxes, or market-impact estimates are reflected.",
        "No point-in-time data: classification based on current business descriptions.",
        "Single data source (Yahoo Finance): adjusted prices may diverge from official vendor data.",
        "Static universe: no formal review process, liquidity screen, or free-float adjustment.",
        "Sharpe ratio computed with zero risk-free rate.",
    ]
    for lim in limitations:
        story.append(Paragraph(f"• {lim}", small))
    story.append(Spacer(1, 0.3*cm))

    # --- Disclaimer ---
    story += section("Disclaimer")
    story.append(Paragraph(
        "This factsheet is prepared by Jiaxin Huang for educational and illustrative purposes only. "
        "It does not constitute investment advice, a financial benchmark registered under any "
        "regulatory framework, or an offer to buy or sell any security. Past performance is not "
        "indicative of future results.",
        caption,
    ))

    # --- Build PDF ---
    doc.build(story)
    print(f"[pdf]   Factsheet saved → {PDF_OUT}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  MIIA Index Build  —  Jiaxin Huang  |  October 2026")
    print("=" * 60)

    # 1. Data
    prices = download_prices()

    # 2. QA
    prices = quality_checks(prices)

    # 3. Index
    print("[calc]  Computing MIIA index …")
    index_levels, weights_df, rebalance_df = compute_index(prices)
    print(f"[calc]  Index computed: {len(index_levels)} daily observations")
    print(f"[calc]  Latest MIIA level: {index_levels.iloc[-1]:.4f}  "
          f"(date: {index_levels.index[-1].date()})")

    # 4. Benchmark
    benchmark = compute_benchmark(prices)

    # 5. Metrics
    print("[metrics] Computing performance metrics …")
    metrics_df = performance_metrics(index_levels, benchmark)
    print(metrics_df[["series", "total_return_pct", "ann_return_pct",
                       "ann_volatility_pct", "sharpe_ratio", "max_drawdown_pct"]].to_string(index=False))

    # 6. Export
    print("\n[out]   Exporting results …")
    export_results(index_levels, benchmark, rebalance_df, metrics_df)

    # 7. PDF
    print("\n[pdf]   Building factsheet …")
    build_pdf(metrics_df, rebalance_df)

    print("\n" + "=" * 60)
    print("  Build complete.")
    print(f"  Results:  {RESULTS_DIR}")
    print(f"  Factsheet: {PDF_OUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()

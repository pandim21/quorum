"""LangChain tool: hand the Research Analyst a company's research packet.

Pulls LIVE fundamentals + recent headlines from Yahoo Finance (yfinance), maps them
into the committee's packet schema, caches the result to data/<ticker>.json (a
stamped audit snapshot), and falls back to that cache if the live fetch fails. So
the demo runs on real data but can never crash on a flaky network or a rate limit.

Quick test (no committee needed):
    uv run python company_data.py NVDA
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.tools import tool

DATA_DIR = Path(__file__).parent / "data"
RISKS_DIR = DATA_DIR / "risks"


def _bn(x):
    """USD -> USD billions (1 dp). Non-numbers (e.g. None) pass through as None."""
    return round(x / 1e9, 1) if isinstance(x, (int, float)) else None


def _pct(x):
    """Decimal ratio -> percent (1 dp). None passes through."""
    return round(x * 100, 1) if isinstance(x, (int, float)) else None


def _num(x, n=1):
    return round(x, n) if isinstance(x, (int, float)) else None


def _headlines(tk) -> list[dict]:
    """Up to 4 recent headlines as {headline, so_what}, robust to yfinance changes."""
    out = []
    try:
        items = tk.news or []
    except Exception:
        items = []
    for item in items[:4]:
        content = item.get("content", item)  # newer yfinance nests under "content"
        headline = content.get("title") or item.get("title")
        if not headline:
            continue
        summary = content.get("summary") or content.get("description") or ""
        out.append({"headline": headline, "so_what": summary[:240]})
    return out


def _load_overlay(ticker: str):
    """Curated, documented structural-risk dossier merged over the live numbers, so
    the committee weighs real qualitative risks (Yahoo's headline feed is too noisy
    to surface them reliably). Returns a list of developments, or None."""
    path = RISKS_DIR / f"{ticker.lower()}.json"
    if not path.exists():
        return None
    try:
        devs = json.loads(path.read_text(encoding="utf-8")).get("recent_developments")
        return devs if isinstance(devs, list) and devs else None
    except Exception:
        return None


def _fetch_live(ticker: str) -> dict:
    """Build the packet from Yahoo Finance. Raises on hard failure (-> fallback)."""
    import yfinance as yf

    tk = yf.Ticker(ticker)
    info = tk.info or {}
    if not info.get("marketCap") and not info.get("shortName"):
        raise ValueError(f"yfinance returned no usable data for '{ticker}'")

    debt, cash = info.get("totalDebt"), info.get("totalCash")
    net_debt = (
        _bn(debt - cash)
        if isinstance(debt, (int, float)) and isinstance(cash, (int, float))
        else None
    )

    snapshot = {
        "sub_industry": info.get("industry") or info.get("sector"),
        "market_cap_usd_bn": _bn(info.get("marketCap")),
        "fwd_pe": _num(info.get("forwardPE")),
    }
    key_financials = {
        "revenue_ttm_usd_bn": _bn(info.get("totalRevenue")),
        "revenue_growth_yoy_pct": _pct(info.get("revenueGrowth")),
        "gross_margin_pct": _pct(info.get("grossMargins")),
        "operating_margin_pct": _pct(info.get("operatingMargins")),
        "net_income_ttm_usd_bn": _bn(info.get("netIncomeToCommon")),
        "fcf_ttm_usd_bn": _bn(info.get("freeCashflow")),
        "net_debt_usd_bn": net_debt,
        "ev_ebitda": _num(info.get("enterpriseToEbitda")),
    }
    gaps = [k for k, v in {**snapshot, **key_financials}.items() if v is None]

    live_headlines = _headlines(tk)
    overlay = _load_overlay(ticker)
    packet = {
        "ticker": ticker.upper(),
        "company": info.get("longName") or info.get("shortName") or ticker.upper(),
        "source": "Yahoo Finance (yfinance)" + (" + curated risk dossier" if overlay else ""),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "snapshot": snapshot,
        "key_financials": key_financials,
        "recent_developments": overlay or live_headlines,
        "data_gaps": gaps,
    }
    if overlay:
        packet["live_headlines"] = live_headlines  # raw feed kept for transparency
    return packet


@tool
def get_company_data(ticker: str) -> str:
    """Return a research data packet (live financials, valuation, recent headlines)
    for a stock ticker, e.g. AAPL, NVDA, MSFT. Pulls live from Yahoo Finance and
    caches the result; falls back to the last cached packet if the fetch fails."""
    ticker = ticker.strip().upper()
    path = DATA_DIR / f"{ticker.lower()}.json"

    try:
        packet = _fetch_live(ticker)
        DATA_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        return json.dumps(packet)
    except Exception as e:  # noqa: BLE001 -- any failure should degrade to cache
        if path.exists():
            cached = json.loads(path.read_text(encoding="utf-8"))
            cached["data_note"] = f"LIVE FETCH FAILED ({type(e).__name__}); using cached snapshot."
            return json.dumps(cached)
        available = ", ".join(sorted(p.stem.upper() for p in DATA_DIR.glob("*.json"))) or "none"
        return json.dumps(
            {"error": f"Live fetch failed for '{ticker}' ({e}); no cached packet. Available: {available}"}
        )


if __name__ == "__main__":
    import sys

    t = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    print(get_company_data.invoke({"ticker": t}))

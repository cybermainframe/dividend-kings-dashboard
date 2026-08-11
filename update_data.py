from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

TICKERS_FILE = ROOT / "tickers.txt"
HISTORY_FILE = DATA_DIR / "dividend_kings_history.csv"
LATEST_FILE = DATA_DIR / "dividend_kings_latest.csv"


DEFAULT_TICKERS = [
    "PH", "BDX", "FUL", "ABT", "EMR", "NWN", "TGT", "ABBV", "AWR", "GPC",
    "JNJ", "SYY", "SCL", "SWK", "WMT", "LOW", "BKH", "RPM", "MSEX", "NFG",
    "ADM", "NDSN", "GWW", "KO", "TR", "MSA", "CL", "FMCB", "PEP", "CWT",
    "ITW", "DOV", "NUE", "ED", "FTS", "SPGI", "PPG", "CBSH", "UBSI", "ABM",
    "PG", "KVUE", "KMB", "GRC", "CINF", "HRL", "MO", "FRT", "CDUAF", "UVV", "TNC",
]


def load_tickers() -> list[str]:
    """Lê a lista de tickers do ficheiro tickers.txt."""
    if TICKERS_FILE.exists():
        lines = TICKERS_FILE.read_text(encoding="utf-8").splitlines()
        tickers = []

        for line in lines:
            line = line.strip().upper()

            if not line:
                continue

            if line.startswith("#"):
                continue

            tickers.append(line)

        return tickers

    return DEFAULT_TICKERS


def fetch_one(ticker: str) -> dict | None:
    """Obtém dados de uma ação usando o yfinance."""
    try:
        stock = yf.Ticker(ticker)

        hist = stock.history(period="1y", interval="1d")

        if hist.empty:
            print(f"Sem histórico para {ticker}")
            return None

        last_date = hist.index[-1].date()
        price = float(hist["Close"].iloc[-1])
        low_52 = float(hist["Low"].min())
        high_52 = float(hist["High"].max())

        info = stock.info or {}

        name = info.get("shortName") or info.get("longName") or ticker
        sector = info.get("sector")
        industry = info.get("industry")
        market_cap = info.get("marketCap")
        trailing_pe = info.get("trailingPE")

        dividend_yield = info.get("dividendYield")

        if dividend_yield is not None:
            dividend_yield = float(dividend_yield)

            if dividend_yield < 1:
                dividend_yield = dividend_yield * 100
        else:
            dividend_rate = info.get("dividendRate")
            current_price_info = info.get("currentPrice") or info.get("regularMarketPrice")

            if dividend_rate and current_price_info:
                try:
                    dividend_yield = (float(dividend_rate) / float(current_price_info)) * 100
                except Exception:
                    dividend_yield = None

        pct_from_low = None
        if low_52 and low_52 > 0:
            pct_from_low = ((price - low_52) / low_52) * 100

        pct_from_high = None
        if high_52 and high_52 > 0:
            pct_from_high = ((price - high_52) / high_52) * 100

        return {
            "date": last_date,
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "price": round(price, 2),
            "low_52w": round(low_52, 2),
            "high_52w": round(high_52, 2),
            "pct_from_low": round(pct_from_low, 2) if pct_from_low is not None else None,
            "pct_from_high": round(pct_from_high, 2) if pct_from_high is not None else None,
            "dividend_yield_pct": round(dividend_yield, 2) if dividend_yield is not None else None,
            "trailing_pe": round(trailing_pe, 2) if trailing_pe is not None else None,
            "market_cap": market_cap,
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }

    except Exception as e:
        print(f"Erro em {ticker}: {e}")
        return None


def save_data(rows: list[dict]) -> None:
    """Guarda os dados em dois ficheiros: histórico e última atualização."""
    df_new = pd.DataFrame(rows)

    if df_new.empty:
        print("Não foram obtidos dados novos.")
        return

    if HISTORY_FILE.exists():
        df_old = pd.read_csv(HISTORY_FILE)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new

    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(subset=["ticker", "date"], keep="last")
    df = df.sort_values(["date", "pct_from_low"])

    df.to_csv(HISTORY_FILE, index=False)

    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date].copy()
    latest = latest.sort_values("pct_from_low")

    latest.to_csv(LATEST_FILE, index=False)

    print(f"Histórico guardado em: {HISTORY_FILE}")
    print(f"Última atualização guardada em: {LATEST_FILE}")
    print(f"Total de linhas no histórico: {len(df)}")
    print(f"Última data: {latest_date.date()}")


def main() -> None:
    tickers = load_tickers()

    print(f"A atualizar {len(tickers)} tickers...")

    rows = []

    for ticker in tickers:
        print(f"A obter {ticker}...")
        row = fetch_one(ticker)

        if row:
            rows.append(row)

        time.sleep(0.25)

    save_data(rows)


if __name__ == "__main__":
    main()
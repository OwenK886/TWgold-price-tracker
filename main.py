#!/usr/bin/env python3
"""Fetch Bank of Taiwan gold passbook prices and append them to data.json."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PRIMARY_URL = "https://www.bot.com.tw/tw/personal-banking/precious-metals"
LEGACY_URL = "https://rate.bot.com.tw/gold?Lang=zh-TW"
SOURCE_URLS = (PRIMARY_URL, LEGACY_URL)
DATA_FILE = Path(__file__).with_name("data.json")
TAIPEI_TZ = timezone(timedelta(hours=8))

CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 30
BROWSER_TIMEOUT_MS = 60_000
CHALLENGE_WAIT_MS = 45_000

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
PRICE_PATTERN = r"([0-9][0-9,]*(?:\.[0-9]+)?)"
CHALLENGE_MARKERS = (
    "Challenge Validation",
    "cp_clge_done",
    "sec-container",
    "sec-cpt-if",
)


class ScraperError(RuntimeError):
    """Raised when a source cannot provide a trustworthy quote."""


class SecurityChallengeError(ScraperError):
    """Raised when an HTTP 200 response is actually a JavaScript challenge."""


class ParseError(ScraperError):
    """Raised when expected price fields are absent or invalid."""


@dataclass(frozen=True)
class GoldQuote:
    listed_at: datetime
    buy: float
    sell: float
    source_url: str


def build_session() -> requests.Session:
    """Return a session with bounded retries for transient network failures."""
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        other=0,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )
    return session


def is_security_challenge(html: str) -> bool:
    return any(marker in html for marker in CHALLENGE_MARKERS)


def fetch_html(session: requests.Session, url: str) -> str:
    """Fetch HTML and reject non-HTML or disguised challenge responses."""
    started = time.monotonic()
    response = session.get(
        url,
        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
    )
    elapsed = time.monotonic() - started
    content_type = response.headers.get("content-type", "<missing>")
    print(
        f"HTTP response: status={response.status_code}, bytes={len(response.content)}, "
        f"content-type={content_type!r}, elapsed={elapsed:.2f}s, url={response.url}"
    )
    response.raise_for_status()

    if "html" not in content_type.lower():
        raise ScraperError(f"Expected HTML but received {content_type!r} from {response.url}")

    encoding = response.encoding
    if not encoding or encoding.lower() == "iso-8859-1":
        encoding = response.apparent_encoding or "utf-8"
    html = response.content.decode(encoding, errors="replace")

    if is_security_challenge(html):
        raise SecurityChallengeError(
            "Received a JavaScript security challenge instead of the gold-price page "
            f"(HTTP {response.status_code}, {len(response.content)} bytes)"
        )
    return html


def _normalise_text(element: BeautifulSoup) -> str:
    return re.sub(r"\s+", " ", element.get_text(" ", strip=True)).strip()


def _parse_price(value: str) -> float:
    return float(value.replace(",", ""))


def _parse_listed_at(text: str) -> datetime:
    match = re.search(
        r"掛牌時間\s*[:：]\s*(\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2})",
        text,
    )
    if not match:
        raise ParseError("Could not find an anchored '掛牌時間' value")
    return datetime.strptime(match.group(1), "%Y/%m/%d %H:%M").replace(tzinfo=TAIPEI_TZ)


def _quote_from_text(text: str, source_url: str, listed_at_text: str | None = None) -> GoldQuote:
    sell_match = re.search(rf"本行賣出\s*{PRICE_PATTERN}", text)
    buy_match = re.search(rf"本行買進\s*{PRICE_PATTERN}", text)
    if not sell_match or not buy_match:
        raise ParseError("Could not find scoped '本行賣出' and '本行買進' values")

    quote = GoldQuote(
        listed_at=_parse_listed_at(listed_at_text or text),
        buy=_parse_price(buy_match.group(1)),
        sell=_parse_price(sell_match.group(1)),
        source_url=source_url,
    )
    validate_quote(quote)
    return quote


def validate_quote(quote: GoldQuote) -> None:
    """Reject obviously wrong fields before they can pollute history."""
    if not 100 <= quote.buy <= 1_000_000 or not 100 <= quote.sell <= 1_000_000:
        raise ParseError(f"Price outside sanity bounds: buy={quote.buy}, sell={quote.sell}")
    if quote.sell <= quote.buy:
        raise ParseError(f"Expected sell price above buy price: buy={quote.buy}, sell={quote.sell}")
    if quote.sell - quote.buy > quote.sell * 0.25:
        raise ParseError(f"Implausibly wide spread: buy={quote.buy}, sell={quote.sell}")


def parse_gold_price(html: str, source_url: str = PRIMARY_URL) -> GoldQuote:
    """Parse the TWD gold-passbook card/table without relying on page-wide number order."""
    if is_security_challenge(html):
        raise SecurityChallengeError("Cannot parse a security challenge page")

    soup = BeautifulSoup(html, "html.parser")
    page_text = _normalise_text(soup)

    # Current bot.com.tw page: scope extraction to the TWD price card so USD/CNY
    # and physical-gold prices cannot be mistaken for the one-gram passbook quote.
    for card in soup.select(".card"):
        card_text = _normalise_text(card)
        if re.search(r"\bTWD\b", card_text) and "本行賣出" in card_text and "本行買進" in card_text:
            return _quote_from_text(card_text, source_url)

    # rate.bot.com.tw table: find the product row and only inspect its adjacent
    # rows. This tolerates harmless class/column changes while staying product-scoped.
    rows = soup.find_all("tr")
    for index, row in enumerate(rows):
        row_text = _normalise_text(row)
        if "黃金存摺" not in row_text or "本行賣出" not in row_text:
            continue
        scoped_rows = rows[index : index + 3]
        scoped_text = " ".join(_normalise_text(item) for item in scoped_rows)
        if "本行買進" in scoped_text:
            return _quote_from_text(scoped_text, source_url, page_text)

    # Final compatibility fallback for a semantically equivalent but flattened
    # page. It remains bounded to the 黃金存摺 section rather than guessing the
    # first two numbers after "1 公克".
    passbook_match = re.search(
        rf"黃金存摺.{{0,180}}?本行賣出\s*{PRICE_PATTERN}.{{0,260}}?本行買進\s*{PRICE_PATTERN}",
        page_text,
    )
    if passbook_match:
        scoped_text = (
            f"本行賣出 {passbook_match.group(1)} "
            f"本行買進 {passbook_match.group(2)}"
        )
        return _quote_from_text(scoped_text, source_url, page_text)

    title = soup.title.get_text(" ", strip=True) if soup.title else "<missing>"
    markers = {
        "TWD": "TWD" in page_text,
        "黃金存摺": "黃金存摺" in page_text,
        "本行賣出": "本行賣出" in page_text,
        "本行買進": "本行買進" in page_text,
        "掛牌時間": "掛牌時間" in page_text,
    }
    raise ParseError(
        f"No scoped TWD gold-passbook quote found; title={title!r}, "
        f"html_chars={len(html)}, markers={markers}"
    )


def fetch_quote_with_browser(urls: tuple[str, ...] = SOURCE_URLS) -> GoldQuote:
    """Use a real browser when Bank of Taiwan requires JavaScript validation."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised in CI integration
        raise ScraperError(
            "Browser fallback is unavailable; install dependencies from requirements.txt"
        ) from exc

    failures: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        try:
            for url in urls:
                try:
                    started = time.monotonic()
                    response = page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=BROWSER_TIMEOUT_MS,
                    )
                    status = response.status if response else "unknown"
                    print(f"Browser response: status={status}, url={page.url}")
                    page.wait_for_function(
                        """
                        () => {
                            const text = document.body?.innerText || '';
                            return text.includes('TWD') &&
                                   text.includes('本行賣出') &&
                                   text.includes('本行買進') &&
                                   text.includes('掛牌時間');
                        }
                        """,
                        timeout=CHALLENGE_WAIT_MS,
                    )
                    html = page.content()
                    print(
                        f"Browser page ready: title={page.title()!r}, "
                        f"html_chars={len(html)}, elapsed={time.monotonic() - started:.2f}s"
                    )
                    return parse_gold_price(html, url)
                except (PlaywrightError, ScraperError, ValueError) as exc:
                    failure = f"{url}: {type(exc).__name__}: {exc}"
                    failures.append(failure)
                    print(f"Browser source failed: {failure}", file=sys.stderr)
        finally:
            context.close()
            browser.close()

    raise ScraperError("All browser sources failed:\n- " + "\n- ".join(failures))


def _parse_history_time(value: str) -> datetime:
    """Parse both new ISO 8601 timestamps and legacy YYYY/MM/DD HH:MM values."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=parsed.tzinfo or TAIPEI_TZ).astimezone(TAIPEI_TZ)
    except ValueError:
        pass

    try:
        return datetime.strptime(value, "%Y/%m/%d %H:%M").replace(tzinfo=TAIPEI_TZ)
    except ValueError as exc:
        raise ParseError(f"Unsupported history timestamp: {value!r}") from exc


def save_to_json(quote: GoldQuote, filename: Path | str = DATA_FILE) -> bool:
    """Append a quote using ISO 8601; return False when it already exists."""
    path = Path(filename)
    history: list[dict[str, object]] = []
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            raise ScraperError(f"Cannot read valid JSON from {path}: {exc}") from exc
        if not isinstance(loaded, list):
            raise ScraperError(f"Expected a JSON array in {path}, got {type(loaded).__name__}")
        history = loaded

    quote_time = quote.listed_at.astimezone(TAIPEI_TZ)
    for item in history:
        if not isinstance(item, dict) or not isinstance(item.get("time"), str):
            continue
        try:
            existing_time = _parse_history_time(item["time"])
        except ParseError:
            continue
        if existing_time == quote_time:
            same_prices = float(item.get("buy", -1)) == quote.buy and float(item.get("sell", -1)) == quote.sell
            if not same_prices:
                raise ScraperError(
                    "Existing record has the same timestamp but different prices: "
                    f"time={item['time']}, existing=({item.get('buy')}, {item.get('sell')}), "
                    f"new=({quote.buy}, {quote.sell})"
                )
            print(f"Duplicate quote ({item['time']}); data.json is unchanged.")
            return False

    history.append(
        {
            "time": quote_time.isoformat(timespec="minutes"),
            "buy": quote.buy,
            "sell": quote.sell,
            "currency": "TWD",
        }
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            json.dump(history, temporary, ensure_ascii=False, indent=4)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)

    print(
        f"Saved quote: time={quote_time.isoformat(timespec='minutes')}, "
        f"buy={quote.buy:g}, sell={quote.sell:g}, records={len(history)}"
    )
    return True


def get_gold_price(filename: Path | str = DATA_FILE) -> bool:
    """Try lightweight HTTP first, then fall back to a JavaScript-capable browser."""
    failures: list[str] = []
    session = build_session()
    print(
        "Fetching Bank of Taiwan gold price "
        f"(connect timeout={CONNECT_TIMEOUT_SECONDS}s, read timeout={READ_TIMEOUT_SECONDS}s, "
        "transient retries=3)..."
    )

    for url in SOURCE_URLS:
        try:
            quote = parse_gold_price(fetch_html(session, url), url)
            print(f"Source succeeded with direct HTTP: {url}")
            return save_to_json(quote, filename)
        except (requests.RequestException, ScraperError, ValueError) as exc:
            failure = f"{url}: {type(exc).__name__}: {exc}"
            failures.append(failure)
            print(f"Direct HTTP source failed: {failure}", file=sys.stderr)

    print("Direct HTTP could not reach price content; starting browser fallback.")
    try:
        quote = fetch_quote_with_browser()
        print(
            "Quote parsed successfully: "
            f"listed_at={quote.listed_at.isoformat(timespec='minutes')}, "
            f"buy={quote.buy:g}, sell={quote.sell:g}, source={quote.source_url}"
        )
        return save_to_json(quote, filename)
    except (ScraperError, ValueError) as exc:
        failures.append(f"browser fallback: {type(exc).__name__}: {exc}")
        raise ScraperError("Unable to obtain a trustworthy quote:\n- " + "\n- ".join(failures)) from exc


def main() -> int:
    try:
        get_gold_price()
    except Exception as exc:
        print(f"Scraper failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

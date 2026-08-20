import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from main import (
    GoldQuote,
    ParseError,
    SecurityChallengeError,
    TAIPEI_TZ,
    parse_gold_price,
    save_to_json,
)


class ParseGoldPriceTests(unittest.TestCase):
    def test_parses_twd_card_without_using_other_currency_prices(self):
        html = """
        <html><head><title>黃金業務</title></head><body>
          <div class="card">
            <div>美金 USD 英兩</div>
            <span>本行賣出</span><span>4,504.95</span>
            <span>本行買進</span><span>4,466.25</span>
            <p>掛牌時間：2026/08/20 12:44</p>
          </div>
          <div class="card">
            <div>新臺幣 TWD 公克</div>
            <span>本行賣出</span><span>4,630.00</span>
            <span>本行買進</span><span>4,580.00</span>
            <p>掛牌時間：2026/08/20 12:44</p>
          </div>
        </body></html>
        """

        quote = parse_gold_price(html)

        self.assertEqual(quote.listed_at.isoformat(timespec="minutes"), "2026-08-20T12:44+08:00")
        self.assertEqual(quote.buy, 4580.0)
        self.assertEqual(quote.sell, 4630.0)

    def test_parses_legacy_passbook_rows(self):
        html = """
        <html><body>
          <p>掛牌時間：2026/08/20 12:44</p>
          <table>
            <tr><th>品名/規格</th><th>1 公克</th></tr>
            <tr><td>黃金存摺</td><td>本行賣出</td><td>4,630</td></tr>
            <tr><td>本行買進</td><td>4,580</td></tr>
            <tr><td>黃金條塊</td><td>本行賣出</td><td>4,633,520</td></tr>
          </table>
        </body></html>
        """

        quote = parse_gold_price(html, "https://rate.bot.com.tw/gold")

        self.assertEqual(quote.buy, 4580.0)
        self.assertEqual(quote.sell, 4630.0)

    def test_rejects_security_challenge_disguised_as_success(self):
        html = "<html><title>Challenge Validation</title><div class='sec-container'></div></html>"
        with self.assertRaises(SecurityChallengeError):
            parse_gold_price(html)

    def test_rejects_unscoped_numbers(self):
        html = "<html><body>掛牌時間：2026/08/20 12:44 1 公克 4630 4580</body></html>"
        with self.assertRaises(ParseError):
            parse_gold_price(html)


class SaveHistoryTests(unittest.TestCase):
    def test_appends_iso_timestamp_and_preserves_legacy_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            legacy = [
                {
                    "time": "2026/06/29 16:52",
                    "buy": 4127.0,
                    "sell": 4177.0,
                    "currency": "TWD",
                }
            ]
            path.write_text(json.dumps(legacy), encoding="utf-8")
            quote = GoldQuote(
                datetime(2026, 8, 20, 12, 44, tzinfo=TAIPEI_TZ),
                buy=4580.0,
                sell=4630.0,
                source_url="https://www.bot.com.tw/",
            )

            changed = save_to_json(quote, path)
            saved = json.loads(path.read_text(encoding="utf-8"))

            self.assertTrue(changed)
            self.assertEqual(saved[0], legacy[0])
            self.assertEqual(saved[1]["time"], "2026-08-20T12:44+08:00")

    def test_deduplicates_equivalent_legacy_and_iso_times(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            original = [
                {
                    "time": "2026/08/20 12:44",
                    "buy": 4580.0,
                    "sell": 4630.0,
                    "currency": "TWD",
                }
            ]
            path.write_text(json.dumps(original), encoding="utf-8")
            quote = GoldQuote(
                datetime(2026, 8, 20, 12, 44, tzinfo=TAIPEI_TZ),
                buy=4580.0,
                sell=4630.0,
                source_url="https://www.bot.com.tw/",
            )

            changed = save_to_json(quote, path)

            self.assertFalse(changed)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)


if __name__ == "__main__":
    unittest.main()

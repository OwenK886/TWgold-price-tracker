# TWgold-price-tracker

追蹤臺灣銀行新臺幣黃金存摺買賣價，並以 GitHub Pages 顯示歷史趨勢。

## 更新方式

GitHub Actions 會在臺灣時間週一至週五 12:00、18:00、22:00 執行 `main.py`。爬蟲先以一般 HTTP 請求讀取臺灣銀行官方頁面；若收到需要 JavaScript 的安全驗證頁，會改用 Chromium 讀取同一個官方來源。新資料以帶有臺北時區偏移的 ISO 8601 時間寫入 `data.json`，前端仍相容既有的 `YYYY/MM/DD HH:MM` 資料。

網站的日期範圍以目前時間為基準；最新資料超過 72 小時時會顯示過期警告，以容納一般週末但仍能揭露持續失敗的更新。

## 歷史資料回補

`data.json` 中 2026/06/30 至 2026/08/19 的缺口已由臺灣銀行官方單日營業時間與盤後歷史牌價回補。每個營業日分別選取不晚於原排程 12:00、18:00、22:00 的最近一筆實際掛牌價；若官方沒有牌價就跳過，不做內插或推算。回補紀錄使用 ISO 8601 時間並帶有 `backfilled: true` 標記。

## 本機驗證

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
python main.py
```

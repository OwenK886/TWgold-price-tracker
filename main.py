import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

def get_gold_price():
    # 嘗試兩個不同的 URL，增加成功率
    urls = [
        "https://rate.bot.com.tw/gold?Lang=zh-TW",
        "https://rate.bot.com.tw/gold/csv/ltm/TWD/0"
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    price = None
    
    for url in urls:
        try:
            print(f"嘗試抓取: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"連線狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                # 如果是 HTML 頁面
                soup = BeautifulSoup(response.text, 'html.parser')
                # 關鍵：台銀的行動版與桌機版結構不同，我們用更廣的搜尋
                tds = soup.find_all('td')
                for td in tds:
                    # 尋找含有價格的屬性
                    if td.get('data-table') == "本行賣出" or "text-right" in td.get('class', []):
                        val = td.get_text().strip().replace(',', '')
                        if val.replace('.', '', 1).isdigit() and len(val) > 2:
                            price = float(val)
                            print(f"成功在網頁中找到價格: {price}")
                            break
                if price: break
        except Exception as e:
            print(f"嘗試 {url} 時發生錯誤: {e}")

    if price:
        save_to_json(price)
    else:
        print("!!! 關鍵錯誤：所有抓取方式都失敗了 !!!")
        # 印出部分網頁原始碼，讓我們診斷是否被擋或結構改變
        print("網頁前 300 個字：", response.text[:300])

def save_to_json(price):
    filename = 'data.json'
    history = []
    
    # 如果檔案存在就讀取，不存在就建立新的
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except:
                history = []
    
    history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "price": price
    })
    
    # 寫入檔案
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
    print(f"成功！檔案已儲存。目前總計 {len(history)} 筆數據。")

if __name__ == "__main__":
    get_gold_price()

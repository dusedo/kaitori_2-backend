# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re
import urllib.parse
import os

app = Flask(__name__)
CORS(app)

# Seleniumの設定
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")

# Heroku環境変数からChromeのパスを取得
chrome_path = os.environ.get('GOOGLE_CHROME_BIN', 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
# Heroku環境変数からChromedriverのパスを取得
driver_path = os.environ.get('CHROMEDRIVER_PATH', 'C:\\path\\to\\chromedriver.exe')

def fetch_with_retry(url, max_retries=3):
    for _ in range(max_retries):
        try:
            driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
            driver.get(url)
            time.sleep(2)  # ページが完全にロードされるのを待つ
            return driver
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            time.sleep(1)
    return None

def fetch_kaitori_1chome(jan, driver):
    url = f"https://www.1-chome.com/elec/search/{jan}"
    driver.get(url)
    time.sleep(2)
    try:
        twitter_link = driver.find_element("xpath", '//a[contains(@href, "twitter.com/share")]')
        href = twitter_link.get_attribute('href')
        decoded_text = urllib.parse.unquote(href)
        match = re.search(r'買取価格：¥([0-9,]+)', decoded_text)
        if match:
            return int(match.group(1).replace(',', ''))
    except Exception as e:
        print(f"Error fetching 買取1丁目 for JAN {jan}: {e}")
    return None

def fetch_morimori(jan, driver):
    url = f"https://www.morimori-kaitori.jp/search/{jan}?sk={jan}"
    driver.get(url)
    time.sleep(2)
    try:
        wechat_link = driver.find_element("css selector", 'a[wechat]')
        wechat_text = wechat_link.get_attribute('wechat')
        match = re.search(r'買取価格：([0-9,]+)円', wechat_text)
        if match:
            return int(match.group(1).replace(',', ''))
    except Exception as e:
        print(f"Error fetching 森森買取 for JAN {jan}: {e}")
    return None

def fetch_kaitori_wiki(jan, driver):
    url = f"https://gamekaitori.jp/search?type=&q={jan}#searchtop"
    driver.get(url)
    time.sleep(2)
    try:
        span_elements = driver.find_elements("tag name", 'span')
        for span in span_elements:
            if '円' in span.text:
                price = re.sub(r'[^\d]', '', span.text)
                if price:
                    return int(price)
    except Exception as e:
        print(f"Error fetching 買取Wiki for JAN {jan}: {e}")
    return None

def fetch_kaitori_rudeya(jan, driver):
    url = f"https://kaitori-rudeya.com/search/index/{jan}/-"
    driver.get(url)
    time.sleep(2)
    try:
        div = driver.find_element("css selector", 'div.td2wrap')
        price_text = re.sub(r'[^\d]', '', div.text)
        if price_text:
            return int(price_text)
    except Exception as e:
        print(f"Error fetching 買取ルデヤ for JAN {jan}: {e}")
    return None

def fetch_prices(jan):
    driver = fetch_with_retry(f"https://www.1-chome.com/elec/search/{jan}")
    if not driver:
        return {
            "買取1丁目": None,
            "森森買取": None,
            "買取Wiki": None,
            "買取ルデヤ": None
        }
    prices = {}
    try:
        prices["買取1丁目"] = fetch_kaitori_1chome(jan, driver)
        prices["森森買取"] = fetch_morimori(jan, driver)
        prices["買取Wiki"] = fetch_kaitori_wiki(jan, driver)
        prices["買取ルデヤ"] = fetch_kaitori_rudeya(jan, driver)
    finally:
        driver.quit()
    return prices

@app.route('/api/fetch-prices', methods=['POST'])
def get_prices():
    data = request.get_json()
    janCodes = data.get('janCodes', [])

    if not isinstance(janCodes, list):
        return jsonify({'error': 'janCodes must be a list.'}), 400

    results = []
    for jan in janCodes:
        if not jan:
            results.append(None)
            continue
        prices = fetch_prices(jan)
        results.append({
            'jan': jan,
            'prices': prices
        })
        time.sleep(2)  # サイト間で2秒待機
    filtered_results = [res for res in results if res is not None]
    return jsonify({'results': filtered_results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

import requests, time, random, os, threading
from flask import Flask
from dotenv import load_dotenv

load_dotenv()
ALL_CIKS = tuple(os.getenv("CIK", "xxxxxxxxxx").split(","))
BOT_NAME = os.getenv("BOT_NAME", "MySecBot")
EMAIL = os.getenv("EMAIL", "your@email.com")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BASE_DELAY = max(float(os.getenv("BASE_DELAY", 3)), 1.0)

HEADERS = {
    "User-Agent": f"{BOT_NAME} {EMAIL}"
}

seen_documents = set()

def get_date():
    #return "2026-03-18"
    gm_time = time.gmtime()
    return f"{gm_time.tm_year:04d}-{gm_time.tm_mon:02d}-{gm_time.tm_mday:02d}"


def clear_seen():
    seen_documents.clear()

def send_telegram_message(msg, to, token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    data = {
        "chat_id": to,
        "text": msg
    }
    
    response = requests.post(url, data=data)
    result = response.json()

    if not result.get("ok"):
        raise Exception(f"Telegram error: {result}")

    return result

def fetch_data(url):
    response = requests.get(url, headers=HEADERS, timeout=5)
    response.raise_for_status()

    if "application/json" not in response.headers.get("Content-Type", ""):
        raise ValueError("Response is not JSON")

    return response.json()

def process_data(data, target_date, cik):
    filings = data["filings"]["recent"]
    results = []

    for filing_date, accession, primary_doc in zip(
        filings["filingDate"],
        filings["accessionNumber"],
        filings["primaryDocument"]
    ):
        if filing_date < target_date:
            break

        if filing_date > target_date:
            continue

        if accession in seen_documents:
            continue

        seen_documents.add(accession)

        acc_number = accession.replace("-", "")
        document_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{acc_number}/{primary_doc}"
        )

        results.append(document_url)

    return results

def handle_output(output, chat_id=None, bot_token=None):
    try:
        send_telegram_message(output, chat_id, bot_token)
        print("Telegram message OK")
    except Exception as e:
        print(f"Failed to send Telegram message:\n{e}\nDefaulting to print.\n")
        print(output)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def main():
    cik_index = 0
    delay = BASE_DELAY
    last_date = get_date()

    while True:
        try:
            URL = f"https://data.sec.gov/submissions/CIK{ALL_CIKS[cik_index]}.json"

            data = fetch_data(URL)
            print(f"Fetched OK: CIK = {ALL_CIKS[cik_index]}")

            delay = BASE_DELAY

            today = get_date()
            document_urls = process_data(data, today, ALL_CIKS[cik_index])

            for url in document_urls:
                output = f"Document found for: {data['name']}, CIK number: {ALL_CIKS[cik_index]}. Click here to see document:\n{url}"
                handle_output(output, chat_id=CHAT_ID, bot_token=TELEGRAM_BOT_TOKEN)
            
            if today != last_date:
                clear_seen()
            last_date = today

            cik_index += 1
            cik_index %= len(ALL_CIKS)
        
        except (requests.exceptions.RequestException, ValueError) as e:
            delay = min(delay * 2, 60)
            print(f"Error: {e} -> backing off to {delay}s")

        time.sleep(delay + random.uniform(0, 0.5))

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    main()

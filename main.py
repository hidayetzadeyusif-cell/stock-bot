from config import load_config, validate_config, save_config
from telegram import TelegramBot

import requests, random, os, json, time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()
BOT_NAME = os.getenv("BOT_NAME", "MySecBot")
EMAIL = os.getenv("EMAIL", "your@email.com")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "None")
CHAT_ID = os.getenv("CHAT_ID", "None")
LOOKBACK_DAYS = 3

HEADERS = {
    "User-Agent": f"{BOT_NAME} {EMAIL}"
}

telegram_bot = TelegramBot(TELEGRAM_BOT_TOKEN, CHAT_ID)

config = load_config()
validate_config(config)

SEEN_FILE = "seen.json"
def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

seen_documents = load_seen()
new_document_exists = False

def fetch_data(url):
    response = requests.get(url, headers=HEADERS, timeout=5)
    response.raise_for_status()

    if "application/json" not in response.headers.get("Content-Type", ""):
        raise ValueError("Response is not JSON")

    return response.json()

def process_data(data, cik):
    global new_document_exists

    filings = data["filings"]["recent"]
    results = []

    cutoff_date = (
        datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    ).date()

    for filing_date, accession, primary_doc in zip(
        filings["filingDate"],
        filings["accessionNumber"],
        filings["primaryDocument"]
    ):
        filing_date_obj = datetime.strptime(
            filing_date,
            "%Y-%m-%d"
        ).date()

        if filing_date_obj < cutoff_date:
            break

        if accession in seen_documents:
            continue

        seen_documents.add(accession)
        new_document_exists = True

        acc_number = accession.replace("-", "")
        document_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{acc_number}/{primary_doc}"
        )

        results.append(document_url)

    return results


def main():
    config_changed = telegram_bot.process_commands(config)
    if config_changed:
        print("Old config:", config)
        save_config(config)
        print("New config:", config)
        print("Updated config")

    for cik in config["ciks"]:
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"

            data = fetch_data(url)

            print(f"Fetched OK: CIK = {cik}")

            document_urls = process_data(data, cik)

            for doc_url in document_urls:
                output = (
                    f"Document found for: {data['name']}, "
                    f"CIK number: {cik}.\n{doc_url}"
                )

                telegram_bot.handle_output(output)

            time.sleep(0.5 + random.uniform(0, 0.5))

        except Exception as e:
            print(f"Error processing {cik}: {e}")

    print("Finished cycle OK")

    if new_document_exists:
        save_seen(seen_documents)


if __name__ == "__main__":
    main()

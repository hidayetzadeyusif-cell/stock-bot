import requests, random, os, json, time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "ciks": []
}

SEEN_FILE = "seen.json"
new_document_exists = False

def load_config():
    config = DEFAULT_CONFIG.copy()

    try:
        with CONFIG_FILE.open() as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Config must be a JSON object.")

        config.update(data)

    except FileNotFoundError:
        print("config.json not found, using defaults.")

    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        print("Using defaults.")

    except Exception as e:
        print(f"Error loading config: {e}")
        print("Using defaults.")

    return config

def validate_config(config):
    if not isinstance(config["ciks"], list):
        raise ValueError("'ciks' must be a list.")

    if not all(isinstance(cik, str) for cik in config["ciks"]):
        raise ValueError("All CIKs must be strings.")
    
    if not all(len(cik) == 10 for cik in config["ciks"]):
        raise ValueError("All CIKs must be 10 digits long.")

def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


config = load_config()
validate_config(config)

seen_documents = load_seen()

ALL_CIKS = tuple(config["ciks"])
BOT_NAME = os.getenv("BOT_NAME", "MySecBot")
EMAIL = os.getenv("EMAIL", "your@email.com")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "None")
CHAT_ID = os.getenv("CHAT_ID", "None")
LOOKBACK_DAYS = 3

HEADERS = {
    "User-Agent": f"{BOT_NAME} {EMAIL}"
}


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


def handle_output(output, chat_id=None, bot_token=None):
    try:
        send_telegram_message(output, chat_id, bot_token)
        print("Telegram message OK")
    except Exception as e:
        print(f"Failed to send Telegram message:\n{e}\n")
        print(output)


def main():
    for cik in ALL_CIKS:
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

                handle_output(
                    output,
                    chat_id=CHAT_ID,
                    bot_token=TELEGRAM_BOT_TOKEN
                )

            time.sleep(0.5 + random.uniform(0, 0.5))

        except Exception as e:
            print(f"Error processing {cik}: {e}")

    print("Finished cycle OK")

    if new_document_exists:
        save_seen(seen_documents)


if __name__ == "__main__":
    main()

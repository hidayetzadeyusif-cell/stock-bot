import requests, time, random, os, json
from dotenv import load_dotenv

load_dotenv()

ALL_CIKS = tuple(os.getenv("CIK", "xxxxxxxxxx").split(","))
BOT_NAME = os.getenv("BOT_NAME", "MySecBot")
EMAIL = os.getenv("EMAIL", "your@email.com")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "None")
CHAT_ID = os.getenv("CHAT_ID", "None")

HEADERS = {
    "User-Agent": f"{BOT_NAME} {EMAIL}"
}

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


def get_date():
    gm_time = time.gmtime()
    return f"{gm_time.tm_year:04d}-{gm_time.tm_mon:02d}-{gm_time.tm_mday:02d}"


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
        print(f"Failed to send Telegram message:\n{e}\n")
        print(output)


def main():
    today = get_date()

    for cik in ALL_CIKS:
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"

            data = fetch_data(url)

            print(f"Fetched OK: CIK = {cik}")

            document_urls = process_data(data, today, cik)

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

    save_seen(seen_documents)


if __name__ == "__main__":
    main()

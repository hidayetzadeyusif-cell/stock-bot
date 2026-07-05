from config import is_valid_cik

import requests

class TelegramBot:
    def __init__(self, bot_token, chat_id):
        self.token = bot_token
        self.chat_id = chat_id
        
    def send_telegram_message(self, msg):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        data = {
            "chat_id": self.chat_id,
            "text": msg
        }

        response = requests.post(url, data=data)
        result = response.json()

        if not result.get("ok"):
            raise Exception(f"Telegram error: {result}")

        return result

    def get_updates(self, offset=None):
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"

        params = {}

        if offset is not None:
            params["offset"] = offset

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        if not result["ok"]:
            raise Exception(result)

        return result["result"]

    def process_commands(self, config):
        config_changed = False

        updates = self.get_updates(
            config["last_update_id"] + 1
        )

        for update in updates:
            config["last_update_id"] = update["update_id"]

            message = update.get("message")

            if message is None:
                continue

            if str(message["chat"]["id"]) != self.chat_id:
                continue

            text = message.get("text", "")

            if not text.startswith("/"):
                continue

            print("Command processed:", text)
            
            parts = text.split()

            command = parts[0].lower()
            args = parts[1:]

            match command:
                case "/help":
                    config_changed = True
                    self.send_telegram_message(
                        "Available commands:\n\n"
                        "/list\n"
                        "/add <CIK>\n"
                        "/remove <CIK>"
                    )

                case "/list":
                    if config["ciks"]:
                        msg = "Currently monitored:\n\n"

                        msg += "\n".join(config["ciks"])

                    else:
                        msg = "No CIKs are currently being monitored."

                    config_changed = True
                    self.send_telegram_message(msg)

                case "/add":
                    if len(args) != 1:
                        self.send_telegram_message("Usage: /add <CIK>")
                        continue

                    cik = args[0]

                    if not is_valid_cik(cik):
                        self.send_telegram_message("CIKs must be exactly 10 digits.")
                        continue

                    if cik in config["ciks"]:
                        self.send_telegram_message("Already monitoring that CIK.")
                        continue

                    config["ciks"].append(cik)
                    config_changed = True

                    self.send_telegram_message(f"Added {cik}.")

                case "/remove":
                    if len(args) != 1:
                        self.send_telegram_message("Usage: /remove <CIK>")
                        continue

                    cik = args[0]

                    if cik not in config["ciks"]:
                        self.send_telegram_message("CIK already not monitored.")
                        continue

                    config["ciks"].remove(cik)
                    config_changed = True

                    self.send_telegram_message(f"Removed {cik}.")
    
        return config_changed
    
    def handle_output(self, output):
        try:
            self.send_telegram_message(output)
            print("Telegram message OK")
        except Exception as e:
            print(f"Failed to send Telegram message:\n{e}\n")
            print(output)

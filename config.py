import json, os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "ciks": [],
    "last_update_id": 0
}

def load_config():
    config = DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r") as  f:
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

def is_valid_cik(cik):
    return (
        isinstance(cik, str)
        and cik.isdigit()
        and len(cik) == 10
    )

def validate_config(config):
    if not isinstance(config["ciks"], list):
        raise ValueError("'ciks' must be a list.")

    if not all(isinstance(cik, str) for cik in config["ciks"]):
        raise ValueError("All CIKs must be strings.")
    
    if not all(is_valid_cik(cik) for cik in config["ciks"]):
        raise ValueError("All CIKs must be 10 digits long.")
    
def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

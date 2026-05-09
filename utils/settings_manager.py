import os
import json
import config

SETTINGS_FILE = os.path.join("data", "settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {"target_channel": config.CHANNEL_LINK}

def save_settings(settings):
    # Ensure data directory exists
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

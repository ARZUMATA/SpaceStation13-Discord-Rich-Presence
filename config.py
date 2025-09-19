import json
import os

from dotenv import load_dotenv
load_dotenv()  # Loads .env file

CONFIG_FILE = "config.json"

# Default config if file doesn't exist
DEFAULT_CONFIG = {
    "UPDATE_INTERVAL": 15,
    "SERVER_OVERRIDES": {
        "92.63.189.15:7888": {
            "name": "BlueMoon",
            "icon": "ss13_bluemoon"
        }
    }
}

# Load config
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config_data = json.load(f)
else:
    # Create default config file
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    config_data = DEFAULT_CONFIG

# Parse SERVER_OVERRIDES: convert "host:port" string keys to (host, int(port)) tuples
raw_overrides = config_data.get("SERVER_OVERRIDES", {})
SERVER_OVERRIDES = {}
for key, value in raw_overrides.items():
    host, port = key.split(":", 1)
    SERVER_OVERRIDES[(host.strip(), int(port))] = value

# Other config values
CLIENT_ID = (
    os.getenv("CLIENT_ID") or
    config_data.get("CLIENT_ID") or
    DEFAULT_CONFIG["CLIENT_ID"]
)

if not CLIENT_ID:
    raise RuntimeError("CLIENT_ID must be set via environment variable or config.json")

UPDATE_INTERVAL = config_data.get("UPDATE_INTERVAL", DEFAULT_CONFIG["UPDATE_INTERVAL"])
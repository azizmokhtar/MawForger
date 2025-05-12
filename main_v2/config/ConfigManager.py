import os
import ast
from typing import Dict, Any
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self):
        load_dotenv(dotenv_path=".env")
        self.config = {
            "TELEGRAM_MESSENGER_TOKEN": os.getenv("TELEGRAM_MESSENGER_TOKEN"),
            "MESSENGER_CHAT_ID": os.getenv("MESSENGER_CHAT_ID"),
            "TELEGRAM_LISTENER_TOKEN": os.getenv("TELEGRAM_LISTENER_TOKEN"),
            "PUBLIC_USER_ADDRESS": os.getenv("PUBLIC_USER_ADDRESS"),
            "TP": float(os.getenv("TP", "1")),
            "TTP_PERCENT": float(os.getenv("TTP_PERCENT", "0.05")),
            "BUY_SIZE": float(os.getenv("BUY_SIZE", "11")),
            "LEVERAGE": int(os.getenv("LEVERAGE", "5")),
            "MULTIPLIER": float(os.getenv("MULTIPLIER", "2")),
            "DEVIATIONS": [float(value) for value in ast.literal_eval(os.getenv("DEVIATIONS", "[1,1.6,6,13]"))],
            "CONNECTION_ERROR_RETRY_DELAY": int(os.getenv("CONNECTION_ERROR_RETRY_DELAY", "60")),
            "CONNECTION_ERROR_MAX_RETRIES": int(os.getenv("CONNECTION_ERROR_MAX_RETRIES", "50")),
            "HEARTBEAT_INTERVAL": int(os.getenv("HEARTBEAT_INTERVAL", "30")),
            "INITIAL_SYMBOLS": ast.literal_eval(os.getenv("INITIAL_SYMBOLS", '["HYPE", "SUI", "ADA"]')),
        }

    def get(self, key: str, default=None) -> Any:
        return self.config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.config[key]
    
    def print_config(self) -> None:
        """Prints all configuration values in a readable format."""
        print("\n=== Configuration ===")
        for key, value in self.config.items():
            print(f"{key}: {value}")
        print("=====================\n")
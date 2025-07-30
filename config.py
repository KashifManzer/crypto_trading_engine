import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# A centralized place to fetch API keys from environment variables
# This keeps sensitive information out of the source code.
API_KEYS = {
    "binance": {
        "api_key": os.getenv("BINANCE_API_KEY", ""),
        "api_secret": os.getenv("BINANCE_API_SECRET", ""),
    },
    "kucoin": {
        "api_key": os.getenv("KUCOIN_API_KEY", ""),
        "api_secret": os.getenv("KUCOIN_API_SECRET", ""),
        "passphrase": os.getenv("KUCOIN_PASSPHRASE", ""),
    },
    "bybit": {
        "api_key": os.getenv("BYBIT_API_KEY", ""),
        "api_secret": os.getenv("BYBIT_API_SECRET", ""),
    },
    "okx": {
        "api_key": os.getenv("OKX_API_KEY", ""),
        "api_secret": os.getenv("OKX_API_SECRET", ""),
        "passphrase": os.getenv("OKX_PASSPHRASE", ""),
    },
    "bitmart": {
        "api_key": os.getenv("BITMART_API_KEY", ""),
        "api_secret": os.getenv("BITMART_API_SECRET", ""),
        "memo": os.getenv("BITMART_MEMO", ""),
    }
}

import sys
import argparse
import uvicorn

from fantomex.api import app
from fantomex.config import get_settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start Fantomex Server")
    parser.add_argument("--auth", action="store_true", help="Enable API key authentication")
    parser.add_argument("--api-key", type=str, default="fantomex-secret-key", help="API key to use if auth is enabled")
    args, unknown = parser.parse_known_args()
    
    settings = get_settings()
    
    # Enable auth via CLI flag or Env variables
    import os
    env_api_key = os.environ.get("FANTOMEX_API_KEY")
    
    if args.auth:
        settings.enable_auth = True
        settings.api_key = args.api_key
        print(f"\n[FANTOMEX AUTH ENABLED] API Key required on all writes: '{settings.api_key}'\n")
    elif env_api_key:
        settings.enable_auth = True
        settings.api_key = env_api_key
        print("\n[FANTOMEX AUTH ENABLED] API Key enabled via FANTOMEX_API_KEY env variable\n")
    else:
        print("\n[FANTOMEX AUTH DISABLED] Access is open to all clients\n")

    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level)

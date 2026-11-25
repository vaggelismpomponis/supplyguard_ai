# Environment checker: loads .env, displays Python version, app environment, log level, and venv status

import os
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set app environment with local default, adjust log level accordingly
APP_ENV = os.getenv("APP_ENV", "local")
LOG_LEVEL = "DEBUG" if APP_ENV == "local" else "INFO"


def check_environment() -> None:
    # Display Python version, environment type, log level
    print(f"Python: {sys.version.split()[0]}")
    print(f"Environment: {APP_ENV}")
    print(f"Log Level: {LOG_LEVEL}")

    # Check if virtual environment is active
    venv_active = sys.prefix != sys.base_prefix
    print(f"Virtual environment: {venv_active}")


if __name__ == "__main__":
    # Show environment details only in local, skip verbose output in production
    if APP_ENV == "local":
        check_environment()
    else:
        print("PRODUCTION ENVIRONMENT")

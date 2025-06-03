import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_PATH: str = os.getenv("DB_PATH", "library.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
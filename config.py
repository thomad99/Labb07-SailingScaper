import os
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(var_name: str, default=None) -> str:
    value = os.getenv(var_name)
    if value is None:
        if default is None:
            raise ValueError(f"Environment variable {var_name} is not set")
        return default
    return value

# Database configuration
DB_URL = get_env_variable("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sailing_results")
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

# OpenAI configuration
OPENAI_API_KEY = get_env_variable("OPENAI_API_KEY")

# Scraping configuration
SCRAPE_BASE_URL = get_env_variable("SCRAPE_BASE_URL", "https://example-sailing-results.com/results")

# Use it in your code
DB_URL = get_env_variable("DATABASE_URL")
OPENAI_API_KEY = get_env_variable("OPENAI_API_KEY") 

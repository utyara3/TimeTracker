import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
STATES_DB_PATH = os.getenv('STATES_DB_PATH')
USERS_DB_PATH = os.getenv('USERS_DB_PATH')

DEFAULT_STATES = [
    "study"
    "work",
    "chill",
    "wait",
    "other"
]

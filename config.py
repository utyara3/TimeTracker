import os
import sys
from dotenv import load_dotenv

is_test = '-test' in sys.argv or '--test' in sys.argv
env_file = '.env-test' if is_test and os.path.exists('.env-test') else '.env'

load_dotenv(env_file)

BOT_TOKEN = os.getenv('BOT_TOKEN')
STATES_DB_PATH = os.getenv('STATES_DB_PATH')
USERS_DB_PATH = os.getenv('USERS_DB_PATH')

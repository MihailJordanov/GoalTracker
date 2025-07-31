import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL environment variable")
    return psycopg2.connect(database_url)

import psycopg2

# Конфигурация за връзка с PostgreSQL
DATABASE_CONFIG = {
    'dbname': 'YourTeam',
    'user': 'misho',
    'password': '1234',
    'host': 'localhost',
    'port': 5432
}

# Функция за връзка с базата данни
def get_db_connection():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    return conn
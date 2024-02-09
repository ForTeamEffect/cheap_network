import os

from dotenv import load_dotenv

load_dotenv()

# postgres
pg_user = os.getenv('PG_USER')
pg_password = os.getenv('PG_PASSWORD')
pg_address = os.getenv('PG_ADDRESS')
pg_port = os.getenv('PG_PORT')
pg_server_name = os.getenv('PG_SERVER_NAME')

# binance
api_key_bin = os.getenv('API_KEY_BIN')
api_secret_bin = os.getenv('API_SECRET_BIN')

# kucoin
api_key_ku = os.getenv('API_KEY_KU')
api_secret_ku = os.getenv('API_SECRET_KU')
api_passphrase_ku = os.getenv('API_PASSPHRASE_KU')

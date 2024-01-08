from dotenv import dotenv_values
import os

class Config:
    db_url: str = None
    app_name: str = "bookstore_catalog"
    version: str = "v1"
    catalog_host: str = 'localhost'
    # Read from .env file
    try:
        db_url = dotenv_values('.env')['DB_URL']
        app_name = dotenv_values('.env')['APP_NAME']
    except Exception as e:
        print('No .env file with DB_URL and APP_NAME found...')
    # Read from ENV
    db_url = os.getenv('DB_URL', default=db_url)
    app_name = os.getenv('APP_NAME', default=app_name)
    catalog_host = os.getenv('BOOKSTORE_CATALOG_SERVICE_HOST', default=catalog_host)

    broken: bool = False

CONFIG = Config()
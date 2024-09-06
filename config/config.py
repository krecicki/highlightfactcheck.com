import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Auth0 by Okta
    AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
    AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
    AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")

    # The flask secret key
    APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")
    
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Database configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))

    # Flask configuration
    SECRET_KEY = os.getenv('APP_SECRET_KEY')

    # Stops forking of the tokenizers
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
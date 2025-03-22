import os

from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# SECRET = "YOUR_SECRET_HERE"

# DB_USER = 'python_hw3'
# DB_PASS = 'python_hw3'
# DB_HOST = 'localhost'
# DB_PORT = 5432
# DB_NAME = 'python_hw3'
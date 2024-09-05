import mysql.connector
import time
from config.config import Config

import mysql.connector
import time
from config.config import Config
from tools.logger import logger


class UserDB:
    def __init__(self):
        self.config = {
            'host': Config.MYSQL_HOST,
            'user': Config.MYSQL_USER,
            'password': Config.MYSQL_PASSWORD,
            'database': Config.MYSQL_DATABASE,
            'port': Config.MYSQL_PORT
        }

    def get_db_connection(self):
        while True:
            try:
                return mysql.connector.connect(**self.config)
            except mysql.connector.Error as err:
                logger.error(f"Database connection error: {err}")
                time.sleep(5)

    def execute_query(self, query, params=None, fetch=False):
        with self.get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True, buffered=True)
            try:
                cursor.execute(query, params or ())
                if fetch:
                    return cursor.fetchall()
                conn.commit()
                return cursor.rowcount
            except mysql.connector.Error as err:
                logger.error(f"Query execution error: {err}")
                conn.rollback()
                raise

    def insert_user(self, nickname, name, user_id, api_key):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor(buffered=True)
            sql = "INSERT INTO users (nickname, name, user_id, api_key) VALUES (%s, %s, %s, %s)"
            val = (nickname, name, user_id, api_key)
            mycursor.execute(sql, val)
            mydb.commit()

    def get_user_by_id(self, user_id):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor(dictionary=True, buffered=True)
            mycursor.execute(
                "SELECT * FROM users WHERE user_id = %s", (user_id,))
            return mycursor.fetchone()

    def update_user_settings(self, user_id, **kwargs):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor()
            set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
            sql = f"UPDATE users SET {set_clause} WHERE user_id = %s"
            val = tuple(kwargs.values()) + (user_id,)
            mycursor.execute(sql, val)
            mydb.commit()
            if mycursor.rowcount == 0:
                raise Exception(f"No user found with user_id: {user_id}")

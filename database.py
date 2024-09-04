import mysql.connector
import time
from config import Config
import logging
import datetime

def get_db_connection():
    while True:
        try:
            mydb = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DATABASE,
                port=Config.MYSQL_PORT
            )
            return mydb
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            time.sleep(5)

def insert_user(nickname, name, user_id, api_key):
    with get_db_connection() as mydb:
        mycursor = mydb.cursor(buffered=True)
        sql = "INSERT INTO users (nickname, name, user_id, api_key) VALUES (%s, %s, %s, %s)"
        val = (nickname, name, user_id, api_key)
        mycursor.execute(sql, val)
        mydb.commit()

def get_user_by_id(user_id):
    with get_db_connection() as mydb:
        mycursor = mydb.cursor(dictionary=True, buffered=True)
        mycursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return mycursor.fetchone()

def update_user_settings(user_id, **kwargs):
    with get_db_connection() as mydb:
        mycursor = mydb.cursor()
        set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
        sql = f"UPDATE users SET {set_clause} WHERE user_id = %s"
        val = tuple(kwargs.values()) + (user_id,)
        mycursor.execute(sql, val)
        mydb.commit()
        if mycursor.rowcount == 0:
            raise Exception(f"No user found with user_id: {user_id}")

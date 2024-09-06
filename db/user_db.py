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

    def insert_user(self, nickname, name, auth0_user_id, api_key):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor(buffered=True)
            sql = "INSERT INTO users (nickname, name, auth0_user_id, api_key) VALUES (%s, %s, %s, %s)"
            val = (nickname, name, auth0_user_id, api_key)
            mycursor.execute(sql, val)
            mydb.commit()

    def get_user_by_id(self, auth0_user_id):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor(dictionary=True, buffered=True)
            mycursor.execute(
                "SELECT * FROM users WHERE auth0_user_id = %s", (auth0_user_id,))
            return mycursor.fetchone()

    def update_user_settings(self, auth0_user_id, **kwargs):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor()
            set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
            sql = f"UPDATE users SET {set_clause} WHERE auth0_user_id = %s"
            val = tuple(kwargs.values()) + (auth0_user_id,)
            mycursor.execute(sql, val)
            mydb.commit()
            if mycursor.rowcount == 0:
                raise Exception(f"No user found with auth0_user_id: {auth0_user_id}")
            
    # name is the email address and nickname is their name only works with manual signup users
    # social profile signup doesnt pass back an email address
    def get_user_by_email(self, name):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor(dictionary=True, buffered=True)
            mycursor.execute("SELECT * FROM users WHERE name = %s", (name,))
            return mycursor.fetchone()
        
    # getting the user by auth0 ID is probbaly the best way to go about it
    def get_user_by_auth0_id(self,auth0_user_id):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor(dictionary=True, buffered=True)
            mycursor.execute("SELECT * FROM users WHERE auth0_user_id = %s", (auth0_user_id,))
            return mycursor.fetchone()
    
    # Required to update the users api keys from the form
    def update_user_settings(self, auth0_user_id, zapier_api_key):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor()
            sql = """
            UPDATE users 
            SET zapier_api_key = %s
            WHERE auth0_user_id = %s
            """
            val = (zapier_api_key, auth0_user_id)
            mycursor.execute(sql, val)
            mydb.commit()
            if mycursor.rowcount == 0:
                raise Exception(f"No user found with auth0_user_id: {auth0_user_id}")

    # check the users subscription status with the webhook
    def update_user_subscription(self, auth0_user_id, customer_id, subscription_id, status):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor()
            sql = """
            UPDATE users 
            SET stripe_customer_id = %s, stripe_subscription_id = %s, subscription_status = %s
            WHERE auth0_user_id = %s
            """
            val = (customer_id, subscription_id, status, auth0_user_id)
            mycursor.execute(sql, val)
            mydb.commit()
            if mycursor.rowcount == 0:
                print(f"No user found with auth0_user_id: {auth0_user_id}")
                
    # If manual login isnt used social logins don't always produce a email return in name so this fixes that
    def update_user_auth0_id(self,email, auth0_user_id):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor()
            sql = "UPDATE users SET auth0_user_id = %s WHERE name = %s AND auth0_user_id IS NULL"
            val = (auth0_user_id, email)
            mycursor.execute(sql, val)
            mydb.commit()

    # If the user doesnt have a zapier api key and has an account lets give them one
    def update_user_zapier_api_key(self,zapier_api_key, auth0_user_id):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor()
            sql = "UPDATE users SET zapier_api_key = %s WHERE auth0_user_id = %s AND zapier_api_key IS NULL"
            val = (zapier_api_key, auth0_user_id)
            mycursor.execute(sql, val)
            mydb.commit()

    # required for the webhook with stripe
    def get_user_by_stripe_customer_id(self, customer_id):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor(dictionary=True)
            sql = "SELECT * FROM users WHERE stripe_customer_id = %s"
            val = (customer_id,)
            mycursor.execute(sql, val)
            return mycursor.fetchone()
    
    # used for checking if the users api key exist for zapier when a webhook is called
    def check_zapier_api_key(self,zapier_api_key):
        with self.get_db_connection() as mydb:
            mycursor = mydb.cursor()
            sql = "SELECT zapier_api_key FROM users WHERE zapier_api_key = %s"
            val = (zapier_api_key,)  # Ensure this is a tuple
            mycursor.execute(sql, val)
            result = mycursor.fetchone()
            if result:
                api_key = result[0]  # Fetch the first element of the tuple
            else:
                api_key = None
        return api_key
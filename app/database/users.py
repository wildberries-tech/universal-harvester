import sqlite3
import json
import syslog
from typing import Tuple, List, Dict, Optional
import sys
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.database.db_connection import create_db_connection
import bcrypt

def db_get_user(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "SELECT is_active, username, hashed_pass, roles, json FROM users WHERE username LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator
        
        cursor = connection.cursor()
        cursor.execute(query, (data["username"],))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            error_message = f"username {data["username"]} not found"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

def db_get_users(current_state):
    query = "SELECT is_active, username, hashed_pass, roles, json FROM users;"
    
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        cursor = connection.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            error_message = "users not found"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

def fetch_user_data(username: str, current_state: Dict) -> Tuple[bool, str, str, Optional[Dict]]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "SELECT is_active, username, hashed_pass, roles, json FROM users WHERE username = %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (username,))
        user_data = cursor.fetchone()
        if user_data is None:
            error_message = f"user {username} not found"
            connection.close()
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        columns = ["is_active", "username", "hashed_pass", "roles", "json"]
        user_dict = dict(zip(columns, user_data))
        user_dict["roles"] = json.loads(user_dict["roles"]) if user_dict["roles"] else []
        user_dict["json"] = json.loads(user_dict["json"]) if user_dict["json"] else {}
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), user_dict
    
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

def fetch_all_users(current_state: Dict) -> Tuple[bool, str, str, List[Dict]]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        cursor = connection.cursor()
        cursor.execute("SELECT is_active, username, hashed_pass, roles, json FROM users ORDER BY username;")
        users_data = cursor.fetchall()
        columns = ["is_active", "username", "hashed_pass", "roles", "json"]
        users_list = []
        for user_data in users_data:
            user_dict = dict(zip(columns, user_data))
            user_dict["roles"] = json.loads(user_dict["roles"]) if user_dict["roles"] else []
            user_dict["json"] = json.loads(user_dict["json"]) if user_dict["json"] else {}
            users_list.append(user_dict)
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), users_list
    
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

def update_user_field(username: str, field: str, value: any, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"UPDATE users SET {field} = %(inputter)s WHERE username = %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        if field in ["roles", "json"]:
            value = json.dumps(value, ensure_ascii=False)
        cursor.execute(query, (value, username))
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

def create_user(username: str, raw_pass: str, roles: list, json_data: dict, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        hashed_pass = bcrypt.hashpw(raw_pass.encode('utf-8'), bcrypt.gensalt())
        hashed_pass = hashed_pass.decode()

        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "INSERT INTO users (is_active, username, hashed_pass, roles, json) VALUES (%(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s)"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(
            query,
            (True, username, hashed_pass, json.dumps(roles), json.dumps(json_data))
        )
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
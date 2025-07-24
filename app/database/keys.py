import sqlite3
import syslog
import sys
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.database.db_connection import create_db_connection

from typing import Tuple, List, Dict, Optional

def db_get_key(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "SELECT system, account, key, comment FROM keys WHERE system LIKE %(inputter)s AND account LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (data["system"],data["account"],))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            logger_log(syslog.LOG_ERR, get_log_message("key not found", currentFuncName(), current_state))
            return False, "key not found", currentFuncName(), None
    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def db_get_keys(current_state):
    query = "SELECT system, account, key, comment FROM keys;"
    
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
            logger_log(syslog.LOG_ERR, get_log_message("db table is empty?", currentFuncName(), current_state))
            return False, "users not found", currentFuncName(), None
    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

# def db_upsert_key(data, current_state):
#     query_update = "UPDATE keys SET key=?, comment=? WHERE system LIKE ? AND account LIKE ?;"
#     query_insert = "INSERT INTO keys (system, account, key, comment) VALUES (?,?,?,?);"
#     logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
#     try:
#         create_db_connection_result = create_db_connection(current_state)
#         if create_db_connection_result[0] == False:
#             error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
#             logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
#             return False, error_message, currentFuncName(), None

#         connection = create_db_connection_result[3]

#         query = "SELECT system, account, key, comment FROM keys WHERE system LIKE %(inputter)s AND account LIKE %(inputter)s;"
#         db_inputter_modificator = {"inputter": create_db_connection_result[1]}
#         query = query % db_inputter_modificator

#         cursor = connection.cursor()

#         cursor.execute(query_update, (data["key"], data["comment"], data["system"],data["account"]))
#         if cursor.rowcount < 1: # апдейт не сработал
#             cursor.execute(query_insert, (data["system"],data["account"],data["key"],data["comment"]))
        
#         connection.commit()
#         cursor.close()
#         connection.close()
#         logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
#         return True, "OK", currentFuncName(), None

#     except BaseException as e:
#         logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
#         return False, str(e), currentFuncName(), None

def fetch_all_keys(current_state: Dict) -> Tuple[bool, str, str, List[Dict]]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        cursor = connection.cursor()
        cursor.execute("SELECT system, account, key, comment  FROM keys ORDER BY system, account;")
        keys_data = cursor.fetchall()
        columns = ["system", "account", "key", "comment"]
        keys_list = [dict(zip(columns, key_data)) for key_data in keys_data]
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), keys_list
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def create_key(system: str, account: str, key: str, comment: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "INSERT INTO keys (system, account, key, comment) VALUES (%(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s)"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(system, account, key, comment))
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def update_key_field(system: str, account: str, field: str, value: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"UPDATE keys SET {field} = %(inputter)s WHERE system = %(inputter)s AND account =%(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(value, system, account))
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def delete_key(system: str, account: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "DELETE FROM keys WHERE system = %(inputter)s AND account = %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (system, account))
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None


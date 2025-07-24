import sqlite3
import json
import syslog
from typing import Tuple, List, Dict, Optional
import sys
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.database.db_connection import create_db_connection

def db_get_sources(current_state):
    query = "SELECT sourcename, json FROM sources;"
    
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
            return True, "sources not found", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def db_get_source(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "SELECT sourcename, json FROM sources WHERE sourcename LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (data["sourcename"],))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            logger_log(syslog.LOG_ERR, get_log_message("db table is empty?", currentFuncName(), current_state))
            return False, "sources not found", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None


def fetch_all_sources(current_state: Dict) -> Tuple[bool, str, str, List[Dict]]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        cursor = connection.cursor()
        cursor.execute("SELECT sourcename, type, json FROM sources ORDER BY sourcename;")
        sources_data = cursor.fetchall()
        columns = ["sourcename", "type", "json"]
        sources_list = [dict(zip(columns, source_data)) for source_data in sources_data]
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), sources_list
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def create_source(sourcename: str, source_type: str, json_data: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "INSERT INTO sources (sourcename, type, json) VALUES (%(inputter)s, %(inputter)s, %(inputter)s)"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(
            query,
            (sourcename, source_type, json_data)
        )
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def update_source_field(sourcename: str, field: str, value: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"UPDATE sources SET {field} = %(inputter)s WHERE sourcename = %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(
            query,
            (value, sourcename)
        )
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def delete_source(sourcename: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "DELETE FROM sources WHERE sourcename = %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (sourcename,))
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

# Валидация данных
def validate_source_fields(sourcename: str, source_type: str, json_data: str) -> Tuple[bool, str, str, None]:
    if not sourcename or not source_type or not json_data:
        return False, "Sourcename, type, and JSON must not be empty", currentFuncName(), None
    try:
        json.loads(json_data)
        return True, "OK", currentFuncName(), None
    except json.JSONDecodeError:
        return False, "Invalid JSON format", currentFuncName(), None
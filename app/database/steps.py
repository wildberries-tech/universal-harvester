import sqlite3
import syslog
import json
import sys
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from typing import Tuple, List, Dict, Optional
from app.validation import check_json_correct
from app.database.db_connection import create_db_connection

def db_get_steps(current_state):
    query = "SELECT stepname, sourcename, json FROM steps;"
    
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

def db_upsert_step(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        db_inputter_modificator = {"inputter": create_db_connection_result[1]}

        query_update = "UPDATE steps SET json=%(inputter)s WHERE stepname LIKE %(inputter)s AND sourcename LIKE %(inputter)s;"
        query_insert = "INSERT INTO steps (stepname, sourcename, json) VALUES (%(inputter)s,%(inputter)s,%(inputter)s);"
        query_update = query_update % db_inputter_modificator
        query_insert = query_insert % db_inputter_modificator

        cursor = connection.cursor()

        cursor.execute(query_update, (data["json"], data["stepname"], data["sourcename"]))
        if cursor.rowcount < 1: # апдейт не сработал
            cursor.execute(query_insert, (data["stepname"], data["sourcename"],data["json"]))
        
        connection.commit()
        cursor.close()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None

    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

######################
# Вспомогательные функции для работы с БД
def fetch_all_steps(current_state: Dict) -> Tuple[bool, str, str, List[Dict]]:
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        cursor = connection.cursor()
        cursor.execute("SELECT stepname, sourcename, sourcetype, roles, json FROM steps ORDER BY stepname;")
        steps_data = cursor.fetchall()
        columns = ["stepname", "sourcename", "sourcetype", "roles", "json"]
        steps_list = [dict(zip(columns, step_data)) for step_data in steps_data]
        for step in steps_list:
            step["roles"] = json.loads(step["roles"]) if step["roles"] else []
        connection.close()
        return True, "OK", currentFuncName(), steps_list
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None
    
def fetch_step_by_name(step_name: str, current_state: Dict) -> Tuple[bool, str, str, Dict]:
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"SELECT stepname, sourcename, sourcetype, roles, json FROM steps WHERE stepname LIKE %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(step_name,))
        step_data = cursor.fetchone()
        connection.close()
        columns = ["stepname", "sourcename", "sourcetype", "roles", "json"]
        step = dict(zip(columns, step_data))
        
        if check_json_correct(step["roles"]) == False:
            error_message = f"step roles is not a valid json"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
    
        step["roles"] = json.loads(step["roles"]) if step["roles"] else []

        if check_json_correct(step["json"]) == False:
            error_message = f"step json is not a valid json"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
        
        step["json"] = json.loads(step["json"]) if step["json"] else {}
        
        return True, "OK", currentFuncName(), step
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), {}
    
def create_step(stepname: str, sourcename: str, sourcetype: str, roles: List[str], json_data: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]
        #new_stepname.value, new_sourcename.value, new_sourcetype.value, new_roles_list, new_json.value, current_state
        query = "INSERT INTO steps (stepname, sourcename, sourcetype, roles, json) VALUES (%(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s)"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(
            query,
            (stepname, sourcename, sourcetype, json.dumps(roles, ensure_ascii=False), json_data)
        )
        connection.commit()
        connection.close()
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def update_step_field(stepname: str, field: str, value: any, current_state: Dict) -> Tuple[bool, str, str, None]:
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"UPDATE steps SET {field} = %(inputter)s WHERE stepname = %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        if field == "roles":
            value = json.dumps(value, ensure_ascii=False)
        cursor.execute(
            query,
            (value, stepname)
        )
        connection.commit()
        connection.close()
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def delete_step(stepname: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"DELETE FROM steps WHERE stepname = %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (stepname,))
        connection.commit()
        connection.close()
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None


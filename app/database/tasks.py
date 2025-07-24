import sqlite3
import syslog
import sys
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from typing import Tuple, Optional, Dict, List
from app.database.db_connection import create_db_connection

def db_get_task_by_id(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"SELECT id, pid, status_code, status, step_name, source_name, username, timestamp_start, timestamp_stop, in_scenario, json FROM tasks WHERE id LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(data["target_id"],))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            logger_log(syslog.LOG_ERR, get_log_message("db table is empty?", currentFuncName(), current_state))
            return True, "task not found", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def db_upsert_task(data, current_state):
    
    

    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]
        query_update = "UPDATE tasks SET json=%(inputter)s, pid=%(inputter)s, status_code=%(inputter)s, status=%(inputter)s, timestamp_stop=%(inputter)s WHERE id LIKE %(inputter)s;"
        query_insert = "INSERT INTO tasks (id, pid, status_code, status, step_name,source_name, username, timestamp_start, timestamp_stop, in_scenario, json) VALUES (%(inputter)s,%(inputter)s,%(inputter)s,%(inputter)s,%(inputter)s,%(inputter)s,%(inputter)s,%(inputter)s,%(inputter)s,%(inputter)s,%(inputter)s);"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query_update = query_update % db_inputter_modificator
        query_insert = query_insert % db_inputter_modificator

        cursor = connection.cursor()

        cursor.execute(query_update, (data["json"], data["pid"], data["status_code"], data["status"], data["timestamp_stop"], data["id"],))
        if cursor.rowcount < 1: # апдейт не сработал
            cursor.execute(query_insert, (data["id"], data["pid"], data["status_code"],data["status"],data["step_name"],data["source_name"],data["username"],data["timestamp_start"],data["timestamp_stop"],data["in_scenario"],data["json"],))
        
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

def db_get_tasks(data, current_state):
    query = f"SELECT id, pid, status_code, status, step_name, source_name, username, timestamp_start, timestamp_stop, in_scenario, result_rows_count FROM tasks ORDER BY timestamp_start DESC LIMIT {data["limit"]};"
    
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
            return True, "tasks not found", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def db_get_unscenario_tasks(data, current_state):
    query = f"SELECT id, stepname, timestamp_start, timestamp_stop, in_scenario FROM tasks WHERE in_scenario LIKE 'Null' AND username LIKE ? AND stepname LIKE ? AND status_code=5 ORDER BY timestamp_start DESC LIMIT {data["limit"]};"
    
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"SELECT id, stepname, timestamp_start, timestamp_stop, in_scenario FROM tasks WHERE in_scenario LIKE 'Null' AND username LIKE %(inputter)s AND stepname LIKE %(inputter)s AND status_code=5 ORDER BY timestamp_start DESC LIMIT {data["limit"]};"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(current_state["username"], data["stepname"],))
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            logger_log(syslog.LOG_ERR, get_log_message("db table is empty?", currentFuncName(), current_state))
            return True, "tasks not found", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def db_update_task_status(data, current_state):
    query_update = "UPDATE tasks SET status_code=?, status=?, timestamp_stop=?, result_rows_count=? WHERE id LIKE ?;"

    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "UPDATE tasks SET status_code=%(inputter)s, status=%(inputter)s, timestamp_stop=%(inputter)s, result_rows_count=%(inputter)s WHERE id LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()

        cursor.execute(query, (data["status_code"], data["status"], data["timestamp_stop"], data["result_rows_count"], data["id"],))
        updated_rows = cursor.rowcount
        
        
        connection.commit()
        cursor.close()
        connection.close()
        if updated_rows != 1: # апдейт не сработал
            logger_log(syslog.LOG_ERR, get_log_message(f"updated rowcount 0", currentFuncName(), current_state))
            return False, "updated rowcount 0", currentFuncName(), None
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None

    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None
    
def db_get_tasks_by_scenario_id(data, current_state):
    query = f"SELECT id, status_code, step_name, source_name, timestamp_start, timestamp_stop, in_scenario, result_rows_count FROM tasks WHERE in_scenario LIKE ?;"
    
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"SELECT id, status_code, step_name, source_name, timestamp_start, timestamp_stop, in_scenario, result_rows_count FROM tasks WHERE in_scenario LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(data["in_scenario"],))
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            error_message = f"tasks by scenario id {data["in_scenario"]} not found"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return True, error_message, currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None
    
def db_get_active_tasks_by_sourcename(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"SELECT id, status_code, step_name, source_name, timestamp_start, timestamp_stop, in_scenario FROM tasks WHERE status_code = %(inputter)s AND source_name LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(data["status_code"],data["source_name"],))
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            logger_log(syslog.LOG_DEBUG, get_log_message("Active tasks not found", currentFuncName(), current_state))
            return True, "Active tasks not found", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None
    

# Вспомогательные функции для работы с БД
def fetch_tasks(username: str, has_tasks_admin: bool, current_state: Dict) -> Tuple[bool, str, str, List[Dict]]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    limit = 1000
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}

        cursor = connection.cursor()
        if has_tasks_admin:
            limit = min(limit, 5000)  # Ограничение для tasks_admin
            #query = "SELECT id, pid, status_code, status, step_name, source_name, username, timestamp_start, timestamp_stop, in_scenario, json, result_rows_count FROM tasks ORDER BY timestamp_start DESC LIMIT %(inputter)s"
            query = "SELECT id, pid, status_code, status, step_name, source_name, username, timestamp_start, timestamp_stop, in_scenario, json, result_rows_count FROM tasks WHERE username = %(inputter)s ORDER BY timestamp_start DESC LIMIT %(inputter)s"
            query = query % db_inputter_modificator
            cursor.execute(query, (username, limit))
        else:
            query = "SELECT id, pid, status_code, status, step_name, source_name, username, timestamp_start, timestamp_stop, in_scenario, json, result_rows_count FROM tasks WHERE username = %(inputter)s ORDER BY timestamp_start DESC LIMIT %(inputter)s"
            query = query % db_inputter_modificator
            cursor.execute(query, (username, limit))
        tasks_data = cursor.fetchall()
        columns = ["id", "pid", "status_code", "status", "step_name", "source_name", "username", "timestamp_start", "timestamp_stop", "in_scenario", "json", "result_rows_count"]
        tasks_list = [dict(zip(columns, task_data)) for task_data in tasks_data]
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), tasks_list
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def update_task_field(task_id: str, field: str, value: any, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"UPDATE tasks SET {field} = %(inputter)s WHERE id = %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(
            query,
            (value, task_id)
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
    
def fetch_task_by_id(task_id: str, current_state: Dict) -> Tuple[bool, str, str, Optional[Dict]]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"SELECT id, pid, status_code, status, step_name, source_name, username, timestamp_start, timestamp_stop, in_scenario, json, result_rows_count FROM tasks WHERE id = %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (task_id,))
        task_data = cursor.fetchone()
        if task_data is None:
            connection.close()
            error_message = f"Task {task_id} not found"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        columns = ["id", "pid", "status_code", "status", "step_name", "source_name", "username", "timestamp_start", "timestamp_stop", "in_scenario", "json", "result_rows_count"]
        task_dict = dict(zip(columns, task_data))
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), task_dict
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None
    
def db_get_done_tasks_by_stepname(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"SELECT id, status_code, step_name, source_name, timestamp_start, timestamp_stop, in_scenario FROM tasks WHERE status_code = 1 AND step_name LIKE %(inputter)s ORDER BY timestamp_stop DESC LIMIT 1;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(data["step_name"],))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            columns = ["id", "status_code", "step_name", "source_name", "timestamp_start", "timestamp_stop", "in_scenario"]
            task_dict = dict(zip(columns, result))
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), task_dict
        else:
            error_message = "Tasks not found"
            logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), {}
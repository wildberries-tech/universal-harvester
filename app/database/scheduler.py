import sqlite3
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from typing import Tuple, Optional, Dict, List
import json
from app.validation import check_json_correct
from app.database.db_connection import create_db_connection

def db_get_scheduler_jobs(current_state):
    query = "SELECT job_name, author, every_minutes, json FROM scheduler;"
    
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        # query = "DELETE FROM sources WHERE sourcename = %(inputter)s"
        # db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        # query = query % db_inputter_modificator
        
        cursor = connection.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        
        if result:
            columns = ["job_name", "author", "every_minutes", "json"]
            jobs = [dict(zip(columns, data)) for data in result]
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), jobs
        else:
            logger_log(syslog.LOG_DEBUG, get_log_message("db table is empty?", currentFuncName(), current_state))
            return False, "scheduler jobs not found", currentFuncName(), []
    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), []
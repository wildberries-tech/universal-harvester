import syslog
import json
import pandas
import io
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from typing import Tuple, Optional, Dict, List
from app.database.db_connection import create_db_connection

def db_get_static_data_list(current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        # получаем актуальное подключение к внутренней базе harvester (оно может быть sqlite или другое)
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        connection = create_db_connection_result[3]

        # делаем запрос в базу, инпуттер тут не нужен, так как в запрос не передаются параметры
        query = f"SELECT DISTINCT name, MIN(timestamp) as timestamp, owner, comment, COUNT(timestamp) as lines FROM static_data GROUP BY name, owner, comment ORDER BY MIN(timestamp);"

        cursor = connection.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        # собираем лист диктов из ответа БД
        columns = ["name", "timestamp", "owner", "comment", "lines"]
        static_data_list = [dict(zip(columns, step_data)) for step_data in result]

        return True, "OK", currentFuncName(), static_data_list

    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def db_get_static_data_by_name(static_data_name, limit, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = f"SELECT json FROM static_data WHERE name=%(inputter)s LIMIT %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator


        cursor = connection.cursor()
        cursor.execute(query,(static_data_name, limit))
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        # собираем лист диктов из ответа БД
        columns = ["json"]
        static_data_json_list = [dict(zip(columns, step_data)) for step_data in result]
        static_data_payload = []
        for line in static_data_json_list:
            static_data_payload.append(json.loads(line["json"]))

        return True, "OK", currentFuncName(), static_data_payload

    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def db_delete_static_data_by_name(name, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "DELETE FROM static_data WHERE name = %(inputter)s"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (name,))
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message(f"deleted {name}", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def db_upload_static_data(name, comment, content, current_state):
    """Контент приходит просто как тектовая репрезентация csv"""

    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]
        cursor = connection.cursor()

        """Для данной функции требуется дополнительная подготовка данных для загрузки
        name, comment придут в параметрах, уже провалидированы
        owner из current_state, данные из content"""
        content = pandas.read_csv(io.StringIO(content)).to_dict(orient='records')

        # загружаем построчно
        for json_content_line in content:
            string_content_line = json.dumps(json_content_line, indent=0)

            query = f"INSERT INTO static_data (name, timestamp, owner, comment, json) VALUES (%(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s);"
            db_inputter_modificator = {"inputter": create_db_connection_result[1]}
            query = query % db_inputter_modificator

        
            cursor.execute(query,(name, currentTimestamp(), current_state["username"], comment, string_content_line,))
        connection.commit()
        cursor.close()
        connection.close()

        return True, "OK", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

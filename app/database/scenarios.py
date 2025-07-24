import sqlite3
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from typing import Tuple, Optional, Dict, List
import json
from app.validation import check_json_correct, validate_data_for_scenario_update, validate_data_for_scenario_insert, validate_data_for_fetch_scenarios
from app.database.db_connection import create_db_connection

def db_get_scenarios(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        cursor = connection.cursor()
        cursor.execute("SELECT scenario_name, json FROM scenarios;")
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            logger_log(syslog.LOG_ERR, get_log_message("db table is empty?", currentFuncName(), current_state))
            return True, "scenarios not found", currentFuncName(), []
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

# def db_upsert_scenarios(data, current_state):
#     logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
#     try:
#         create_db_connection_result = create_db_connection(current_state)
#         if create_db_connection_result[0] == False:
#             error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
#             logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
#             return False, error_message, currentFuncName(), None

#         connection = create_db_connection_result[3]

#         query = "DELETE FROM sources WHERE sourcename = %(inputter)s"
#         db_inputter_modificator = {"inputter": create_db_connection_result[1]}
#         query_update = "UPDATE scenarios SET roles=%(inputter)s, json=%(inputter)s WHERE scenario_name LIKE %(inputter)s;"
#         query_insert = "INSERT INTO scenarios (scenario_name, author, roles, json) VALUES (?,?);"
#         query = query % db_inputter_modificator
#         query = query % db_inputter_modificator

#         cursor = connection.cursor()

#         cursor.execute(query_update, (data["json"], data["scenario_name"]))
#         if cursor.rowcount < 1: # апдейт не сработал
#             cursor.execute(query_insert, (data["scenario_name"],data["json"]))
        
#         connection.commit()
#         cursor.close()
#         connection.close()
#         logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
#         return True, "OK", currentFuncName(), None

#     except BaseException as e:
#         if 'connection' in locals():
#             connection.close()
#         logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
#         return False, str(e), currentFuncName(), None
    
def db_update_scenario(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "UPDATE scenarios SET scenario_name=%(inputter)s, roles=%(inputter)s, json=%(inputter)s WHERE scenario_name LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator
        
        cursor = connection.cursor()
        # data = {
        #     "scenario_original_name":scenario["scenario_name"],
        #     "scenario_new_name": scenario_name_input.value,
        #     "roles": new_roles,
        #     "json": json_input.value
        # }

        cursor.execute(query,(data["scenario_new_name"], data["roles"], data["json"], data["scenario_original_name"]))

        if cursor.rowcount < 1: # апдейт не сработал
            error_message = "Updated 0 lines?"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
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
    
def db_insert_scenario(data, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "INSERT INTO scenarios (scenario_name, author, roles, json) VALUES (%(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s);"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        # data = {
        #     "scenario_new_name": scenario_name_input.value,
        #     "roles": new_roles,
        #     "json": json_input.value
        # }

        cursor.execute(query,(data["scenario_new_name"], current_state["username"], data["roles"], data["json"]))

        if cursor.rowcount < 1: # апдейт не сработал
            cursor.close()
            connection.close()
            error_message = "Inserted 0 lines?"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
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

# Вспомогательные функции для работы с БД
def fetch_scenarios(has_scenarios_admin: bool, current_state: Dict) -> Tuple[bool, str, str, List[Dict]]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}

        cursor = connection.cursor()
        if has_scenarios_admin:
            query = "SELECT scenario_name, author, roles, json FROM scenarios ORDER BY scenario_name;"
            cursor.execute(query)
        else:
            query = "SELECT scenario_name, author, roles, json FROM scenarios WHERE author = %(inputter)s ORDER BY scenario_name;"
            query = query % db_inputter_modificator
            cursor.execute(query, (current_state["username"], ))
        scenarios_data = cursor.fetchall()
        connection.close()
        columns = ["scenario_name", "author", "roles", "json"]
        scenarios_list = [dict(zip(columns, scenario_data)) for scenario_data in scenarios_data]
        for scenario in scenarios_list:
            validate_data_for_fetch_scenarios_result = validate_data_for_fetch_scenarios(scenario, current_state)
            if validate_data_for_fetch_scenarios_result[0] == False:
                error_message = f"validate_data_for_fetch_scenarios_result is false: {validate_data_for_fetch_scenarios_result[1]}"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            scenario["json"] = json.loads(scenario["json"])
            scenario["roles"] = json.loads(scenario["roles"])

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), scenarios_list
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

def fetch_scenarios_history(has_scenarios_admin: bool, current_state: Dict) -> Tuple[bool, str, str, List[Dict]]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        limit = 1000
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}

        cursor = connection.cursor()
        if has_scenarios_admin:
            
            query = "SELECT scenario_name, username, status_code, status, timestamp_start, timestamp_stop, session_id, json FROM scenarios_history ORDER BY timestamp_start DESC LIMIT %(inputter)s;"
            query = query % db_inputter_modificator
            cursor.execute(query, (limit,))
        else:
            query = "SELECT scenario_name, username, status_code, status, timestamp_start, timestamp_stop, session_id, json FROM scenarios_history WHERE username = %(inputter)s ORDER BY timestamp_start DESC LIMIT %(inputter)s;"
            query = query % db_inputter_modificator
            cursor.execute(query, (current_state["username"], limit))
        history_data = cursor.fetchall()
        columns = ["scenario_name", "username", "status_code", "status", "timestamp_start", "timestamp_stop", "session_id", "json"]
        history_list = [dict(zip(columns, history_data)) for history_data in history_data]

        ##################################
        # проверяем и преобразуем в dict столбец json
        ##################################
        for line in history_list:
            if check_json_correct(line["json"]) == False:
                error_message = f"json in scenario history line {line["session_id"]} is incorrect"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), []
            else:
                line["json"] = json.loads(line["json"])

        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), history_list
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    
def create_scenario_history_line(scenario_name: str, status_code: int, status: str, timestamp_start: str, timestamp_stop: str, session_id: str, json_data: Dict, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "INSERT INTO scenarios_history (scenario_name, username, status_code, status, timestamp_start, timestamp_stop, session_id, json) VALUES (%(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s, %(inputter)s)"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(scenario_name, current_state["username"], status_code, status, timestamp_start, timestamp_stop, session_id, json.dumps(json_data, ensure_ascii=False),)
        )
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"create_scenario_history_line fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None
    
def get_scenario_history_line(session_id: str, current_state: Dict) -> Tuple[bool, str, str, Dict]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "SELECT scenario_name, username, status_code, status, timestamp_start, timestamp_stop, session_id, json FROM scenarios_history WHERE session_id LIKE %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (session_id,)
        )
        scenario_execution_data = cursor.fetchone()
        columns = ["scenario_name", "username", "status_code", "status", "timestamp_start", "timestamp_stop", "session_id", "json"]
        scenario_execution_dict = dict(zip(columns, scenario_execution_data))
        cursor.close()
        connection.close()

        if check_json_correct(scenario_execution_dict["json"]) == False:
            error_message = f"get_scenario_history_line fail: json in {session_id} is not valid"
            return False, error_message, currentFuncName(), {}
        
        scenario_execution_dict["json"] = json.loads(scenario_execution_dict["json"])
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), scenario_execution_dict
    except BaseException as e:
        error_message = f"get_scenario_history_line fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), {}
    
def update_scenario_history_line(status_code: int, status: str, session_id: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "UPDATE scenarios_history SET status_code = %(inputter)s, status = %(inputter)s, timestamp_stop = %(inputter)s WHERE session_id = %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query,(status_code, status, currentTimestamp(), session_id,))
        connection.commit()
        connection.close()
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"get_scenario_history_line fail: {str(e)}"
        if 'connection' in locals():
            connection.close()
        return False, error_message, currentFuncName(), None

def db_get_scenario_by_name(scenario_name, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        query = "SELECT scenario_name, author, roles, json FROM scenarios WHERE scenario_name = %(inputter)s;"
        db_inputter_modificator = {"inputter": create_db_connection_result[1]}
        query = query % db_inputter_modificator

        cursor = connection.cursor()
        cursor.execute(query, (scenario_name,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if not result:
            error_message = f"scenario {scenario_name} not found"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}

        columns = ["scenario_name", "author", "roles", "json"]
        scenario_dict = dict(zip(columns, result))

        if check_json_correct(scenario_dict["json"]) == False:
            error_message = f"db_get_scenario_by_name fail: json in {scenario_name} is not valid"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
        
        scenario_dict["json"] = json.loads(scenario_dict["json"])

        if check_json_correct(scenario_dict["roles"]) == False:
            error_message = f"db_get_scenario_by_name fail: roles in {scenario_name} is not valid"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
        
        scenario_dict["roles"] = json.loads(scenario_dict["roles"])
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), scenario_dict
    except BaseException as e:
        if 'connection' in locals():
            connection.close()
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None
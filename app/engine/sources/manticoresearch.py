import requests
import json
import pandas
import syslog
from app.logging import get_log_message, logger_log, currentFuncName

def execute_manticoresearch_sql(data_map, source, query, step, parameters, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
    try:
        response = requests.post(
            source["url"], 
            data=query["query"], 
            verify = source["verify"], 
            timeout=source["timeout"])
        
        if response.status_code != 200:
            error_message = f"fail: manticoresearch response code is {response.status_code}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        if isinstance(response.json(), list) == False:
            error_message = f"fail: manticoresearch response is not a list"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        if len(response.json()) == 0:
            error_message = f"fail: manticoresearch response list is empty"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        if "data" not in response.json()[0]:
            error_message = f"fail: there is not data node in manticoresearch response list 0"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        output_df = pandas.DataFrame(response.json()[0]["data"])

        output_data = output_df.to_dict('records')#to_json(orient="records")#.to_dict('records')
        logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), output_data

    except BaseException as e:
        error_message = f"manticoresearch sql execution fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
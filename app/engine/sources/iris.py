import datetime
import pandas
import requests
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.engine.sources.additional.flatten import flatten_data

def mod_iris_alert_history(node):
    new_node = {}
    target_timestamp = "0.0"
    target_node = {}
    counter = 0
    for key in node.keys():
        if "modification_history_" not in key:
            new_node[key] = node[key]
        else:
            # если такого ещё нет, то создаём пустой лист
            if "modification_history" not in new_node:
                new_node["modification_history"] = []
            # выделяем текущий timestamp
            current_timestamp = key[21:]
            current_timestamp = current_timestamp[:current_timestamp.find("_")]
            current_field = key[21:]
            current_field = current_field[current_field.find("_")+1:]
            if current_timestamp != target_timestamp:
                # это первое попадание
                if counter == 0:
                    counter = counter + 1
                    target_timestamp = current_timestamp
                    target_node["timestamp"] = target_timestamp
                    target_node[current_field] = node[key]
                else:
                    new_node["modification_history"].append(target_node)
                    target_node = {}
                    ounter = counter + 1
                    target_timestamp = current_timestamp
                    target_node["timestamp"] = target_timestamp
                    target_node[current_field] = node[key]
            else:
                target_node[current_field] = node[key]
    new_node["modification_history"].append(target_node)
    return new_node
    
def execute_function_iris_get_alerts(data_map, source, query, step, parameters, current_state):#, per_page, source_start_date, source_end_date, asset_name): 
    try:
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))

        TOKEN = source["key"]["value"]
        url = source["url"]
        search_field = query["search_field"]
        search_value = parameters["search_value"]

        # if "alert_assets" in parameters:
        #     alert_assets = parameters["alert_assets"]
        # elif "alert_assets" in query:
        #     alert_assets = query["alert_assets"]
        # else:
        #     error_message = f"fail: alert_assets not found in parameters or query"
        #     logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        #     return False, error_message, currentFuncName(), []

        output = []
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {TOKEN}'
        }    
        
        response = requests.get(f"""{url}/alerts/filter?cid=1&page=1&per_page={query["per_page"]}&sort=desc&source_start_date={parameters["start_date"]}&source_end_date={parameters["end_date"]}&{search_field}={search_value}""", headers=headers)
        if response.status_code != 200:
            error_message = f"fail: iris response code is {response.status_code}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        if 'application/json' not in response.headers.get('Content-Type', ''):
            error_message = f"fail: iris response is not application/json"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        if "data" not in response.json():
            error_message = f"fail: there is not data node in iris response"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        if "alerts" not in response.json()["data"]:
            error_message = f"fail: there is not alerts node in data node in iris response"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        if isinstance(response.json()["data"]["alerts"], list) == False:
            error_message = f"fail: alerts data is not a list"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        for alert in response.json()["data"]["alerts"]:
            output.append(flatten_data(mod_iris_alert_history(flatten_data(alert))))
        # print(response.json())
        # print(output)
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), output
    except Exception as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []


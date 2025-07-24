import datetime
import pandas
import requests
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName

def execute_gitlab_namespace_owner_request(data_map, source, query, step, parameters, current_state):
    try:
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))

        namespace = parameters["namespace"]
        token_gitlab = source["key"]["value"]
        gitlab_url = source["url"]
        project_id = parameters["project_id"]

        response = requests.get(
            #https://docs.gitlab.com/api/namespaces/ ???
            f"{gitlab_url}/api/v4/projects/{project_id}/search",
            params={"scope": "blobs", "search": namespace},
            headers={"PRIVATE-TOKEN": token_gitlab}
        )
        
        if response.status_code != 200:
            error_message = f"fail: gitlab response code is {response.status_code}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        output_result = []

        #print(response.json()) #DEBUG!!!
        results = response.json()
        for result in results:
            if "owner" in result['data']:
                for line in result['data'].splitlines():
                    if 'owner' in line:
                        node = {}
                        node["namespace"] = namespace
                        node["owner_file"] = result['filename']
                        node["owner_line"] = line
                        #info['namespaces'][namespace].append((f"File: {result['filename']} Line: {line}"))
                        output_result.append(node)

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), output_result#df_normalized.to_dict('records')
    except Exception as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []

def execute_gitlab_search_request(data_map, source, query, step, parameters, current_state):
    try:
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))

        target = parameters["target"]
        scope = parameters["scope"]
        token_gitlab = source["key"]["value"]
        gitlab_url = source["url"]

        response = requests.get(
            #https://docs.gitlab.com/api/search/
            f"{gitlab_url}/api/search",
            params={"scope": scope, "search": target},
            headers={"PRIVATE-TOKEN": token_gitlab}
        )
        #print(response.status_code)
        #print(response.text)
        if response.status_code != 200:
            error_message = f"fail: gitlab response code is {response.status_code}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        if 'application/json' not in response.headers.get('Content-Type', ''):
            error_message = f"fail: gitlab response is not application/json"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        output_result = []

        #print(response.json()) #DEBUG!!!
        results = response.json()
        if isinstance(results, list):
            output_result = results
        elif isinstance(results, dict):
            output_result = [results]
        else:
            error_message = f"wrong output datatype"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), output_result
    except Exception as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []

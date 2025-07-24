import datetime
import pandas
import requests
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName


def fields_dict_to_youtrack_fields(field: dict, separator: str):
    """Пара рекурсивных функций для конвертации структуры забираемых из ютрека полей в query в то, что нужно включить в API-запрос"""
    output = ""
    for key in field.keys():
        if isinstance(field[key],str):
            if len(output) == 0:
                output = f"{key}({field[key]})"
            else:
                output = f"{output}{separator}{key}({field[key]})"
        if isinstance(field[key],list):
            if len(output) == 0:
                output = f"{key}({fields_list_to_youtrack_fields(field[key], separator)})"
            else:
                output = f"{output}{separator}{key}({fields_list_to_youtrack_fields(field[key], separator)})"
        if isinstance(field[key],dict):
            if len(output) == 0:
                output = f"{key}({fields_dict_to_youtrack_fields(field[key], separator)})"
            else:
                output = f"{output}{separator}{key}({fields_dict_to_youtrack_fields(field[key], separator)})"
    return output

def fields_list_to_youtrack_fields(fields: list, separator: str):
    output = ""
    for field in fields:
        if isinstance(field, str):
            if len(output) == 0:
                output = field
            else:
                output = output + separator + field
        if isinstance(field, list):
            if len(output) == 0:
                output = fields_list_to_youtrack_fields(field, separator)
            else:
                output = f"{output}{separator}{fields_list_to_youtrack_fields(field, separator)}"
        if isinstance(field, dict):
            if len(output) == 0:
                output = fields_dict_to_youtrack_fields(field, separator)
            else:
                output = f"{output}{separator}{fields_dict_to_youtrack_fields(field, separator)}"
    return output

def execute_youtrack_project_finder(data_map, source, query, step, parameters, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        url = source["url"]
        token = source["key"]["value"]
        target = parameters["target"]
        project = parameters["project"]
        fields = query["fields"]
        timeout = source["timeout"]

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }
        response = requests.get(
            f"{url}/api/issues?fields=idReadable&query=project:{project}%20'{target}:'",
            headers=headers, timeout = timeout
        )
        if response.status_code != 200:
            error_message = f"fail: youtrack response code is {response.status_code}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        #print(response.json())###DEBUG
        raw_data = []

        idReadable_list = [project_doc['idReadable'] for project_doc in response.json()]
        for idReadable in idReadable_list:
            try:
                issue_response = requests.get(
                        f'{url}/api/issues/{idReadable}/?fields={fields_list_to_youtrack_fields(fields,",")}',
                        headers=headers, timeout = timeout
                    )
                if issue_response.status_code != 200:
                    continue

                issue_response_json = issue_response.json()
                #print(issue_response.json())###DEBUG
                node = {}

                for issue_response_key in issue_response_json.keys():
                    if issue_response_key == "customFields":
                        for customField in issue_response_json['customFields']:
                            if "value" in customField and "name" in customField:
                                if customField["value"]:
                                    if isinstance(customField["value"], dict):
                                        if "name" in customField["value"]:
                                            node[customField["name"]] = customField["value"]["name"]
                                    else:
                                        node[customField["name"]] = customField["value"]
                            
                            # if customField["name"] not in node:
                            #     node[customField["name"]] = customField["value"]
                            # else:
                            #     node[f"customField_{customField['name']}"] = customField["value"]
                    else:
                        if isinstance(issue_response_json[issue_response_key], dict):
                            for issue_response_node_key in issue_response_json[issue_response_key].keys():
                                if issue_response_node_key == "$type":
                                    pass
                                else:
                                    if isinstance(issue_response_json[issue_response_key][issue_response_node_key], list):
                                        node[f"{issue_response_key}_{issue_response_node_key}"] = "/".join(x["name"] for x in issue_response_json[issue_response_key][issue_response_node_key])
                                    elif isinstance(issue_response_json[issue_response_key][issue_response_node_key], dict):
                                        pass
                                    else:
                                        node[f"{issue_response_key}_{issue_response_node_key}"] = issue_response_json[issue_response_key][issue_response_node_key]
                        elif isinstance(issue_response_json[issue_response_key], list):
                            pass
                        else:
                            node[issue_response_key] = issue_response_json[issue_response_key]
                #print(node)###DEBUG
                raw_data.append(node)

            except BaseException as e:
                error_message = f"idReadable {idReadable} fail: {str(e)}"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                continue
        # теперь раскрываем повзможные вложенности с помощью пандаса
        #print(raw_data)###DEBUG
        #df_normalized = pandas.json_normalize(pandas.DataFrame(raw_data))

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), raw_data#df_normalized.to_dict('records')
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    

def execute_youtrack_all_project_issue_finder(data_map, source, query, step, parameters, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        url = source["url"]
        token = source["key"]["value"]
        target = parameters["target"]
        fields = query["fields"]
        top = parameters["top"]
        #fields_with_content = query["fields_with_content"]
        timeout = source["timeout"]
        #with_content_flag = parameters["with_content_flag"]

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }
        # if with_content_flag == True:
        #     response = requests.get(
        #         #idReadable,project,description,summary,created,reporter,updated,updater,resolved
        #         f"{url}/api/issues?fields={fields_list_to_youtrack_fields(fields_with_content,",")}&flatten=true&query=\"{target}\"",
        #         headers=headers, timeout=timeout
        #     )
        # else:
        #     response = requests.get(
        #         #idReadable,project,description,summary,created,reporter,updated,updater,resolved
        #         f"{url}/api/issues?fields={fields_list_to_youtrack_fields(fields,",")}&flatten=true&query=\"{target}\"",
        #         headers=headers, timeout=timeout
        #     )
        response = requests.get(
                #idReadable,project,description,summary,created,reporter,updated,updater,resolved
                f"{url}/api/issues?fields={fields_list_to_youtrack_fields(fields,",")}&top={top}&flatten=true&query=\"{target}\"",
                headers=headers, timeout=timeout
            )
        if response.status_code != 200:
            error_message = f"fail: youtrack response code is {response.status_code}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        raw_data = response.json()

        if isinstance(raw_data, list):
            for line in raw_data:
                if "idReadable" in line:
                    line["link"] = f"{url}/issue/{line["idReadable"]}/"
                else:
                    line["link"] = f"?"
        elif isinstance(raw_data, dict):
            raw_data = [raw_data]
        else:
            error_message = f"wrong response data type"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []


        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), raw_data#df_normalized.to_dict('records')
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []

def execute_youtrack_all_articles_finder(data_map, source, query, step, parameters, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        url = source["url"]
        token = source["key"]["value"]
        target = parameters["target"]
        fields = query["fields"]
        fields_with_content = query["fields_with_content"]
        with_content_flag = parameters["with_content_flag"]
        timeout = source["timeout"]
        top = parameters["top"]

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
        }

        if with_content_flag == True:
            response = requests.get(
                f"{url}/api/articles?$top={top}&fields={fields_list_to_youtrack_fields(fields_with_content,",")}&query={{\"{target}\"}}",
                headers=headers, timeout=timeout
            )
        else:
            response = requests.get(
                f"{url}/api/articles?$top={top}&fields={fields_list_to_youtrack_fields(fields,",")}&query={{\"{target}\"}}",
                headers=headers, timeout=timeout
            )


        if response.status_code != 200:
            error_message = f"fail: youtrack response code is {response.status_code}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        raw_data = response.json()

        if isinstance(raw_data, list):
            for line in raw_data:
                if "idReadable" in line:
                    line["link"] = f"{url}/articles/{line["idReadable"]}/"
                else:
                    line["link"] = f"?"
        elif isinstance(raw_data, dict):
            raw_data = [raw_data]
        else:
            error_message = f"wrong response data type"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), raw_data#df_normalized.to_dict('records')
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
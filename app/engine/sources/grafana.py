import datetime
import json
import requests
from zoneinfo import ZoneInfo
#import httpx

#import pycurl
#from io import BytesIO, StringIO
from urllib.parse import urlencode

import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName

from app.engine.cache import get_data_from_cache


def grafana_exported_data_to_dataframe(grafana_data, current_state):
    output = []
    if not isinstance(grafana_data, dict):
        logger_log(syslog.LOG_DEBUG, get_log_message("grafana_data is not a dict", currentFuncName(), current_state))
        return output

    if not 'results' in grafana_data:
        logger_log(syslog.LOG_DEBUG, get_log_message("there is not results in grafana_data", currentFuncName(), current_state))
        return output

    if not 'A' in grafana_data['results']:
        logger_log(syslog.LOG_DEBUG, get_log_message("there is not A in grafana_data.results", currentFuncName(), current_state))
        return output

    if not 'frames' in grafana_data['results']['A']:
        logger_log(syslog.LOG_DEBUG, get_log_message("there is not frames in grafana_data.results.A", currentFuncName(), current_state))
        return output

    if not isinstance(grafana_data['results']['A']['frames'], list):
        logger_log(syslog.LOG_DEBUG, get_log_message("frames in grafana_data.results.A is not a list", currentFuncName(), current_state))
        return output
        
    for data_line in grafana_data['results']['A']['frames']:
        if not 'schema' in data_line:
            logger_log(syslog.LOG_DEBUG, get_log_message("there is not schema in data_line of grafana_data.results.A.frames", currentFuncName(), current_state))
            continue
        if not 'fields' in data_line['schema']:
            logger_log(syslog.LOG_DEBUG, get_log_message("there is not fields in data_line.schema of grafana_data.results.A.frames", currentFuncName(), current_state))
            continue
        if not isinstance(data_line['schema']['fields'], list):
            logger_log(syslog.LOG_DEBUG, get_log_message("data_line.schema.fields of grafana_data.results.A.frames is not a list", currentFuncName(), current_state))
            continue
        for grafana_fields in data_line['schema']['fields']:
            if not 'labels' in grafana_fields:
                logger_log(syslog.LOG_DEBUG, get_log_message("there is not labels in grafana_fields of data_line.schema.fields of grafana_data.results.A.frames", currentFuncName(), current_state))
                continue
            if not isinstance(grafana_fields['labels'], dict):
                logger_log(syslog.LOG_DEBUG, get_log_message("labels in grafana_fields of data_line.schema.fields of grafana_data.results.A.frames is not a dict", currentFuncName(), current_state))
                continue
            output.append(grafana_fields['labels'])

    logger_log(syslog.LOG_DEBUG, get_log_message(f"returned {len(output)} lines", currentFuncName(), current_state))       
    return output

def execute_grafana_export_table_requests(data_map, source, query, step, parameters, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        # проверяем, можно ли взять данные из локального кеша
        get_data_from_cache_result = get_data_from_cache(step, query["ttl"], current_state)
        if get_data_from_cache_result[0] == True: #!!!!
            logger_log(syslog.LOG_DEBUG, get_log_message("done from cache", currentFuncName(), current_state))
            return True, "ОК from cache", currentFuncName(), get_data_from_cache_result[3]
        

        TOKEN_GRAFANA = source["key"]["value"]
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {TOKEN_GRAFANA}'
        }
        ds_uid = query["data_source_uid"]
        format = '%Y-%m-%dT%H:%M:%S.%f%z'
        _from = datetime.datetime.strptime(parameters["gte"], format).replace(tzinfo=ZoneInfo(query["server_timezone"])).timestamp() * 1000
        _to = datetime.datetime.strptime(parameters["lte"], format).replace(tzinfo=ZoneInfo(query["server_timezone"])).timestamp() * 1000

        current_data = []
        for ds in ds_uid:
            
            data = {}
            data["queries"] = []
            data["queries"].append(
                {
                    "datasource":{
                        "type":query["datasource_type"],
                        "uid":ds
                    },
                    "editorMode": "code",
                    "exemplar": False,
                    "expr": query["expr"],
                    "format": "table",
                    "hide": False,
                    "instant": True,
                    "interval": "",
                    "legendFormat": "__auto",
                    "range": False,
                    "refId": "A",
                    "requestId": "2A",
                    "utcOffsetSec": 10800,
                    "datasourceId": int(ds_uid[ds]),
                    "intervalMs": 15000,
                    "maxDataPoints": 5000
                }
            )
            data["from"] = str(int(_from))
            data["to"] = str(int(_to))

            data = json.dumps(data)


            url = source["url"]
            if isinstance(url, tuple):
                url = url[0]

            

            response = requests.post(url+query["api_path"], headers=headers, data=data)

            if response.status_code == 200:
                current_data = current_data + grafana_exported_data_to_dataframe(response.json(), current_state)
            else:
                logger_log(syslog.LOG_ERR, get_log_message(f"response.status_code is not 200: {response.status_code}, {response.text}", currentFuncName(), current_state))

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "ОК", currentFuncName(), current_data
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
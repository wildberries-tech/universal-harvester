from opensearchpy import OpenSearch
import pandas
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
import app.engine.sources.additional.elastic2python as elastic2python


# execution_function
def execute_opensearch_query(data_map, source, query, step, parameters, current_state):
    # создаём объект подключения к эластику
    try:
        if source["auth_type"] == "http_auth":
            client = OpenSearch(
                hosts = [{'host': source["host"], 'port': source["port"]}],
                http_compress = source["http_compress"], # enables gzip compression for request bodies
                http_auth = (source["key"]["account"], source["key"]["value"]),
                use_ssl = source["use_ssl"],
                verify_certs = source["verify_certs"],
                ssl_assert_hostname = source["ssl_assert_hostname"],
                ssl_show_warn = source["ssl_show_warn"],
                timeout=source["timeout"], 
                max_retries=source["max_retries"]
            )
        else:
            error_message = f"unknown source auth_type {source['auth_type']}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []        
    except BaseException as e:
        error_message = f"create client fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    
    # проверяем создание объекта подключения
    if client is None:
        error_message = f"create client is None"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []   
    
    # выполняем запрос    
    try: 
        data_taxi_status = elastic2python.data_taxi(
                elastic_client = client, 
                index = query["index"], 
                query = query["query"], 
                sort = query["sort"], 
                fields = query["fields"], 
                size = query["size"], 
                search_after_shift = query["search_after_shift"], 
                debug = False
        )
        if data_taxi_status[0] == False:
            error_message = f"data_taxi_status is false: {data_taxi_status[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        return True, "OK", currentFuncName(), data_taxi_status[3]
    
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    
def execute_opensearch_aggs(data_map, source, query, step, parameters, current_state):
    # создаём объект подключения к эластику
    try:
        if source["auth_type"] == "http_auth":
            client = OpenSearch(
                hosts = [{'host': source["host"], 'port': source["port"]}],
                http_compress = source["http_compress"], # enables gzip compression for request bodies
                http_auth = (source["key"]["account"], source["key"]["value"]),
                use_ssl = source["use_ssl"],
                verify_certs = source["verify_certs"],
                ssl_assert_hostname = source["ssl_assert_hostname"],
                ssl_show_warn = source["ssl_show_warn"],
                timeout=source["timeout"], 
                max_retries=source["max_retries"]
            )
        else:
            error_message = f"unknown source auth_type {source['auth_type']}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []        
    except BaseException as e:
        error_message = f"create client fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    
    # проверяем создание объекта подключения
    if client is None:
        error_message = f"create client is None"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []   
    
    # выполняем запрос
    try:   
        data_taxi_aggs_status = elastic2python.data_taxi_aggs(
            elastic_client = client,
            index = query["index"], 
            query = query["query"],
            size = 0,
            aggs = query["aggs"],
            debug = False
        )
        if data_taxi_aggs_status[0] == False:
            error_message = f"data_taxi_aggs_status is false: {data_taxi_aggs_status[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        return True, "OK", currentFuncName(), data_taxi_aggs_status[3]
    except BaseException as e:
        error_message = f"query fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
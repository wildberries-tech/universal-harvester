import requests
import pandas
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
import app.engine.sources.additional.elastic2python as elastic2python

# execution_function
def execute_elastic_query(data_map, source, query, step, parameters, current_state):
    try:  
        logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
        data_taxi_requests_result = elastic2python.data_taxi_requests(
            query["url"], 
            f'{current_state["app_name"]}/{current_state["app_version"]}',
            source["key"]["value"], 
            source["verify_certs"], 
            source["request_timeout"],
            query["query"], 
            query["sort"], 
            query["fields"], 
            query["size"], 
            query["search_after_shift"], 
            debug = False)
        if data_taxi_requests_result[0] == False:
            error_message = f"data_taxi_requests_result is false: {data_taxi_requests_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), data_taxi_requests_result[3]

    except BaseException as e:
        error_message = f"first query fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []


def execute_elastic_aggs(data_map, source, query, step, parameters, current_state):
    try:   
        logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
        data_taxi_aggs_requests_result = elastic2python.data_taxi_aggs_requests(
            query["url"], 
            f'{current_state["app_name"]}/{current_state["app_version"]}', 
            source["key"]["value"], 
            source["verify_certs"], 
            source["request_timeout"], 
            query["query"], 
            query["aggs"], 
            debug = False, 
            size = 0)
        
        if data_taxi_aggs_requests_result[0] == False:
            error_message = f"data_taxi_aggs_requests_result is false: {data_taxi_aggs_requests_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), data_taxi_aggs_requests_result[3]

    except BaseException as e:
        error_message = f"query fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    
# функция построения цепочки иерархии для выбранного процесса pid
def execute_function_linux_pid_hierarchy_elastic_requests(data_map, source, query, step, parameters, current_state):
    try: 
        logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
        current_data = []
        
        # получаем данные по целевому pid
        try:
            data_taxi_requests_result = elastic2python.data_taxi_requests(
                query["url"], 
                f'{current_state["app_name"]}/{current_state["app_version"]}',
                source["key"]["value"], 
                source["verify_certs"], 
                source["request_timeout"],
                query["query"], 
                query["sort"], 
                query["fields"], 
                query["size"], 
                query["search_after_shift"], 
                debug = False)
            if data_taxi_requests_result[0] == False:
                error_message = f"data_taxi_requests_result is false: {data_taxi_requests_result[1]}"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), []
            
            response_data = data_taxi_requests_result[3]
        
        except BaseException as e:
            error_message = f"target pid query fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []   

        if len(response_data) == 0:
            error_message = f"target pid no data (response_data len is 0)"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []   

        for data in response_data: #бывает так, что в логах в один момент времени есть 2 процесса с одинаковым pid (возможно нужны наносекунды)
            data["hierarchy_position"] = 0
        current_data = current_data + response_data

        # получаем данные по иерархии
        # ищем родителей
        parent_deep = parameters["parent_deep"]
        position = 0
        while parent_deep > 0:
            parent_deep = parent_deep - 1
            if "process.parent.pid" in current_data[-1]:
                position = position - 1
                #parent_deep = parent_deep - 1
                # подготовка фильтров. в пид подставляем родительский пид
                #print(current_data[-1])
                current_elastic_query = query["query"]
                target_parent_pid = current_data[-1]["process.parent.pid"]
                current_elastic_query["bool"]["filter"][2]["match_phrase"] = {}
                current_elastic_query["bool"]["filter"][2]["match_phrase"]["process.pid"] = target_parent_pid
                current_elastic_query["bool"]["filter"][0]["range"][parameters["timestamp_field"]]["gte"] = parameters["gte"] #от левого края предела поиска
                current_elastic_query["bool"]["filter"][0]["range"][parameters["timestamp_field"]]["lte"] = current_data[-1][parameters["timestamp_field"]] # до времени целевого процесса, родитель появился раньше согласно принципцу причинности
                
                try:
                    data_taxi_requests_result = elastic2python.data_taxi_requests(
                        query["url"], 
                        f'{current_state["app_name"]}/{current_state["app_version"]}',
                        source["key"]["value"], 
                        source["verify_certs"], 
                        source["request_timeout"],
                        current_elastic_query, 
                        query["sort"], 
                        query["fields"], 
                        query["size"], 
                        query["search_after_shift"], 
                        debug = False)
                    if data_taxi_requests_result[0] == False:
                        error_message = f"data_taxi_requests_result is false: {data_taxi_requests_result[1]}"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), []
                    
                    response_data = data_taxi_requests_result[3]
                except BaseException as e:
                    error_message = f"parent pid query fail: {str(e)}"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), []
                
                # если мы прошли успешно запрос, то обрабатываем ответ        
                if len(response_data) > 0:
                    # если вдруг найдено много,берём с самым ближайшим временем к целевому процессу
                    # мы можем это сделать, так как у нас есть сортировка
                    
                    response_data[0]["hierarchy_position"] = position
                    current_data.append(response_data[0])

        # ищем детей
        child_deep = parameters["child_deep"]
        position = 0
        # поскольку детей может быть много, запоминать, кого смотреть, будем через списки
        target_child_pid_list = [] # для текущей итерации
        target_child_pid_list_buf = [] # подготовительный для следующей итерации
        target_child_pid_list_done = [] # запоминалка, кого уже посмотрели, на случай дублей
        target_child_pid_list_buf.append({"pid":current_data[0]["process.pid"],"timestamp":current_data[0][parameters["timestamp_field"]]})
        while child_deep > 0:
            position = position + 1 # счётчик позиции для иерархии
            child_deep = child_deep - 1 # счётчик глубины
            target_child_pid_list = target_child_pid_list_buf # принимаем подготовленный список
            target_child_pid_list_buf = [] # очищаем подготавливаемый
            for pid in target_child_pid_list: # обходим все пиды, что нужно проверить, и ищем их детей
                if pid not in target_child_pid_list_done:
                    target_child_pid_list_done.append(pid) # запоминаем, чтобы его больше не смотреть
                    # подготавливаем фильтр
                    current_elastic_query = query["query"]
                    
                    current_elastic_query["bool"]["filter"][2]["match_phrase"] = {}
                    current_elastic_query["bool"]["filter"][2]["match_phrase"]["process.parent.pid"] = pid["pid"]
                    current_elastic_query["bool"]["filter"][0]["range"][parameters["timestamp_field"]]["gte"] = pid["timestamp"] # время от текущего пида
                    current_elastic_query["bool"]["filter"][0]["range"][parameters["timestamp_field"]]["lte"] = parameters["lte"] # до указанного предела в будущее
                    
                    try:
                        data_taxi_requests_result = elastic2python.data_taxi_requests(
                            query["url"], 
                            f'{current_state["app_name"]}/{current_state["app_version"]}',
                            source["key"]["value"], 
                            source["verify_certs"], 
                            source["request_timeout"],
                            current_elastic_query, 
                            query["sort"], 
                            query["fields"], 
                            query["size"], 
                            query["search_after_shift"], 
                            debug = False)
                        if data_taxi_requests_result[0] == False:
                            error_message = f"data_taxi_requests_result is false: {data_taxi_requests_result[1]}"
                            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                            return False, error_message, currentFuncName(), []
                        
                        response_data = data_taxi_requests_result[3]
                    except BaseException as e:
                        error_message = f"child pid query fail: {str(e)}"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), []
            
                    if len(response_data) > 0:
                            # пробегаемся по ответу от эластика
                        for data in response_data:
                            data["hierarchy_position"] = position # проставляем иерархию
                            current_data.append(data) # добавляем данные
                            target_child_pid_list_buf.append({"pid":data["process.pid"],"timestamp":data[parameters["timestamp_field"]]}) # пишем в список на следующую проверку
        
        logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), current_data
    except BaseException as e:
        error_message = f"generic fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    
# функция получения сиблингов для выбранного процесса pid
def execute_function_linux_pid_siblings_elastic_requests(data_map, source, query, step, parameters, current_state):
    try: 
        logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
        current_data = []
        # получаем данные по целевому pid
        try:
            data_taxi_requests_result = elastic2python.data_taxi_requests(
                query["url"], 
                f'{current_state["app_name"]}/{current_state["app_version"]}',
                source["key"]["value"], 
                source["verify_certs"], 
                source["request_timeout"],
                query["query"], 
                query["sort"], 
                query["fields"], 
                query["size"], 
                query["search_after_shift"], 
                debug = False)
            if data_taxi_requests_result[0] == False:
                error_message = f"data_taxi_requests_result is false: {data_taxi_requests_result[1]}"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), []
                        
            response_data = data_taxi_requests_result[3]
        except BaseException as e:
            error_message = f"target pid query fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        if len(response_data) == 0:
            error_message = f"target pid no data (response_data len is 0)"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        current_data = current_data + response_data
        
        # получаем данные по сиблингам
        current_elastic_query = query["query"]
        target_parent_pid = current_data[-1]["process.parent.pid"]
        current_elastic_query["bool"]["filter"][2]["match_phrase"] = {}
        current_elastic_query["bool"]["filter"][2]["match_phrase"]["process.parent.pid"] = target_parent_pid
        current_elastic_query["bool"]["filter"][0]["range"][parameters["timestamp_field"]]["gte"] = parameters["gte"] #от левого края
        current_elastic_query["bool"]["filter"][0]["range"][parameters["timestamp_field"]]["lte"] = parameters["lte"] # до правого края
            
        # делаем запрос
        try:
            data_taxi_requests_result = elastic2python.data_taxi_requests(
                query["url"], 
                f'{current_state["app_name"]}/{current_state["app_version"]}',
                source["key"]["value"], 
                source["verify_certs"], 
                source["request_timeout"],
                current_elastic_query, 
                query["sort"], 
                query["fields"], 
                query["size"], 
                query["search_after_shift"], 
                debug = False)
            if data_taxi_requests_result[0] == False:
                error_message = f"data_taxi_requests_result is false: {data_taxi_requests_result[1]}"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), []
                        
            response_data = data_taxi_requests_result[3]
        except BaseException as e:
            error_message = f"siblings pid query fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        for data in response_data:
            current_data.append(data)

        logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), current_data
    except BaseException as e:
        error_message = f"generic fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
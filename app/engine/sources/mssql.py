import pymssql
import pandas
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
import datetime

def execute_mssql(data_map, source, query, step, parameters, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
    try:
        if source["auth_type"] == "login/pass":
            client = pymssql.connect(
                host=source["host"],
                port = source["port"],
                database=source["database"],
                user=source["key"]["account"],
                password=source["key"]["value"],
                timeout=query["timeout"]
            )
        else:
            error_message = f"unknown source auth_type {source["auth_type"]}"
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
    
    try:
        cursor = client.cursor()
        
        # сначала выполняем подготовительные запросы, если они нужны    
        for sql_query in query["preparatory_queries"]:
            cursor.execute(sql_query)
            client.commit()
        

        # выполняем основной результирующий запрос, ожидается, что это SELECT из получившейся БД
        output_df = pandas.read_sql_query(query["final_query"], client) 
        cursor.close()       
        client.close()

        dict_output = output_df.to_dict('records')

        # Приводим данные к текстовому виду, так как pymssql отдаёт вместо времени объекты
        # + какие-то байтовые штуки, из-за которых всё ломается с экспортом данных в тестах
        for line in dict_output:
            for key in line.keys():
                if isinstance(line[key], datetime.datetime) == True:
                    line[key] = line[key].isoformat()
                if isinstance(line[key], pandas.Timestamp) == True:
                    line[key] = line[key].to_pydatetime().isoformat()
                if isinstance(line[key], bytes) == True:
                    line[key] = line[key].decode(query["encoding"])#.decode('latin-1').encode("utf-8")

        logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), dict_output#output_df.to_json(orient="records", date_format="iso", force_ascii=False)

    except BaseException as e:
        error_message = f"mssql execution fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
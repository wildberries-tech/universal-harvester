import psycopg2
import pandas
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName

def execute_postgresql(data_map, source, query, step, parameters, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
    try:
        if source["auth_type"] == "login/pass":
            client = psycopg2.connect(
                host=source["host"],
                port = source["port"],
                database=source["database"],
                user=source["key"]["account"],
                password=source["key"]["value"],
                connect_timeout=query["timeout"]
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

        output_data = output_df.to_dict('records')#to_json(orient="records")#.to_dict('records')
        logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), output_data

    except BaseException as e:
        error_message = f"postgresql execution fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
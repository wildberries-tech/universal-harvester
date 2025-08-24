import duckdb
import math
import re
import ipaddress
import datetime
import duckdb.typing
import pytz
import pandas
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName



def field_collision_cutter(df):
    column_list = list(df)
    column_list_lower = [x.lower() for x in column_list]
    

    seen = set()
    dupes = []
    
    for i, x in enumerate(column_list_lower):
        if x in seen:
            dupes.append((i,x))
        else:
            seen.add(x)
    
    for i, dupe in enumerate(dupes):
        rename_field = column_list[dupe[0]]
        df = df.rename(columns = {rename_field:f"{rename_field}_{i}"})    
    
    return(df)
    
def convert_size(size_bytes):
    try:
        if size_bytes == "nan":
            return "nan"
        if size_bytes == "":
            return "nan"
        size_bytes = int(float(size_bytes))
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "%s %s" % (s, size_name[i])
    except BaseException as e:
        #syslog.syslog(syslog.LOG_ERR,get_log_message(app_name, version, "Any problem with convert data sum; "+str(e), str(currentFuncName()), json_dumps_indent))
        return "nan"

def validate_ip_address(ip_string):
    try:
        ip_object = ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False

def datetime_to_timestamp(timestamp_string, format):
    try:
        timestamp = datetime.datetime.strptime(timestamp_string, format)
        unixtime = timestamp.timestamp()
        return unixtime
    except BaseException:
        return -1
    
def execute_duckdb(data_map, source, query, step, parameters, current_state):
    # поскольку мы используем inmemory, то клиента к системе проверять не нужно
    try: 
        # представление данных в duckdb (view или table)
        data_representation_type = query["type"]
        if data_representation_type not in ["view", "table"]:
            error_message = f"unknown duckdb data_representation_type: {query['type']}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        # создаём подключение
        conn = duckdb.connect(':memory:')
        conn.execute("PRAGMA threads=8")  # Включение многопоточности
        # добавляем regex функции и можно другие добавить тоже
        conn.create_function(
            'regexp', 
            lambda x, y: 1 if re.search(x,y) else False,
            [duckdb.typing.VARCHAR, duckdb.typing.VARCHAR],
            duckdb.typing.BOOLEAN
        )
        conn.create_function(
            'regexp_substr', 
            lambda x, y: str(re.findall(x,y)) if isinstance(x,str) and isinstance(y,str) else 'regexp_error',
            [duckdb.typing.VARCHAR, duckdb.typing.VARCHAR],
            duckdb.typing.VARCHAR
        )
        conn.create_function(
            'ip_is_private', 
            lambda x: int(ipaddress.ip_address(str(x)).is_private) if validate_ip_address(str(x)) else False,
            [duckdb.typing.VARCHAR],
            duckdb.typing.BOOLEAN
        )
        conn.create_function(
            'unixtime_to_iso_timestamp', 
            lambda x: str(datetime.datetime.fromtimestamp(float(x), pytz.timezone('UTC')).isoformat(sep='T', timespec='milliseconds')) if str(x).replace(".", "", 1).isdigit() else str(x),
            [duckdb.typing.VARCHAR],
            duckdb.typing.VARCHAR
        )
        conn.create_function(
            'bytes_to_string', 
            lambda x: str(convert_size(x)),
            [duckdb.typing.INTEGER],
            duckdb.typing.VARCHAR
        )
        conn.create_function(
            'ip_port2ip', 
            lambda x: x[:x.find(":")] if isinstance(x,str) else 'ip_port2ip_error',
            [duckdb.typing.VARCHAR],
            duckdb.typing.VARCHAR
        )
        conn.create_function(
            'validate_ip_address', 
            lambda x: validate_ip_address(str(x)),
            [duckdb.typing.VARCHAR],
            duckdb.typing.BOOLEAN
        )
        conn.create_function(
            'datetime_to_timestamp', 
            lambda x, y: datetime_to_timestamp(x, y),
            [duckdb.typing.VARCHAR, duckdb.typing.VARCHAR],
            duckdb.typing.DOUBLE
        )

        try:
            # теперь заполняем нашу БД таблицами из data_map
            df_list = []
            for table in data_map.keys():
                #проверка на пустоту
                if len(data_map[table]["data"]) != 0:

                    input_df = field_collision_cutter(pandas.DataFrame(data_map[table]["data"]))

                    # нормализация данных   
                    stringcols = input_df.select_dtypes(include='object').columns
                    input_df[stringcols] = input_df[stringcols].fillna('').astype(str)

                    if data_representation_type == "view": # это используем, когда данные точно есть (невозможен ALTER VIEW +column)
                        df_list.append(input_df)
                        conn.register(table, df_list[-1])
                    if data_representation_type == "table": # обычные таблицы, чуть медленнее, но больше возможностей
                        conn.sql(f"CREATE TABLE {table} AS SELECT * FROM input_df")

                else:
                    #input_df = pandas.DataFrame([{"status":"empty"}])
                    pass
        except BaseException as e:
            error_message = f"duckdb data transfer to virtual db fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
                
            
        # сначала выполняем подготовительные запросы, если они нужны
        try:
            for i, sql_query in enumerate(query["preparatory_queries"]):
                conn.sql(sql_query)
        except BaseException as e:
            error_message = f"preparatory query {i} fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        # выполняем основной результирующий запрос, ожидается, что это SELECT из получившейся БД
        output_df = conn.sql(query["final_query"]).df()            

        return True, "OK", currentFuncName(), output_df.to_dict('records')

    except BaseException as e:
        error_message = f"duckdb fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []

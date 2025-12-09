import sqlite3
import math
import re
import ipaddress
import datetime
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
    
def execute_sqlite3(data_map, source, query, step, parameters, current_state):
    # поскольку мы используем inmemory, то клиента к системе проверять не нужно
    try: 
        # создаем экземпляр БД
        db = sqlite3.connect(':memory:')

        # Optimize SQLite settings for performance
        cursor = db.cursor()
        #without row id?
        cursor.execute('PRAGMA synchronous = OFF;')
        cursor.execute('PRAGMA journal_mode = OFF;')
        cursor.execute('PRAGMA page_size = 65535;')
        # добавляем regex функции и можно другие добавить тоже
        db.create_function('regexp', 2, lambda x, y: 1 if re.search(x,y) else 0)
        db.create_function('regexp_substr', 2, lambda x, y: str(re.findall(x,y)) if isinstance(x,str) and isinstance(y,str) else 'regexp_error') #ipaddress.ip_address('192.168.0.1').is_private
        db.create_function('ip_is_private', 1, lambda x: int(ipaddress.ip_address(str(x)).is_private) if validate_ip_address(str(x)) else 0)
        db.create_function('unixtime_to_iso_timestamp', 1, lambda x: str(datetime.datetime.fromtimestamp(float(x), pytz.timezone('UTC')).isoformat(sep='T', timespec='milliseconds')) if str(x).replace(".", "", 1).isdigit() else str(x))
        db.create_function('bytes_to_string', 1, lambda x: str(convert_size(x)))
        db.create_function('ip_port2ip', 1, lambda x: x[:x.find(":")] if isinstance(x,str) else 'ip_port2ip_error')
        db.create_function('validate_ip_address', 1, lambda x: validate_ip_address(str(x)))
        db.create_function('datetime_to_timestamp', 2, lambda x, y: datetime_to_timestamp(x, y))

        try:
            # теперь заполняем нашу БД таблицами из data_map
            for table in data_map.keys():
                #проверка на пустоту
                if len(data_map[table]["data"]) != 0:
                    #print(list(pandas.DataFrame(result_buf[table])))
                    input_df = field_collision_cutter(pandas.DataFrame(data_map[table]["data"]))
                    #print(list(input_df))
                    column_list  = list(input_df)
                    # нормализация данных, чтобы то, что в пандасе, влезло в sqlite3    
                    stringcols = input_df.select_dtypes(include='object').columns
                    input_df[stringcols] = input_df[stringcols].fillna('').astype(str)
                    input_df.to_sql(table, db, if_exists="replace", chunksize=100, index=False, method="multi")
                else:
                    #input_df = pandas.DataFrame([{"status":"empty"}])
                    pass
        except BaseException as e:
            error_message = f"sqlite3 data transfer to virtual db fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
                
            
            
        # создаем курсор для манипуляции с данными
        db_cursor = db.cursor()

        # сначала выполняем подготовительные запросы, если они нужны
        try:
            for i, sql_query in enumerate(query["preparatory_queries"]):
                db_cursor.execute(sql_query)
                db.commit()
        except BaseException as e:
            error_message = f"preparatory query {i} fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        # выполняем основной результирующий запрос, ожидается, что это SELECT из получившейся БД
        output_df = pandas.read_sql_query(query["final_query"], db)            
        db.close()
        return True, "OK", currentFuncName(), output_df.to_dict('records')

    except BaseException as e:
        error_message = f"sqlite3 fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []

import sqlite3
import psycopg2
import json
import base64
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from typing import Tuple, Optional, Dict, List

from app.crptgrphy import decrypt

def create_db_connection(current_state: Dict):
    try:
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))

        #################################
        # раскрываем конфигурацию
        #################################
        # в current_state должен быть db_conf

        if "db_conf" not in current_state:
            error_message = f"db_conf not in current_state"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if isinstance(current_state["db_conf"], str) == False:
            error_message = f"db_conf in current_state is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        decrypt_result = decrypt(current_state["db_conf"], current_state)
        if decrypt_result[0] == False:
            error_message = f"db_conf decrypting is false"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        db_conf = json.loads(base64.b64decode(decrypt_result[3].encode()).decode())

        if "type" not in db_conf:
            error_message = f"type not in db_conf"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if db_conf["type"] == "sqlite3":
            if "sqlite3" not in db_conf:
                error_message = f"sqlite3 not in db_conf"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            if isinstance(db_conf["sqlite3"], dict) == False:
                error_message = f"db_conf.sqlite3 is not a dict"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            if "db_path" not in db_conf["sqlite3"]:
                error_message = f"db_path not in db_conf.sqlite3"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None

            connection = sqlite3.connect(db_conf["sqlite3"]["db_path"])
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            query_parameter_inputter = "?"
            return True, query_parameter_inputter, currentFuncName(), connection
        
        elif db_conf["type"] == "postgresql":
            if "postgresql" not in db_conf:
                error_message = f"postgresql not in db_conf"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            if isinstance(db_conf["postgresql"], dict) == False:
                error_message = f"db_conf.postgresql is not a dict"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            if "host" not in db_conf["postgresql"]:
                error_message = f"host not in db_conf.postgresql"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            if "port" not in db_conf["postgresql"]:
                error_message = f"port not in db_conf.postgresql"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            if "db_name" not in db_conf["postgresql"]:
                error_message = f"dbname not in db_conf.postgresql"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            if "login" not in db_conf["postgresql"]:
                error_message = f"login not in db_conf.postgresql"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            
            if "password" not in db_conf["postgresql"]:
                error_message = f"password not in db_conf.postgresql"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            connection = psycopg2.connect(
                host = db_conf["postgresql"]["host"], 
                port = db_conf["postgresql"]["port"],
                dbname = db_conf["postgresql"]["db_name"],
                user = db_conf["postgresql"]["login"],
                password = db_conf["postgresql"]["password"]
            )
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            query_parameter_inputter = "%s"
            return True, query_parameter_inputter, currentFuncName(), connection
        else:
            error_message = f"unsupported db type {db_conf['type']}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
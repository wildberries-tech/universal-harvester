import syslog
from app.logging import get_log_message, logger_log, currentFuncName
from app.database.db_connection import create_db_connection

def db_get_access_networks(current_state):
    query = "SELECT ip_network, allow, comment FROM access_networks;"
    
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        cursor = connection.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        if result:
            logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), result
        else:
            logger_log(syslog.LOG_ERR, get_log_message("access networks not found", currentFuncName(), current_state))
            return False, "access networks not found", currentFuncName(), None
    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None
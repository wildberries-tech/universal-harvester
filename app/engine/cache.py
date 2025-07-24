import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.database.tasks import db_get_done_tasks_by_stepname
from app.engine.storage import read_step_from_storage
import datetime

def get_data_from_cache(step: dict, ttl:int, current_state: dict):
    """Некоторые функции исполнения могут обращаться к уже выполненным таскам для сбора данных, если они были получены не позже ttl в секундах.
    Это актуально для тех шагов, которые не имеют механизмов фильтрации и забирают от источника большой слой данных.
      Чтобы не перегружать источник и сеть, данных могут быть получены из storage от успешно выполненной таске в прошлом в пределах ttl."""
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        ###################################
        # делаем запрос в БД, получаем список выполненных тасок по данному шагу
        ###################################
        db_get_done_tasks_by_stepname_result = db_get_done_tasks_by_stepname({"step_name":step["step_name"]}, current_state)
        if db_get_done_tasks_by_stepname_result[0] == False:
            error_message = f"db_get_done_tasks_by_stepname_result is False: {db_get_done_tasks_by_stepname_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        task_dict = db_get_done_tasks_by_stepname_result[3]
        ###################################
        # проверяем актуальность данных по ttl
        ###################################

        timestamp_now = datetime.datetime.fromisoformat(currentTimestamp())
        timestamp_data = datetime.datetime.fromisoformat(task_dict["timestamp_start"])
        if (timestamp_now-timestamp_data).total_seconds() <= ttl:
            # читаем из storage
            read_step_from_storage_result = read_step_from_storage({"target_id":task_dict["id"]}, current_state)
            if read_step_from_storage_result[0] == False:
                error_message = f"read_step_from_storage_result is False: {read_step_from_storage_result[1]}"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), []
            import_data = read_step_from_storage_result[3]

            if "data" not in import_data:
                error_message = f"data not in import_data"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), []
            
            if isinstance(import_data["data"], list) == False:
                error_message = f"import_data data is not a list"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), []
            
            return True, "OK", currentFuncName(), import_data["data"]

        else:
            error_message = f"data is irrelevant"
            logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
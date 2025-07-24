import argparse
import json
import time
import schedule
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName

from app.engine.shared_memory import get_data_from_shared_memory
from app.engine.scenarios import run_scenario, waiting_for_scenario_execution
from app.database.scheduler import db_get_scheduler_jobs
from app.validation import scheduler_jobs_validator
from app.database.scenarios import db_get_scenario_by_name

from app.scheduler.actions import action_syslog
from app.database.tasks import db_get_tasks_by_scenario_id

current_state = {
    "app_name":"Universal_Harvester_scheduler",
    "app_version":"0.0.1",
    "main_session_id":"00000000-0000-0000-0000-000000000000",
    "user_session_id":"00000000-0000-0000-0000-000000000000",
    "client_ip_address":"127.0.0.1",
    "client_port":0,
    "username":"system"
}

def scheduler_launch(job, scenario_name, parameters, current_state):
    DEBUG = False
    
    if DEBUG: print("user_roles", user_roles)
    ##############################################
    # получаем сценарий из бд по имени
    ##############################################
    db_get_scenario_by_name_result = db_get_scenario_by_name(scenario_name, current_state)
    if db_get_scenario_by_name_result[0] == False:
        error_message = f"get scenario by name error: {db_get_scenario_by_name_result[1]}"
        logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
        return
    
    scenario_dict = db_get_scenario_by_name_result[3]
    if DEBUG: print("scenario_dict", scenario_dict)
    #######################################
    # получаем разрешенные роли для сценария дл проверки прав доступа
    #######################################
    # планировщик заданий работает с полными правами на исполнения сценариев
    user_roles = ["fullmaster"]
    allow_flag = False
    
    if "fullmaster" in user_roles:
        allow_flag = True
    for user_role in user_roles:
        if user_role in scenario_dict["roles"]:
            allow_flag = True
            break
    
    if allow_flag == False:
        error_message = f"you do not have permission to execute this scenario"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return
    ##############################################
    # процедура запуска сценария
    ##############################################
    run_scenario_result = run_scenario(user_roles, scenario_name, json.dumps(scenario_dict["json"]), parameters, "", current_state)
    if run_scenario_result[0] == False:
        error_message = f"scenario launch error: {run_scenario_result[1]}"
        logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
        return
    
    scenario_session_id = run_scenario_result[3]

    if DEBUG: print("scenario_dict", scenario_session_id)
    ##############################################
    # ожидание выполнения
    ##############################################
    waiting_for_scenario_execution_result = waiting_for_scenario_execution(10000, scenario_session_id, current_state)
    if waiting_for_scenario_execution_result[0] == False:
        error_message = f"scenario execution error: {waiting_for_scenario_execution_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return
    
    scenario_execution_dict = waiting_for_scenario_execution_result[3]
    if DEBUG: print("scenario_execution_dict", scenario_execution_dict)

    #scenario history ["scenario_name", "username", "status_code", "status", "timestamp_start", "timestamp_stop", "session_id", "json"]
    ##############################################
    # проверяем наличие результата (есть ли то, о чём надо уведомлять?) количество строк данных шагов с show=True >0
    ##############################################
    db_get_tasks_by_scenario_id_result = db_get_tasks_by_scenario_id({"in_scenario":scenario_execution_dict["session_id"]}, current_state)
    if db_get_tasks_by_scenario_id_result[0] == False:
        error_message = f"db_get_tasks_by_scenario_id_result is false: {db_get_tasks_by_scenario_id_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return
    #id, status_code, step_name, source_name, timestamp_start, timestamp_stop, in_scenario, result_rows_count
    scenario_tasks_results_count = {}
    for data_line in db_get_tasks_by_scenario_id_result[3]:
        task_id = data_line[0]
        result_rows_count = data_line[7]
        scenario_tasks_results_count[task_id] = result_rows_count

    found_flag = False
    for step in scenario_execution_dict["json"]["scenario"]["steps"]:
        if step["show"] == True:
            if scenario_tasks_results_count[step["current_task_id"]] > 0:
                found_flag = True
                break
    
    if found_flag == False:
        # + scheduler_history
        message = f"Job {job["job_name"]} {currentTimestamp()} done, data is not found"
        logger_log(syslog.LOG_NOTICE, get_log_message(message, currentFuncName(), current_state))
        return
    ##############################################
    # выполнение actions (сначала надо понять, есть ли результат. Если есть, то выполнить действие)
    ##############################################


"""Планировщик заданий работает в вечном цикле, обновляет список заданий, выполняет задания, загруженные из БД"""
def main():
    #####################################
    # инициализация планировщика заданий
    #####################################
    global args
    parser = argparse.ArgumentParser(description="Движок UH2")
    parser.add_argument(
        "--shared_memory_name",
        type=str,
        default="psm_b0046289", #t.me/extended_netflow_bot
        help="Имя объекта shared memory для получения мастер-ключа и других параметров"
    )

    global current_state
    args = parser.parse_args() # []

    ###############################################
    # логируем запуск и параметры запуска
    ###############################################

    logger_log(syslog.LOG_DEBUG, get_log_message(f"scheduler start, shared memory object: {args.shared_memory_name}", currentFuncName(),current_state))

    ###############################################
    # получаем параметры работы от фронта
    ###############################################
    engine_get_data_from_shared_memory_result = get_data_from_shared_memory(args.shared_memory_name, current_state)
    if engine_get_data_from_shared_memory_result[0] == False:
        logger_log(syslog.LOG_CRIT, get_log_message(f"engine_get_data_from_shared_memory_status is False: {engine_get_data_from_shared_memory_result[1]}", currentFuncName(),current_state))
        return
    current_state = engine_get_data_from_shared_memory_result[3]

    # цикл работы
    WORK_FLAG = True

    """Должно быть несколько таймеров
    Таймер обновления заданий. Раз в 120 секунд?
    Хотя основной таймер будет раз в 5 секунд"""
    job_update_timer = 24
    while(WORK_FLAG):
        job_update_timer = job_update_timer + 1

        if job_update_timer >= 24:
            logger_log(syslog.LOG_DEBUG, get_log_message(f"job_update_timer: {job_update_timer}, update from db", currentFuncName(),current_state))
            job_update_timer = 0
            ###############################################
            # Получаем job из БД, старые удаляем
            ###############################################
            db_get_scheduler_jobs_result = db_get_scheduler_jobs(current_state)
            if db_get_scheduler_jobs_result[0] == False:
                logger_log(syslog.LOG_ERR, get_log_message(f"db_get_scheduler_jobs error: {db_get_scheduler_jobs_result[1]}, update from db", currentFuncName(),current_state))
                jobs = []
            else:
                jobs = db_get_scheduler_jobs_result[3]

            ###############################################
            # валидируем джобы
            ###############################################
            scheduler_jobs_validator_result = scheduler_jobs_validator(jobs, current_state)
            if scheduler_jobs_validator_result[0] == False:
                logger_log(syslog.LOG_ERR, get_log_message(f"scheduler_jobs_validator error: {db_get_scheduler_jobs_result[1]}, update from db", currentFuncName(),current_state))
                jobs = []
            else:
                jobs = scheduler_jobs_validator_result[3]

        for job in jobs:
            if "valid" in job:
                if job["valid"] == True:
                    schedule.every(job["every_minutes"]).minutes.do(scheduler_launch(scenario_name, parameters, current_state))

        time.sleep(3)


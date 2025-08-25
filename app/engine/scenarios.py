from datetime import datetime, timezone
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
import json
from typing import Tuple, Optional, Dict, List
import uuid
import time
from app.validation import *
from app.validation import scenario_validator, check_json_correct
from app.database.steps import fetch_all_steps
from app.engine.steps import get_parameters_from_step
from app.database.steps import fetch_step_by_name
from app.engine.engine import engine_hasshin
from app.database.scenarios import create_scenario_history_line, get_scenario_history_line, update_scenario_history_line, db_get_scenario_by_name
from app.database.tasks import db_get_tasks, fetch_tasks, update_task_field, fetch_task_by_id
from app.engine.storage import read_step_from_storage
import asyncio

def get_parameters_from_scenario(scenario_text: str, current_state: dict) -> Tuple[bool, str, str, dict]:
    #####################################
    # проверка на json
    #####################################
    if isinstance(scenario_text, str):
        if check_json_correct(scenario_text) == False:
            error_message = f"scenario_text is not a valid json"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
        
        scenario = json.loads(scenario_text)
    elif isinstance(scenario_text, dict):
        scenario = scenario_text
    else:
        error_message = f"invalid scenario_text datatype"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {}
    #####################################
    # надо провалидировать наш сценарий на всякий случай
    #####################################
    scenario_validator_result = scenario_validator(False, scenario, current_state)
    if scenario_validator_result[0] == False:
        error_message = f"scenario_validator_result is False: {scenario_validator_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {}
    
    #####################################
    # Теперь надо забрать все шаги сценария из БД по имени
    #####################################
    fetch_all_steps_result = fetch_all_steps(current_state)
    if fetch_all_steps_result[0] == False:
        error_message = f"fetch_all_steps_result is False: {fetch_all_steps_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {}
    
    found_steps = []
    all_steps_list = fetch_all_steps_result[3]
    for scenario_step in scenario["steps"]:
        step_found = False
        for db_step in all_steps_list:
            if scenario_step["step_name"] == db_step["stepname"]:
                found_steps.append({"step_name":db_step["stepname"],"step_json":db_step["json"]})
                step_found = True
                break
        if step_found == False:
            error_message = f"scenario step {scenario_step['step_name']} is not found in db"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
        
    #####################################
    # Теперь забираем параметры из каждого шага
    #####################################
    steps_parameters = {}

    for i, step in enumerate(found_steps):
        get_parameters_from_step_result = get_parameters_from_step("simple", step["step_name"], step["step_json"], scenario, i, current_state)
        if get_parameters_from_step_result[0] == False:
            error_message = f"get_parameters_from_step_result is False for step {step['step_name']}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
        steps_parameters[i] = get_parameters_from_step_result[3]
    
    #####################################
    # Теперь забираем параметры из каждого шага и совмещаем с conjoined
    #####################################
    # тут может быть 2 варианта: если есть conjoined, и если его нет (он опционален)
    scenario_parameters = {}

    if "conjoined_parameters" in scenario:
        conjoined_parameters = scenario["conjoined_parameters"]
    else:
        conjoined_parameters = {}
    for step_index in steps_parameters:
        for parameter in steps_parameters[step_index].keys():
            # структура conjoined такова "conjoined_parameters":{"search_value":["1:search_value"]}
            conjoined_candidate_name = f"{step_index}:{parameter}" # этого кандидата будем искать в листе

            conjoined_found = False
            for conjoined_parameter in conjoined_parameters.keys():
                if conjoined_candidate_name in conjoined_parameters[conjoined_parameter]:
                    scenario_parameter_name = conjoined_parameter
                    conjoined_found = True
            
            if conjoined_found == False:
                scenario_parameter_name = conjoined_candidate_name
            scenario_parameters[scenario_parameter_name] = steps_parameters[step_index][parameter]
    

    return True, "OK", currentFuncName(), scenario_parameters

def run_scenario(user_roles: List, scenario_name: str, scenario_json, scenario_parameters, need_scenario_notify: bool, id_prefix: str, current_state: Dict) -> Tuple[bool, str, str, str]:
    #####################################
    # проверка на json
    #####################################
    if isinstance(scenario_json, str):
        if check_json_correct(scenario_json) == False:
            error_message = f"scenario_text is not a valid json"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), "None"
        
        scenario = json.loads(scenario_json)
    elif isinstance(scenario_json, dict):
        scenario = scenario_json
    else:
        error_message = f"Wrong datatype of scenario_text"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), "None"

    if isinstance(scenario_parameters, str):
        if check_json_correct(scenario_parameters) == False:
            error_message = f"scenario_parameters is not a valid json"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), "None"
        
        parameters = json.loads(scenario_parameters)
    elif isinstance(scenario_parameters, dict):
        parameters = scenario_parameters
    else:
        error_message = f"Wrong datatype of scenario_parameters"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), "None"

    #####################################
    # валидируем сценарий
    #####################################
    scenario_validator_result = scenario_validator(False, scenario, current_state)
    if scenario_validator_result[0] == False:
        error_message = f"scenario_validator_result is False: {scenario_validator_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), "None"
    
    #####################################
    # теперь надо собрать данные по шагам из бд
    #####################################
    steps_from_db = {}
    # steps_data_roles_list = []
    # steps_data_json_list = []
    for i, step in enumerate(scenario["steps"]):
        fetch_step_by_name_result = fetch_step_by_name(step["step_name"], current_state)
        if fetch_step_by_name_result[0] == False:
            error_message = f"fetch_step_by_name_result for step {i}:{step['step_name']} is False: {fetch_step_by_name_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), "None"
        # steps_data_roles_list.append(fetch_step_by_name_result[3]["roles"])
        # steps_data_json_list.append(fetch_step_by_name_result[3]["json"])
        steps_from_db[step["step_name"]] = {}
        steps_from_db[step["step_name"]]["roles"] = fetch_step_by_name_result[3]["roles"]
        steps_from_db[step["step_name"]]["json"] = fetch_step_by_name_result[3]["json"]
        steps_from_db[step["step_name"]]["sourcename"] = fetch_step_by_name_result[3]["sourcename"]
        steps_from_db[step["step_name"]]["stepname"] = fetch_step_by_name_result[3]["stepname"]
    #####################################
    # проверяем права/разрешения на запуск сценария
    #####################################
    # получаем сценарий из БД:
    #scenario_name
    db_get_scenario_by_name_result = db_get_scenario_by_name(scenario_name, current_state)
    if db_get_scenario_by_name_result[0] == False:
        error_message = f"db_get_scenario_by_name_result is fasle: {db_get_scenario_by_name_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), "None"
    scenario_roles = db_get_scenario_by_name_result[3]["roles"]

    access = False
    if "fullmaster" in user_roles:
        access = True
    else:
        for scenario_role in scenario_roles:
            if scenario_role in user_roles:
                access = True
                break
    if access == False:
        error_message = f"access deny"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), "None"
        #for i, step_roles in steps_data_roles_list:
        # for step_name in steps_from_db.keys():
        #     step_roles = steps_from_db[step_name]["roles"]
        #     access = False
        #     for user_role in user_roles:
        #         if user_role in step_roles:
        #             access = True
        #             break
        #     if access == False:
        #         error_message = f"there is not access for step {step_name}"
        #         logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        #         return False, error_message, currentFuncName(), "None"
            
    #####################################
    # на всякий случай валидируем шаги
    #####################################
    for step_name in steps_from_db.keys():
        step_json = steps_from_db[step_name]["json"]
        step_validator_result = step_validator(step_json, current_state)
        if step_validator_result[0] == False:
            error_message = f"step_validator_result for step {step_name} is False: {step_validator_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), "None"
        
    #####################################
    # назначаем UUID таскам в рамках сценария (надо для областей видимости)
    #####################################
    for step in scenario["steps"]:
        step["current_task_id"] = str(uuid.uuid4())
    # дополнительно создаём идентификатор запуска сценария
    if id_prefix == "":# id prefix нужен для запуска сценариев в рамках шага, чтобы можно было поиском отделить их
        scenario_launch_id = f"{scenario_name}:{str(uuid.uuid4())}"
    else:
        scenario_launch_id = f"{id_prefix}:{scenario_name}:{str(uuid.uuid4())}"

    #####################################
    # пишем в историю запуска намерение запустить сценарий
    #####################################
    create_scenario_history_line_result = create_scenario_history_line(
        scenario_name, 0, "Сценарий подготовлен к запуску", currentTimestamp(), "-", scenario_launch_id, {"scenario":scenario, "parameters":parameters}, current_state)
    if create_scenario_history_line_result[0] == False:
        error_message = f"create_scenario_history_line_result for scenario {scenario_launch_id} is False: {create_scenario_history_line_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), scenario_launch_id
    
    #####################################
    # теперь надо последовательно пройтись по шагам и каждый запустить отдельно
    #####################################
    tasks_starting_status = []
    for i, step in enumerate(scenario["steps"]):
        db_step = steps_from_db[step["step_name"]]
        #print(db_step)
        data = {
            "id":step["current_task_id"],
            "pid":-1,
            "status_code":0,
            "status":"New",
            "step_name":db_step["stepname"],
            "source_name":db_step["sourcename"],
            "username":current_state["username"],
            "timestamp_start": currentTimestamp(),
            "timestamp_stop": "-",
            "in_scenario": scenario_launch_id,
            "json":json.dumps({
                "step":db_step["json"],
                "parameters":parameters,
                "scenario":scenario,
                "need_scenario_notify": need_scenario_notify
            }, indent = 0)
        }

        engine_hasshin_result = engine_hasshin(data,current_state)

        if engine_hasshin_result[0] == False:
            error_message = f"Step start execution error: {engine_hasshin_result[1]} for task {step['current_task_id']} in scenario {scenario_launch_id}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            tasks_starting_status.append(False)
        tasks_starting_status.append(True)
    # проверка успешности запуска?

    #####################################
    # теперь надо записать в историю запуска -- сценарий запущен
    #####################################
    """Ожидается, что эта запись будет выполнена быстрее, чем завершатся все экземпляры движка с тасками"""
    
    update_scenario_history_line_result = update_scenario_history_line(2, "Сценарий запущен, исполняется", scenario_launch_id, current_state)
    if update_scenario_history_line_result[0] == False:
        error_message = f"update_scenario_history_line_result for scenario {scenario_launch_id} is False: {update_scenario_history_line_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), scenario_launch_id
    
    return True, "OK", currentFuncName(), scenario_launch_id


# async def sleep():
#     await asyncio.sleep(3)

def waiting_for_scenario_execution(iterations_limit: int, scenario_session_id: str, current_state: Dict):
    """Попробуем периодически образаться к табличке с историей запуска сценариев и дождаться, пока там не появится результат
    Но если будет ошибка движка, то это может быть бессмысленным. У нас нет гарантии, что отвал движков будет отражён в ошибке
    В это можно только верить.
    """
    execution_done_flag = False
    iterations_count = 0
    while(execution_done_flag == False):
        iterations_count = iterations_count + 1
        #####################################
        # читаем историю запусков сценариев
        #####################################
        get_scenario_history_line_result = get_scenario_history_line(scenario_session_id, current_state)
        if get_scenario_history_line_result[0] == False:
            error_message = f"get_scenario_history_line_result for scenario_session_id {scenario_session_id} is False: {get_scenario_history_line_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        scenario_execution_dict = get_scenario_history_line_result[3]
        current_status_code = scenario_execution_dict["status_code"]

        if current_status_code < 0:
            error_message = f"scenario execution error: {scenario_execution_dict['status']}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if current_status_code == 1:
            message = f"scenario done: {scenario_session_id}"
            logger_log(syslog.LOG_DEBUG, get_log_message(message, currentFuncName(), current_state))
            return True, message, currentFuncName(), get_scenario_history_line_result[3]
        
        if iterations_count >= iterations_limit:
            error_message = f"iterations limit out"
            logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        # раз в 3 секунды проверяем выполнение сценария
        time.sleep(3)

def get_scenarios_data_from_storage(scenario_execution_dict: Dict, current_state: Dict):
    """Функция позволяет забрать данные по сценарию из хранилища как есть"""

    scenario_data_dict = {}

    for i, step in enumerate(scenario_execution_dict["json"]["scenario"]["steps"]):
        step_data_name = f"{i}_{step['step_name']}"
        data_data_name = step["data_name"]
        if step["show"] == True:
            scenario_data_dict[step_data_name] = {}
            scenario_data_dict[step_data_name]["data"] = [{}]
            scenario_data_dict[step_data_name]["task_id"] = step['current_task_id']
            #######################################
            # получаем статус выполненной таски
            #######################################
            fetch_task_by_id_result = fetch_task_by_id(step['current_task_id'], current_state)
            if fetch_task_by_id_result[0] == False:
                error_message = f"Get task result {i} is False: {fetch_task_by_id_result[1]}"
                logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                scenario_data_dict[step_data_name]["status"] = error_message
            else:
                #######################################
                # получаем статус выполненной таски по task_id
                #######################################
                fetch_task_by_id_result = fetch_task_by_id(step['current_task_id'], current_state)
                if fetch_task_by_id_result[0] == False:
                    error_message = f"Failed to load task {step['current_task_id']}: {fetch_task_by_id_result[1]}"
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    scenario_data_dict[step_data_name]["status"] = error_message

                else: # выводим статус таски
                    task_by_id_data = fetch_task_by_id_result[3]
                    scenario_data_dict[step_data_name]["status_code"] = task_by_id_data["status_code"]
                    scenario_data_dict[step_data_name]["step_name"] = task_by_id_data["step_name"]
                    scenario_data_dict[step_data_name]["source_name"] = task_by_id_data["source_name"]
                    scenario_data_dict[step_data_name]["timestamp_start"] = task_by_id_data["timestamp_start"]
                    scenario_data_dict[step_data_name]["timestamp_stop"] = task_by_id_data["timestamp_stop"]
                    scenario_data_dict[step_data_name]["id"] = task_by_id_data["id"]

                    if task_by_id_data["status_code"] == 0:
                        scenario_data_dict[step_data_name]["status"] = "task is not started yet"
                    if task_by_id_data["status_code"] == 1:
                        scenario_data_dict[step_data_name]["status"] = "successful"
                    if task_by_id_data["status_code"] > 1:
                        scenario_data_dict[step_data_name]["status"] = "task is processed yet"
                    if task_by_id_data["status_code"] < 0:
                        scenario_data_dict[step_data_name]["status"] = f"task was finished with error: {task_by_id_data['status']}"

                # выводим описание таски
                scenario_data_dict[step_data_name]["description"] = step["description"]

                #######################################
                # получаем данные выполненной таски по task_id
                #######################################
                read_step_from_storage_result = read_step_from_storage({"target_id":step['current_task_id']}, current_state)
                if read_step_from_storage_result[0] == False:
                    error_message = f"Failed to load data of task {step['current_task_id']}: {read_step_from_storage_result[1]}"
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    scenario_data_dict[step_data_name]["data"] = [{"error":read_step_from_storage_result[1]}]
                    scenario_data_dict[step_data_name]["data_name"] = data_data_name
                else:
                    scenario_data_dict[step_data_name]["data"] = read_step_from_storage_result[3]['data']
                    scenario_data_dict[step_data_name]["data_name"] = data_data_name
    return scenario_data_dict

def scenario_filter_by_roles(scenario_list: list, user_roles: list, current_state: dict):
    try:
        allowed_scenarios = []
        for scenario in scenario_list:
            for user_role in user_roles:
                if user_role in scenario["roles"] or user_role == "fullmaster":
                    allowed_scenarios.append(scenario)
                    break
        return True, "OK", currentFuncName(), allowed_scenarios

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

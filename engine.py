import termios
import argparse
import time
import copy
import syslog
import pandas
import urllib.parse
import asyncio
import inspect

from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.engine.shared_memory import get_data_from_shared_memory
from app.engine.engine import *
from app.database.tasks import db_get_task_by_id, db_update_task_status, db_get_tasks_by_scenario_id, db_get_active_tasks_by_sourcename
from app.database.sources import db_get_source
from app.validation import *
from app.engine.storage import write_step_to_storage, read_step_from_storage
from app.engine.steps import input_parameter_validator
from app.validation import scenario_validator
from app.database.scenarios import update_scenario_history_line, get_scenario_history_line
from app.database.users import fetch_user_data
from app.notify.mattermost import notify_mattermost_proc
from app.notify.telegram import notify_telegram_proc

SLEEP_TIME = 2 # секунды
DEBUG = False

current_state = {
    "app_name":"Universal Harvester Engine",
    "app_version":"1.0.0",
    "main_session_id":"00000000-0000-0000-0000-000000000000",
    "user_session_id":"00000000-0000-0000-0000-000000000000",
    "client_ip_address":"127.0.0.1",
    "client_port":0,
    "username":"system"
}

async def main():
    global args
    parser = argparse.ArgumentParser(description="Engine UH")
    parser.add_argument(
        "-s",
        "--shared_memory_name",
        type=str,
        #default="",
        help="Имя объекта shared memory для получения мастер-ключа и других параметров"
    )

    global current_state
    args = parser.parse_args() # []

    ###############################################
    # логируем запуск и параметры запуска
    ###############################################

    logger_log(syslog.LOG_NOTICE, get_log_message(f"engine start, shared memory object: {args.shared_memory_name}", currentFuncName(),current_state))

    ###############################################
    # получаем параметры работы от фронта
    ###############################################
    engine_get_data_from_shared_memory_result = get_data_from_shared_memory(args.shared_memory_name, current_state)
    if engine_get_data_from_shared_memory_result[0] == False:
        logger_log(syslog.LOG_CRIT, get_log_message(f"engine_get_data_from_shared_memory_status is False: {engine_get_data_from_shared_memory_result[1]}", currentFuncName(),current_state))
        return
    current_state = engine_get_data_from_shared_memory_result[3]
    ########################################
    # получаем таску на исполнение
    ########################################

    db_get_task_by_id_result = db_get_task_by_id({"target_id":current_state["target_id"]}, current_state)

    if db_get_task_by_id_result[0] == False:
        logger_log(syslog.LOG_CRIT, get_log_message(f"db_get_task_by_id_result is False: {db_get_task_by_id_result[1]}", currentFuncName(), current_state))
        return
    
    if DEBUG: print("db_get_task_by_id_result", db_get_task_by_id_result[3])

    logger_log(syslog.LOG_DEBUG, get_log_message(f"task {db_get_task_by_id_result[3][0]} pid {db_get_task_by_id_result[3][1]} loaded", currentFuncName(),current_state))

    ########################################
    # обновляем статус таски как принятую на исполнение
    #######################################
    status_code = 2
    db_update_task_status_result = db_update_task_status(
        {
            "status_code":status_code,
            "status":"Принята к исполнению, подготовка и валидация",
            "timestamp_stop":currentTimestamp(),
            "id":current_state["target_id"],
            "result_rows_count": 0
        }, 
        current_state)
    if db_update_task_status_result[0] == False:
        logger_log(syslog.LOG_CRIT, get_log_message(
            f"Status updating error for {current_state['target_id']}, actual status is {status_code} / {currentTimestamp()}",
            currentFuncName(), current_state))
    
    ##############################################
    # получаем основные элементы таски
    ##############################################
    #id, pid, status_code, status, step_name, source_name, username, timestamp, in_scenario, json
    scenario_session_id = db_get_task_by_id_result[3][9] # Null для интерактивного запуска шага
    task_json = db_get_task_by_id_result[3][10]
    step_name = db_get_task_by_id_result[3][4] # это или имя шага как в базе для запуска отдельного шага, или псевдоним  при работе в рамках сценария
    source_name = db_get_task_by_id_result[3][5]
    

    if check_json_correct(task_json) == False:
        logger_log(syslog.LOG_CRIT, get_log_message(f"task json is not a valid json", currentFuncName(), current_state))
        return
    
    task_json = json.loads(task_json)
    step = task_json["step"]
    parameters = task_json["parameters"]
    scenario = task_json["scenario"] # {} пустой для интерактивного запуска шага
    need_scenario_notify = task_json["need_scenario_notify"]

    # проброс идентификатора таски в степ
    step["__id__"] = current_state["target_id"]
    
    # тут надо определить номер шага в рамках сценария, чтобы потом не запутаться в параметрах
    # для этого сверим таск id в current state и в шагах сценария
    # если сценарий пустой, то по дефолту имеем 0
    step_in_scenario_num = 0
    if "steps" in scenario:
        if isinstance(scenario["steps"],list):
            for i, in_scenario_step in enumerate(scenario["steps"]):
                if in_scenario_step["current_task_id"] == current_state["target_id"]:
                    step_in_scenario_num = i

    step["step_name"] = step_name # для функционирования кешированных запросов

    if scenario_session_id == "Null":
        scenario["steps"] = []
        scenario["description"] = ""
        scenario["llm"] = {"preprompt":"","postprompt":""}
        
    current_data = []

    if "__outervision__" in parameters:
        outervision_parameters = parameters["__outervision__"]
    else:
        outervision_parameters = None

    # подготовка контейнера для записи данных
    # он тут нужен в том числе и при ошибке работы сценария
    without_key_current_state = copy.deepcopy(current_state)
    del without_key_current_state["master_key"]
    stored_data = {
        "state":without_key_current_state,
        "data":current_data,
        "source_name":source_name,
        "step_name":step_name,
        "task":task_json,
        "scenario_session_id":scenario_session_id,
        "step_description":step["description"],
        "step_llm":step["llm"],
        "scenario_description":scenario["description"],
        "scenario_llm":scenario["llm"]
    }
    if DEBUG: print("\nstored_data:\n", stored_data)

    #######################################
    # валидируем scenario
    #######################################
    scenario_validator_result = scenario_validator(True, scenario, current_state)
    if scenario_validator_result[0] == False:
        # сценарий не прошёл валидацию
        message = f"Ошибка валидации блока scenario: {scenario_validator_result[1]}"
        stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            parameters,
                            -30, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
        return
    #######################################
    # получаем текущий source по имени
    #######################################
    db_get_source_result = db_get_source({"sourcename":source_name}, current_state)
    if db_get_source_result[0] == False:
        # сорс не был получен из БД
        message = f"Ошибка получения источника данных {source_name}: {db_get_source_result[1]}"
        stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            parameters, 
                            -29, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
        return
    
    if DEBUG: print("db_get_source_result", db_get_source_result[3])

    source = db_get_source_result[3][1]

    #######################################
    # валидируем сорс
    #######################################

    engine_source_parameters_validator_result = engine_source_parameters_validator(ENGINE_SOURCES_AND_FUNCTIONS_MAP, source, current_state)
    if engine_source_parameters_validator_result[0] == False:
        # сорс не прошёл валидацию, ставим статус в базу на таску, пишем в лог из завершаем работу
        message = f"Ошибка валидации источника данных {source_name}: {engine_source_parameters_validator_result[1]}"
        stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            parameters, 
                            -28, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
        return

        
    current_source = engine_source_parameters_validator_result[3] # сорс с полными параметрами и ключами

    ###################################
    # Нормализация параметров и (разжатие)
    ###################################
    #print(parameters)
    #step_in_scenario_num -- int с номером шага в сценарии. Для бессценарных -- 0
    #Разжатие
    if "conjoined_parameters" in scenario:
        if isinstance(scenario["conjoined_parameters"], dict) == False:
            message = f"Scenario conjoined_parameters is not a dict"
            stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            parameters, 
                            -27, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
            return
        # проверяем наличие объединяемого параметра во входных параметрах
        for conj_param in scenario["conjoined_parameters"].keys():
            if conj_param not in parameters:
                # объединения параметров нет во входных параметрах
                message = f"Объединённый параметр {conj_param} отсутствует во входных параметрах"
                stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            parameters, 
                            -27, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
                return
            if isinstance(scenario["conjoined_parameters"][conj_param], list) == False:
                message = f"Scenario conjoined_parameter {conj_param} is not a list"
                stop_engine_with_scenario_history(
                                syslog.LOG_ERR,
                                message, 
                                current_data, stored_data,
                                scenario["steps"],
                                parameters, 
                                -27, #current_status
                                f"Сценарий завершён с ошибкой: {message}",
                                scenario_session_id,
                                need_scenario_notify, 
                                current_state)
                return
        # раскрываем объединённые параметры    
        for conj_parameter in scenario["conjoined_parameters"].keys():
            for conj_element_parameter in scenario["conjoined_parameters"][conj_parameter]:
                parameters[conj_element_parameter] = parameters[conj_parameter]


    #print(parameters)
    for parameter in list(parameters.keys()):
        if ":" not in parameter and "conjoined_parameters" in scenario:
            del parameters[parameter]
        else:
            parameter_step_num = parameter[:parameter.find(":")]
            try:
                parameter_step_num = int(parameter_step_num)
                if parameter_step_num != step_in_scenario_num:
                    del parameters[parameter]
            except BaseException as e:
                pass
            

    # теперь чистим параметры, чтобы убрать int:
    for parameter in list(parameters.keys()):
        if ":" in parameter:
            parameters[parameter[parameter.find(":")+1:]] = parameters[parameter]
            del parameters[parameter]
    #print(parameters)

    ###################################
    # валидируем параметры шага
    ###################################

    input_parameter_validator_result = input_parameter_validator(parameters, step, current_state)
    if input_parameter_validator_result[0] == False:
        message = f"Ошибка валидации входных параметров для {step_name}: {input_parameter_validator_result[1]}"
        stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            parameters, 
                            -26, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
        return
            
    parameters = input_parameter_validator_result[3]
    if DEBUG: print("\ninput_parameter_validator_result", input_parameter_validator_result,"\n")

    ######################################
    # добавление/изменение блоков apply и generate_parameters, если они были переопределёны сценарием
    ######################################
    if "steps" in scenario:
        if len(scenario["steps"]) > step_in_scenario_num: # для случая отладочного запуска шага без сценария
            if "apply_replacement" in scenario["steps"][step_in_scenario_num]:
                step["apply"] = scenario["steps"][step_in_scenario_num]["apply_replacement"]
            if "generate_parameters_replacement" in scenario["steps"][step_in_scenario_num]:
                step["generate_parameters"] = scenario["steps"][step_in_scenario_num]["generate_parameters_replacement"]

    ######################################
    # генерация параметров
    ######################################
    if "apply" not in step:
        if "generate_parameters" in step:
            process_parameters_generation_result = process_parameters_generation({},step["generate_parameters"], parameters, step["input_parameters"], current_state)
            if process_parameters_generation_result[0] == False:
                message = f"Ошибка генерации параметров шага {step_name}: {process_parameters_generation_result[1]}"
                stop_engine_with_scenario_history(
                                syslog.LOG_ERR,
                                message, 
                                current_data, stored_data,
                                scenario["steps"],
                                parameters, 
                                -25, #current_status
                                f"Сценарий завершён с ошибкой: {message}",
                                scenario_session_id,
                                need_scenario_notify, 
                                current_state)
                return
            current_parameters = process_parameters_generation_result[3]
        else:
            current_parameters = parameters # без генерации параметров
    else:
        current_parameters = parameters # без генерации параметров
    if DEBUG: print("\nAFTER PARAMETERS GENERATION\n",current_parameters)


    ######################################
    # инпут-инъектирование
    ######################################
    
    process_injections_result = process_injections(step["query"], current_parameters, current_state)
    if process_injections_result[0] == False:
        message = f"Ошибка инъектирования параметров в query шага {step_name}: {process_injections_result[1]}"
        stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            current_parameters, 
                            -24, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
        return
    current_query = process_injections_result[3]  

    ######################################
    # инпут-инъектирование apply, если имеется
    ######################################
    # apply через apply инъектить нельзя, только через параметры
    if "apply" in step:
        process_injections_result = process_injections(step["apply"], current_parameters, current_state)
        if process_injections_result[0] == False:
            message = f"Ошибка инъектирования параметров в query шага {step_name}: {process_injections_result[1]}"
            stop_engine_with_scenario_history(
                                syslog.LOG_ERR,
                                message, 
                                current_data, stored_data,
                                scenario["steps"],
                                current_parameters, 
                                -24, #current_status
                                f"Сценарий завершён с ошибкой: {message}",
                                scenario_session_id,
                                need_scenario_notify, 
                                current_state)
            return
        step["apply"] = process_injections_result[3]

    ####################################
    # получаем список зависимостей
    ####################################
    get_step_dependency_result = get_step_dependency(step, current_source, current_query, current_state)
    if get_step_dependency_result[0] == False:
        current_status = -3
        status_text = f"Ошибка получения списка зависимостей шага {step_name}: {get_step_dependency_result[1]}"
        message = f"Ошибка получения списка зависимостей шага {step_name}: {get_step_dependency_result[1]}"
        stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            current_parameters, 
                            -23, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
        return
            
    dependency = get_step_dependency_result[3] # тут используется step_scenario_name

    if DEBUG: print("\n\ndependency", dependency, "\n\n")

    ########################################
    # обновляем статус таски как ожидание зависимостей
    #######################################
    status_code = 3
    db_update_task_status_result = db_update_task_status(
        {
            "status_code":status_code,
            "status":"Ожидание зависимостей",
            "timestamp_stop":currentTimestamp(),
            "id":current_state["target_id"],
            "result_rows_count": 0
        }, 
        current_state)
    if db_update_task_status_result[0] == False:
        logger_log(syslog.LOG_CRIT, get_log_message(
            f"Status updating error for {current_state['target_id']}, actual status is {status_code} / {currentTimestamp()}",
            currentFuncName(), current_state))
    ##########################################
    # проверяем зависимости и восстанавливаем область видимости
    ##########################################
    outervision_data = {}

    if len(dependency) > 0: # если у нас есть зависимости, то мы их должны включить в область видимости
        if scenario_session_id == "Null": # в имени шага не может быть : -- посыпятся sqlite таблицы?
            #выполнение шага без сценария
            # тут смотрим область видимости по специальному блоку параметров __outervision__
            if not outervision_parameters:
                message = f"В параметрах отсутствует блок __outervision__ для указания зависимостей"
                stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            current_parameters, 
                            -22, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
                return
            for dep in dependency:
                if dep not in outervision_parameters:
                    message = f"В блоке параметров __outervision__ отсутствует зависимость {dep}"
                    stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            current_parameters, 
                            -21, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
                    return
                loaded_task_data_result = read_step_from_storage({"target_id":outervision_parameters[dep]} ,current_state)
                if loaded_task_data_result[0] == False:
                    message = f"Ошибка чтения таски {outervision_parameters[dep]}: {loaded_task_data_result[1]}"
                    stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            current_parameters, 
                            -20, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
                    return
                loaded_task_data = loaded_task_data_result[3]
                outervision_data[dep] = loaded_task_data

        else:
            # забираем все таски по исполнению сценария, они будут лежать в конструкции scenarios -> steps
            deb_task_id_list = []
            deb_task_id_map = {}
            for dep in dependency:
                for in_current_scenario_step in scenario["steps"]:
                    if in_current_scenario_step["data_name"] == dep:
                        deb_task_id_list.append(in_current_scenario_step["current_task_id"])
                        deb_task_id_map[dep] = in_current_scenario_step["current_task_id"]
                        
                

            # тут мы должны дождаться, когда все зависимости будут выполнены
            pass_flag_list = [False]
            while(False in pass_flag_list):
                pass_flag_list = []

                # получаем актуальный список тасок из БД
                db_get_tasks_by_scenario_id_result = db_get_tasks_by_scenario_id({"in_scenario":scenario_session_id} ,current_state)
                if db_get_tasks_by_scenario_id_result[0] == False:
                    message = f"Ошибка получения списка тасок сценария с актуальными статусами {step_name}: {db_get_tasks_by_scenario_id_result[1]}"
                    stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            current_parameters, 
                            -19, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
                    return
                        
                scenario_tasks = db_get_tasks_by_scenario_id_result[3]
                from_db_tasks = {}

                for scenario_task in scenario_tasks:
                    another_task_id = scenario_task[0]
                    another_task_step_status_code = scenario_task[1]
                    from_db_tasks[another_task_id] = another_task_step_status_code

                for deb_task_id in deb_task_id_list:
                    if deb_task_id not in from_db_tasks:
                        message = f"Зависимости {dep} ({deb_task_id}) нет в списке запущенных сценарием тасок"
                        stop_engine_with_scenario_history(
                            syslog.LOG_ERR,
                            message, 
                            current_data, stored_data,
                            scenario["steps"],
                            current_parameters, 
                            -18, #current_status
                            f"Сценарий завершён с ошибкой: {message}",
                            scenario_session_id,
                            need_scenario_notify, 
                            current_state)
                        return
                    # проверяем статусы выполнения зависимостей
                    if from_db_tasks[deb_task_id] == 1 or from_db_tasks[deb_task_id] < 0: # статус завершения
                        pass_flag_list.append(True)
                    elif from_db_tasks[deb_task_id] > 1 or from_db_tasks[deb_task_id] == 0:
                        pass_flag_list.append(False)
                    # else: # при этих статусах ждать выполнения не стоит
                    #     message = f"Зависимость {dep} ({deb_task_id}) была завершена с ошибкой"
                    #     stop_engine_with_scenario_history(
                    #         syslog.LOG_ERR,
                    #         message, 
                    #         current_data, stored_data,
                    #         scenario["steps"],
                    #         current_parameters, 
                    #         -17, #current_status
                    #         f"Сценарий завершён с ошибкой: {message}",
                    #         scenario_session_id, 
                    #         current_state)
                    #     return
                    
                if False in pass_flag_list:
                    # ждём у моря погоды
                    time.sleep(SLEEP_TIME)

            # тут мы точно уверены, что зависимости все завершены, можно грузить в память
            for dep in dependency:
                if dep not in deb_task_id_map:
                    message = f"Зависимость {dep} отсутствует в deb_task_id_map"
                    stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -16, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
                    return


                loaded_task_data_result = read_step_from_storage({"target_id":deb_task_id_map[dep]} ,current_state)
                if loaded_task_data_result[0] == False:
                    message = f"Ошибка чтения при загрузке данных зависимости таски {deb_task_id_map[dep]}: {loaded_task_data_result[1]}"
                    stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -15, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
                    return
                loaded_task_data = loaded_task_data_result[3]
                outervision_data[dep] = loaded_task_data
    
    
    ##################################
    # Формируем карту данных, они по итогу попадут в конечную source функцию исполнения шага
    ##################################

        #     "step_description":step["description"],
        # "step_llm":step["llm"],
        # "scenario_description":scenario["description"]

    data_map = {}
    for dep in outervision_data:
        data_map[dep] = {}
        data_map[dep]["data"] = outervision_data[dep]["data"]
        data_map[dep]["scenario_description"] = outervision_data[dep]["scenario_description"]
        data_map[dep]["scenario_llm"] = outervision_data[dep]["scenario_llm"]
        data_map[dep]["step_description"] = outervision_data[dep]["step_description"]
        data_map[dep]["step_llm"] = outervision_data[dep]["step_llm"]

    ##################################################
    # получение исполняемой функции перед выполнением
    ##################################################

    if current_source["type"] not in ENGINE_SOURCES_AND_FUNCTIONS_MAP:
        message = f"Тип источкика {current_source['type']} отсутствует в ENGINE_SOURCES_AND_FUNCTIONS_MAP"
        stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -14, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
        return
    if step["source_function"] not in ENGINE_SOURCES_AND_FUNCTIONS_MAP[current_source["type"]]["functions"]:
        message = f"Функция шага {step['source_function']} отсутствует в ENGINE_SOURCES_AND_FUNCTIONS_MAP[{current_source['type']}] функциях"
        stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -13, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
        return
    
    current_execute_function = ENGINE_SOURCES_AND_FUNCTIONS_MAP[current_source["type"]]["functions"][step["source_function"]]["functions"]["query"]
    converter_exists = False
    if "converter" in ENGINE_SOURCES_AND_FUNCTIONS_MAP[current_source["type"]]["functions"][step["source_function"]]["functions"]:
        current_execute_converter = ENGINE_SOURCES_AND_FUNCTIONS_MAP[current_source["type"]]["functions"][step["source_function"]]["functions"]["converter"]
        converter_exists = True

    ########################################
    # обновляем статус таски как ожидание очереди исполнения
    #######################################
    status_code = 4
    db_update_task_status_result = db_update_task_status(
        {
            "status_code":status_code,
            "status":"Ожидание очереди исполнения",
            "timestamp_stop":currentTimestamp(),
            "id":current_state["target_id"],
            "result_rows_count": 0
        }, 
        current_state)
    if db_update_task_status_result[0] == False:
        logger_log(syslog.LOG_CRIT, get_log_message(
            f"Status updating error for {current_state['target_id']}, actual status is {status_code} / {currentTimestamp()}",
            currentFuncName(), current_state))
    ####################################  
    # проверяем очередь параллелелизма
    ####################################
    
    # получаем список активных тасок для данного сорса
    # если их больше, чем "max_threads", то ждём
    if "max_threads" in current_source:
        current_threads = 999999 # do while emulation
        while(current_threads > current_source["max_threads"]):
            db_get_active_tasks_by_sourcename_result = db_get_active_tasks_by_sourcename({"source_name":source_name, "status_code":5},current_state)
            if db_get_active_tasks_by_sourcename_result == False:
                message = f"Ошибка получения списка активных тасок по сорсу {source_name}: {db_get_active_tasks_by_sourcename_result[1]}"
                stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -12, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
                return
            active_task_list = db_get_active_tasks_by_sourcename_result[3]
            current_threads = len(active_task_list)
            if current_threads > current_source["max_threads"]:
                # ждём у моря погоды
                time.sleep(SLEEP_TIME)
    


    ########################################
    # обновляем статус таски как исполняемая на источнике
    #######################################
    status_code = 5
    db_update_task_status_result = db_update_task_status(
        {
            "status_code":status_code,
            "status":"Исполнение на источнике",
            "timestamp_stop":currentTimestamp(),
            "id":current_state["target_id"],
            "result_rows_count": 0
        }, 
        current_state)
    if db_update_task_status_result[0] == False:
        logger_log(syslog.LOG_CRIT, get_log_message(
            f"Status updating error for {current_state['target_id']}, actual status is {status_code} / {currentTimestamp()}",
            currentFuncName(), current_state))
    ###################################################
    # исполнение / apply генерация параметров и исполнение
    ###################################################
    #current_data = []

    if DEBUG: print("\nBefore launch:","\ncurrent_source\n",current_source,"\ncurrent_query\n", current_query,"\nstep\n", step,"\nparameters\n", parameters,"\ncurrent_state\n", current_state)

    if "apply" in step:
        if "target_data" not in step["apply"]:
            message = f"Отсутствует target_data в блоке apply шага {step_name}"
            stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -11, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
            return
        target_data = step["apply"]["target_data"]
        if target_data not in data_map:
            message = f"Отсутствует target_data {target_data} в области видимости шага {step_name}"
            stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -10, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
            return
        
        applied_data = data_map[target_data]["data"]
        if len(applied_data) == 0:
            message = f"Данные {target_data} отсутствуют (len=0)"
            stop_engine_with_scenario_history(
                        syslog.LOG_WARNING,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        1, #current_status
                        f"Сценарий завершён c предупреждением: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
            return
        if "target_parameters" not in step["apply"]:
            message = f"В ноде apply->{target_data} шага {step_name} отсутствует блок target_parameters"
            stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -8, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
            return
        # проверяем наличие прикрепляемых полей в каждой записи target_data
        for parameter in step["apply"]["target_parameters"]:
            for i, data_node in enumerate(applied_data):
                if parameter["column_name"] not in data_node:
                    message = f"Столбец {parameter['column_name']} отсутствует в строке {i} применяемых (apply) данных {target_data} для шага {step_name}"
                    stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -7, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
                    return
        # проверки завершены, теперь запускаем цикл выполнения
        for i, data_node in enumerate(applied_data):
            current_applied_parameters = copy.deepcopy(current_parameters)
            for parameter in step["apply"]["target_parameters"]:
                # добавляем параметры applied

                # убираем данную проверку для возможности переопределения уже имеющихся параметров

                # if i==1 and parameter["as"] in current_applied_parameters:
                #     message = f"Обнаружена коллизия параметров apply: добавляемый параметр {parameter["as"]} уже существовует"
                #     stop_engine_with_scenario_history(
                #         syslog.LOG_ERR,
                #         message, 
                #         current_data, stored_data,
                #         scenario["steps"],
                #         current_parameters, 
                #         -6, #current_status
                #         f"Сценарий завершён с ошибкой: {message}",
                #         scenario_session_id,
                #         need_scenario_notify, 
                #         current_state)
                #     return

                # опциональный паттерн создания параметра
                if "pattern" not in parameter:
                    current_applied_parameters[parameter["as"]] = data_node[parameter["column_name"]]
                else:
                    if isinstance(parameter["pattern"], str):
                        pattern_dict = {
                            "__pattern_value__":data_node[parameter["column_name"]],
                            "__pattern_data__":target_data,
                            "__pattern_column__":parameter["column_name"],
                            "__pattern_as__":parameter["as"]
                        }
                        current_applied_parameters[parameter["as"]] = parameter["pattern"] % pattern_dict
            # делаем генерацию параметров

            if "generate_parameters" in step:
                process_parameters_generation_result = process_parameters_generation(step["apply"], step["generate_parameters"], current_applied_parameters, step["input_parameters"], current_state)
                if process_parameters_generation_result[0] == False:
                    message = f"Ошибка генерации параметров шага {step_name}: {process_parameters_generation_result[1]}"
                    stop_engine_with_scenario_history(
                                    syslog.LOG_ERR,
                                    message, 
                                    current_data, stored_data,
                                    scenario["steps"],
                                    parameters, 
                                    -25, #current_status
                                    f"Сценарий завершён с ошибкой: {message}",
                                    scenario_session_id,
                                    need_scenario_notify, 
                                    current_state)
                    return
                current_applied_parameters = process_parameters_generation_result[3]

            # инпут-инъектирование новых параметров
            process_injections_result = process_injections(step["query"], current_applied_parameters, current_state)
            if process_injections_result[0] == False:
                message = f"Ошибка инъектирования параметров в apply query шага {step_name}: {process_injections_result[1]}"
                stop_engine_with_scenario_history(
                                    syslog.LOG_ERR,
                                    message, 
                                    current_data, stored_data,
                                    scenario["steps"],
                                    current_parameters, 
                                    -24, #current_status
                                    f"Сценарий завершён с ошибкой: {message}",
                                    scenario_session_id,
                                    need_scenario_notify, 
                                    current_state)
                return
            current_query = process_injections_result[3] 
            # всё готово к выполнению
            current_data_shard = []
            ########################
            # Выполнение (apply)
            ########################
            if inspect.iscoroutinefunction(current_execute_function):
                current_execute_query_status = await current_execute_function(data_map, current_source, current_query, step, current_applied_parameters, current_state)
            else:
                current_execute_query_status = current_execute_function(data_map, current_source, current_query, step, current_applied_parameters, current_state)
            if current_execute_query_status[0] == False:
                message = f"Ошибка исполнения шага {step_name}: {current_execute_query_status[1]}"
                stop_engine_with_scenario_history(
                        syslog.LOG_ERR,
                        message, 
                        current_data, stored_data,
                        scenario["steps"],
                        current_parameters, 
                        -5, #current_status
                        f"Сценарий завершён с ошибкой: {message}",
                        scenario_session_id,
                        need_scenario_notify, 
                        current_state)
                return
            current_data_shard = current_execute_query_status[3]

            # if converter_exists == True:
            #     current_execute_converter_status = current_execute_converter(current_data, current_source, current_query, step, parameters, current_state)
            #     if current_execute_converter_status[0] == False:
            #         message = f"Ошибка исполнения конвертера шага {step_name}: {current_execute_converter_status[1]}"
            #         stop_engine_with_scenario_history(
            #             syslog.LOG_ERR,
            #             message, 
            #             len(current_data),
            #             scenario["steps"],
            #             current_parameters, 
            #             -4, #current_status
            #             f"Сценарий завершён с ошибкой: {message}", 
            #             scenario_session_id, 
            #             current_state)
            #         return
            #     current_data_shard = current_execute_converter_status[3]

            # добавляем к выводу наши параметры, чтобы мы потом смогли сделать JOIN
            for current_data_shard_line in current_data_shard:
                for parameter in step["apply"]["target_parameters"]:
                    current_data_shard_line["applied_"+parameter["as"]] = current_applied_parameters[parameter["as"]]

            current_data = current_data + current_data_shard
        

        # чистка возможных дубликатов при необходимости
        if "output_unique_fields" in step["apply"]:
            if isinstance(step["apply"]["output_unique_fields"], list) == True:
                if len(step["apply"]["output_unique_fields"]) > 0:
                    current_data = pandas.DataFrame(current_data).drop_duplicates(step["apply"]["output_unique_fields"]).to_dict('records')
    else:#source, query, step, parameters, current_state
        ########################
        # Выполнение (без apply)
        ########################
        if inspect.iscoroutinefunction(current_execute_function):
            current_execute_query_status = await current_execute_function(data_map, current_source, current_query, step, parameters, current_state)
        else:
            current_execute_query_status = current_execute_function(data_map, current_source, current_query, step, parameters, current_state)
        current_data = current_execute_query_status[3]
        if current_execute_query_status[0] == False:
            message = f"Ошибка исполнения шага {step_name}: {current_execute_query_status[1]}"
            stop_engine_with_scenario_history(
                syslog.LOG_ERR,
                message, 
                current_data, stored_data,
                scenario["steps"],
                current_parameters, 
                -3, #current_status
                f"Шаг завершён с ошибкой: {message}", 
                scenario_session_id,
                need_scenario_notify, 
                current_state)
            return
        #current_data = current_execute_query_status[3]

        # if converter_exists == True:
        #     current_execute_converter_status = current_execute_converter(current_data, current_source, current_query, step, parameters, current_state)
        #     if current_execute_converter_status[0] == False:
        #         current_status = -1
        #         logger_log(syslog.LOG_ERR, get_log_message(f"current_execute_query_status is false: {current_execute_converter_status[1]}", currentFuncName(),current_state))
        #         db_update_task_status_result = db_update_task_status(
        #             {
        #                 "status_code":current_status,
        #                 "status":f"Ошибка исполнения конвертера шага {step_name}: {current_execute_converter_status[1]}",
        #                 "timestamp_stop":currentTimestamp(),
        #                 "id":current_state["target_id"]
        #             }, 
        #             current_state)
        #         if db_update_task_status_result[0] == False:
        #             logger_log(syslog.LOG_CRIT, get_log_message(
        #                 f"Ошибка обновления статуса таски {current_state["target_id"]}, должен быть статус {current_status} от {currentTimestamp()}", 
        #                 currentFuncName(), current_state))
        #         return
        #     current_data = current_execute_converter_status[3]

    ####################################################    
    # защита от дурака
    ####################################################
    if isinstance(current_data, list) == False:
        message = f"Результат исполнение шага {step_name} не является листом []: {str(type(current_data))}"
        stop_engine_with_scenario_history(
            syslog.LOG_ERR,
            message,
            current_data, stored_data,
            scenario["steps"],
            current_parameters, 
            -2, #current_status
            f"Сценарий завершён с ошибкой: {message}",  
            scenario_session_id,
            need_scenario_notify, 
            current_state)
        return



    ##current_data = [{}]
    ########################################
    # обновляем статус таски как запись в хранилище
    #######################################
    # status_code = 6
    # db_update_task_status_result = db_update_task_status(
    #     {
    #         "status_code":status_code,
    #         "status":"Запись результата в хранилище",
    #         "timestamp_stop":currentTimestamp(),
    #         "id":current_state["target_id"],
    #         "result_rows_count": 0
    #     }, 
    #     current_state)
    # if db_update_task_status_result[0] == False:
    #     logger_log(syslog.LOG_CRIT, get_log_message(
    #         f"Status updating error for {current_state["target_id"]}, actual status is {status_code} / {currentTimestamp()}", 
    #         currentFuncName(), current_state))
    ##########################################
    # запись результата в storage
    ##########################################
    # without_key_current_state = copy.deepcopy(current_state)
    # del without_key_current_state["master_key"]
    # stored_data = {
    #     "state":without_key_current_state,
    #     "data":current_data,
    #     "source_name":source_name,
    #     "step_name":step_name,
    #     "task":task_json,
    #     "scenario_session_id":scenario_session_id,
    #     "step_description":step["description"],
    #     "step_llm":step["llm"],
    #     "scenario_description":scenario["description"],
    #     "scenario_llm":scenario["llm"]
    # }
    # if DEBUG: print("\nstored_data:\n", stored_data)


    
    #########################################
    # завершение работы таски, запись б БД tasks
    #########################################
    stop_engine_with_scenario_history(
        syslog.LOG_NOTICE,
        f"Таска завершена успешно, получено {len(current_data)} строк данных", 
        current_data,
        stored_data, 
        scenario["steps"],
        current_parameters, 
        1, #current_status
        "Сценарий завершён успешно", # scenario status, если это последняя таска
        scenario_session_id,
        need_scenario_notify, 
        current_state)
    return

def stop_engine_with_scenario_history(log_level, task_log_message: str, result: list, stored_data: dict, scenario_steps: List, parameters: Dict, status_code: int, status: str, scenario_session_id: str, need_scenario_notify: bool, current_state: Dict) -> None:
    # функция должна вызываться перед каждым return
    # она также обеспечивает нотификацию и обновление в таблице tasks
    # сначала пишем в storage то, что получилось
    try:
        stored_data["data"] = result
        stored_data["status_code"] = status_code
        stored_data["status"] = status

        write_step_to_storage_result = write_step_to_storage(stored_data, current_state)
        if write_step_to_storage_result[0] == False:
            message = f"Ошибка записи результата шага в хранилище task {current_state['target_id']}"
            logger_log(syslog.LOG_ERR, get_log_message(message, currentFuncName(),current_state))
            task_log_message = message
            status_code = -1
            

        logger_log(log_level, get_log_message(task_log_message, currentFuncName(),current_state))
        result_rows_count = len(result)
        db_update_task_status_result = db_update_task_status(
            {
                "status_code":status_code,
                "status":task_log_message,
                "timestamp_stop":currentTimestamp(),
                "id":current_state["target_id"],
                "result_rows_count": result_rows_count
            }, 
            current_state)
        if db_update_task_status_result[0] == False:
            logger_log(syslog.LOG_CRIT, get_log_message(
                f"Status updating error for {current_state['target_id']}, actual status is {status_code} / {currentTimestamp()}",
                currentFuncName(), current_state))

        # получаем параметры нотификации
        # username есть в current_state
        fetch_user_data_result = fetch_user_data(current_state["username"], current_state)
        if fetch_user_data_result[0] == False:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка получения данных пользователя {current_state['username']}", currentFuncName(), current_state))
            return
                
        current_user_json = fetch_user_data_result[3]["json"]


        need_notify_in_last_step = False

        if scenario_session_id == "Null":
            # когда мы запускаем сценарий в режиме отладки, мы не делаем нотификацию
            pass
        else:
            # теперь надо полнять очерёдность тасок, по идее обновлять должна последняя таска
            # но на самом деле очерёдность выполнения не имеет жёсткой последовательности
            # пока что примем, что отрабатывать должна последняя таска по списку запуска сценария
            # вычисляем, последняя ли это выполняемая таска
            
            # получаем актуальный список тасок из БД
            db_get_tasks_by_scenario_id_result = db_get_tasks_by_scenario_id({"in_scenario":scenario_session_id} ,current_state)
            if db_get_tasks_by_scenario_id_result[0] == False:
                logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка получения тасок по session_id для {current_state['username']}", currentFuncName(), current_state))
                return
                        
            scenario_tasks = db_get_tasks_by_scenario_id_result[3]
            
            last_step = True

            for scenario_task in scenario_tasks:
                another_task_id = scenario_task[0]
                if another_task_id != current_state["target_id"]:
                    another_task_step_status_code = scenario_task[1]
                    if another_task_step_status_code > 1 or another_task_step_status_code == 0:
                        last_step = False
                        break


            if last_step:
                # текущая таска является последней завершённой
                update_scenario_history_line_result = update_scenario_history_line(status_code, status, scenario_session_id, current_state)
                if update_scenario_history_line_result[0] == False:
                    logger_log(syslog.LOG_CRIT, get_log_message(
                        f"Ошибка обновления статуса сессии сценария {current_state['target_id']}, должен быть статус {status_code} ({status}) от {currentTimestamp()}",
                        currentFuncName(), current_state))

        if "notify" in current_user_json and need_scenario_notify == True and last_step == True:
            if scenario_session_id != "Null":
                get_scenario_history_line_result = get_scenario_history_line(scenario_session_id, current_state)
                if get_scenario_history_line_result[0] == False:
                    logger_log(syslog.LOG_CRIT, get_log_message(
                        f"Ошибка получения истории сценария {scenario_session_id} в task {current_state['target_id']}",
                        currentFuncName(), current_state))
                    scenario_parameters = {"error":f"Ошибка получения параметров сценария: {get_scenario_history_line_result[1]}"}
                else:
                    scenario_parameters = get_scenario_history_line_result[3]["json"]["parameters"]

            notify_text = "Dummy notify text"
            if scenario_session_id == "Null":
                if status_code == 1:
                    notify_text = f"Шаг {current_state['target_id']} с параметрами {json.dumps(parameters, indent=2, ensure_ascii=False)} завершён успешно."
                if status_code < 0:
                    notify_text = f"Шаг {current_state['target_id']} с параметрами {json.dumps(parameters, indent=2, ensure_ascii=False)} завершён с ошибкой: {status}."
                if status_code == 0 or status_code > 1:
                    notify_text = f"Шаг {current_state['target_id']} с параметрами {json.dumps(parameters, indent=2, ensure_ascii=False)} находится в работе."
            else:
                base_link = current_state['itself_link'] + urllib.parse.quote(f"result/{scenario_session_id}")
                if status_code == 1:
                    notify_text = f"Сценарий {scenario_session_id} с параметрами {json.dumps(scenario_parameters, indent=2, ensure_ascii=False)} завершён успешно: [pretty]({base_link}/pretty), [xlsx]({base_link}/xlsx), [csv]({base_link}/csv)."
                if status_code < 0:
                    notify_text = f"Сценарий {scenario_session_id} с параметрами {json.dumps(scenario_parameters, indent=2, ensure_ascii=False)} завершён с ошибкой: {status}, [pretty]({base_link}/pretty)."
                if status_code == 0 or status_code > 1:
                    notify_text = f"Сценарий {scenario_session_id} с параметрами {json.dumps(scenario_parameters, indent=2, ensure_ascii=False)} находится в работе"
            
            #print(notify_text)
            if "mattermost" in current_user_json["notify"]:
                notify_mattermost_proc(current_user_json["notify"]["mattermost"], notify_text, current_state)

            if "telegram" in current_user_json["notify"]:
                notify_telegram_proc(current_user_json["notify"]["telegram"], notify_text, current_state)

    except BaseException as e:
        error_message = f"fail: {str(e)}, actual status of task {current_state['target_id']} is {status_code} ({status})"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None


#main()
if __name__ ==  '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())





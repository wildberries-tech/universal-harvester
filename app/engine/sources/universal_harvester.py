import duckdb

import pandas
import syslog
import json
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName


def execute_local_scenario(data_map, source, query, step, parameters, current_state):
    from app.database.scenarios import db_get_scenario_by_name
    from app.engine.scenarios import run_scenario, waiting_for_scenario_execution, get_scenarios_data_from_storage
    # поскольку мы используем inmemory, то клиента к системе проверять не нужно
    try:
        scenario_name = query["scenario_name"]
        result_data_name = query["result_data_name"]
        ##############################################
        # получаем сценарий из бд по имени
        ##############################################
        db_get_scenario_by_name_result = db_get_scenario_by_name(scenario_name, current_state)
        if db_get_scenario_by_name_result[0] == False:
            error_message = f"get scenario by name error: {db_get_scenario_by_name_result[1]}"
            #logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
            #return
        
        scenario_dict = db_get_scenario_by_name_result[3]
        scenario_json = json.dumps(scenario_dict["json"])

        ##############################################
        # права запуска
        ##############################################
        # предполагается, что если главный сценарий был запущен с учётом его ролей
        # то разрешено запустить любой подчинённый сценарий
        # т.е. роль fullmaster

        user_roles = ["fullmaster"]

        ##############################################
        # процедура запуска сценария
        ##############################################
        need_scenario_notify = False # нотификации на подчинённые сценарии не нужны
        run_scenario_result = run_scenario(user_roles, scenario_name, scenario_json, query["parameters"], need_scenario_notify, step["__id__"], current_state)
        if run_scenario_result[0] == False:
            error_message = f"scenario launch error: {run_scenario_result[1]}"
            logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        scenario_session_id = run_scenario_result[3]

        ##############################################
        # ожидание выполнения
        ##############################################
        waiting_for_scenario_execution_result = waiting_for_scenario_execution(10000, scenario_session_id, current_state)
        if waiting_for_scenario_execution_result[0] == False:
            error_message = f"scenario execution error: {waiting_for_scenario_execution_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
            #return
        
        scenario_execution_dict = waiting_for_scenario_execution_result[3]

        ##############################################
        # получение результата из хранилища
        ##############################################
        scenarios_data = get_scenarios_data_from_storage(scenario_execution_dict, current_state)

        ##############################################
        # формирование вывода (выбор data_name)
        ##############################################
        # правильнее будет сохранить все данные, чтобы любые забрать, или сохранять листом. На подумать
        for step_data in scenarios_data.keys():
            if scenarios_data[step_data]["data_name"] == result_data_name:
                return True, "OK", currentFuncName(), scenarios_data[step_data]["data"]

        error_message = f"there is not result_data_name {result_data_name} in scenarios_data"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []


    except BaseException as e:
        error_message = f"universal harvester local scenario execute fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
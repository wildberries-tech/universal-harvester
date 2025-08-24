import syslog
from app.logging import get_log_message, logger_log, currentFuncName
from typing import Tuple, Optional, Dict, List
from nicegui import ui
from app.validation import client_auth_token_validation, client_auth_token_test
from app.engine.scenarios import run_scenario, waiting_for_scenario_execution, get_scenarios_data_from_storage
from app.database.users import db_get_user
import bcrypt
import json
from app.validation import check_json_correct
from app.database.scenarios import db_get_scenario_by_name
from app.interface.additional import scenario_export_to_raw_json, scenario_export_to_zip_json, scenario_export_to_zip_csv, scenario_export_to_xlsx



def api_scenario_launch_page(client_headers: Dict, scenario_name: str, parameters: str, output_type: str, current_state: Dict) -> None:
    """Функция, которая отвечает за работу API запуска сценариев. Основная функция интеграции с другими автоматизированными системами.
    Логика действий следующая:
    1. Валидируем всё, что пришло, данные должны быть корректные + отсеивание потенциальных векторов атак.
    2. Проверяем API, проверяем пользователя, к которому привязан API-ключ, проверяем его права доступа.
    3. Достаём сценарий по имени.
    4. Валидируем параметры запуска.
    5. Запускаем сценарий -- партия движков.
    6. Ждём отработки сценария.
    7. Читаем результат отработки сценария.
    8. Возвращаем ответ в соответствии с output_type.

    Апи ключи лежат вместе с остальными ключами в таблице keys. API-ключ редставляет собой base64 system:account:hash(key)
    """
    DEBUG = False
    try:
        logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
        ##############################################
        # проверяем наличие хедера "Authorization"
        ##############################################
        if "authorization" not in client_headers:
            error_message = f'there was not authorization header "Authorization: base64({{"username":"","password":""}})" in this request'
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            #ui.label(error_message).classes("text-h5 text-red-500")
            return False, error_message, currentFuncName(), {"response_code":401, "buffer":None, "media_type":None, "filename":None}
            #return 
        
        client_auth_token = client_headers["authorization"]

        if DEBUG: print("client_auth_token", client_auth_token)
        ##############################################
        # валидируем токен клиента он должен быть base64, в котором json в виде текста
        ##############################################
        client_auth_token_validation_result = client_auth_token_validation(client_auth_token, current_state)
        if client_auth_token_validation_result[0] == False:
            error_message = client_auth_token_validation_result[1]
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            #ui.label(error_message).classes("text-h5 text-red-500")
            return False, error_message, currentFuncName(), {"response_code":400, "buffer":None, "media_type":None, "filename":None}
            #return
        
        client_auth_token_dict = client_auth_token_validation_result[3]

        if DEBUG: print("client_auth_token_dict", client_auth_token_dict)
        ##############################################
        # получаем данные о пользователе
        ##############################################
        from_db_user = db_get_user(client_auth_token_dict, current_state)
        if DEBUG: print("from_db_user", from_db_user)

        if from_db_user[0] == False:
            error_message = f"api login {client_auth_token_dict['username']} not in db"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, "auth error", currentFuncName(), {"response_code":401, "buffer":None, "media_type":None, "filename":None}
            #ui.label(error_message).classes("text-h5 text-red-500")
            #return
        
        # активность УЗ пользователя
        if from_db_user[3][0] == 0:
            # попытка логина из заблокированной УЗ
            error_message = f"disabled account {client_auth_token_dict['username']} api login attempt"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, "auth error", currentFuncName(), {"response_code":401, "buffer":None, "media_type":None, "filename":None}
            #ui.label(error_message).classes("text-h5 text-red-500")
            #return
        
        ##############################################
        # пробуем залогиниться
        ##############################################

        from_db_user_password = from_db_user[3][2]

        if isinstance(from_db_user_password, str):
            from_db_user_password = from_db_user_password.encode('utf-8')

        if not bcrypt.checkpw(client_auth_token_dict["password"].encode('utf-8'), from_db_user_password):
            error_message = f"unsuccessful api login {client_auth_token_dict['username']}"
            #logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            return False, "auth error", currentFuncName(), {"response_code":401, "buffer":None, "media_type":None, "filename":None}
            #return
        
        logger_log(syslog.LOG_DEBUG, get_log_message(f"successful api login {client_auth_token_dict['username']}", currentFuncName(), current_state))
        current_state["username"] = client_auth_token_dict["username"]
        ##############################################
        # получаем роли
        ##############################################
        from_db_user_roles = from_db_user[3][3]
        if check_json_correct(from_db_user_roles) == False:
            error_message = f"incorrect json from_db_user_roles for user {client_auth_token_dict['username']}"
            #logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {"response_code":500, "buffer":None, "media_type":None, "filename":None}
            #return
        
        user_roles = json.loads(from_db_user_roles)
        if DEBUG: print("user_roles", user_roles)
        ##############################################
        # получаем сценарий из бд по имени
        ##############################################
        db_get_scenario_by_name_result = db_get_scenario_by_name(scenario_name, current_state)
        if db_get_scenario_by_name_result[0] == False:
            error_message = f"get scenario by name error: {db_get_scenario_by_name_result[1]}"
            #logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {"response_code":400, "buffer":None, "media_type":None, "filename":None}
            #return
        
        scenario_dict = db_get_scenario_by_name_result[3]
        if DEBUG: print("scenario_dict", scenario_dict)
        #######################################
        # получаем разрешенные роли для сценария дл проверки прав доступа
        #######################################

        allow_flag = False
        
        if "fullmaster" in user_roles:
            allow_flag = True
        for user_role in user_roles:
            if user_role in scenario_dict["roles"]:
                allow_flag = True
                break
        
        if allow_flag == False:
            error_message = f"you do not have permission to execute this scenario"
            #logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {"response_code":401, "buffer":None, "media_type":None, "filename":None}
            #return
        ##############################################
        # процедура запуска сценария
        ##############################################
        need_scenario_notify = True
        run_scenario_result = run_scenario(user_roles, scenario_name, json.dumps(scenario_dict["json"]), parameters, need_scenario_notify, "", current_state)
        if run_scenario_result[0] == False:
            error_message = f"scenario launch error: {run_scenario_result[1]}"
            logger_log(syslog.LOG_DEBUG, get_log_message(error_message, currentFuncName(), current_state))
            #ui.label(error_message).classes("text-h5 text-red-500")
            return False, error_message, currentFuncName(), {"response_code":400, "buffer":None, "media_type":None, "filename":None}
            #return
        
        scenario_session_id = run_scenario_result[3]

        if DEBUG: print("scenario_dict", scenario_session_id)
        ##############################################
        # ожидание выполнения
        ##############################################
        waiting_for_scenario_execution_result = waiting_for_scenario_execution(10000, scenario_session_id, current_state)
        if waiting_for_scenario_execution_result[0] == False:
            error_message = f"scenario execution error: {waiting_for_scenario_execution_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            #ui.label(error_message).classes("text-h5 text-red-500")
            return False, error_message, currentFuncName(), {"response_code":500, "buffer":None, "media_type":None, "filename":None}
            #return
        
        scenario_execution_dict = waiting_for_scenario_execution_result[3]
        if DEBUG: print("scenario_execution_dict", scenario_execution_dict)
        ##############################################
        # получение результата из хранилища
        ##############################################
        scenarios_data = get_scenarios_data_from_storage(scenario_execution_dict, current_state)
        if DEBUG: print("scenarios_data", scenarios_data)
        ##############################################
        # формирование вывода согласно output_type и вывод
        ##############################################
        #небольшая переконвертация

        for_table_result = {}
        for task_name in scenarios_data.keys():
            #for_table_result[task_name] = scenarios_data[task_name]["data"]
            for_table_result[scenarios_data[task_name]["data_name"]] = scenarios_data[task_name]["data"]

        if output_type == "xlsx":
            buffer = scenario_export_to_xlsx(for_table_result)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"report_{scenario_session_id.replace(':', '_')}.xlsx"
            logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), {"response_code":200, "buffer":buffer, "media_type":media_type, "filename":filename}
        if output_type == "csvzip":
            buffer = scenario_export_to_zip_csv(for_table_result)
            media_type = "application/zip"
            filename = f"report_{scenario_session_id.replace(':', '_')}.csv.zip"
            logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), {"response_code":200, "buffer":buffer, "media_type":media_type, "filename":filename}
        if output_type == "jsonzip":
            buffer = scenario_export_to_zip_json(scenarios_data)
            media_type = "application/zip"
            filename = f"report_{scenario_session_id.replace(':', '_')}.json.zip"
            logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), {"response_code":200, "buffer":buffer, "media_type":media_type, "filename":filename}
        if output_type == "json":
            buffer = scenario_export_to_raw_json(scenarios_data)
            media_type = "application/json"
            filename = f"report_{scenario_session_id.replace(':', '_')}.json"
            logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
            return True, "OK", currentFuncName(), {"response_code":200, "buffer":buffer, "media_type":media_type, "filename":filename}
            #return buffer, media_type, filename
    except BaseException as e:
        error_message = f"{str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {"response_code":500, "buffer":None, "media_type":None, "filename":None}
    



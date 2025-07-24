import json
import ipaddress
import re
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.database.users import db_get_user
from app.database.access_networks import db_get_access_networks
from app.database.keys import db_get_key
from typing import Tuple, List, Dict, Optional
import base64
from app.crptgrphy import decrypt

REGEX_PASSWORD_RULE = r"^(?=.*[0-9])(?=.*[0-9])(?=.*[!@#$%^&*:.>\/<,;+?~–}{)(\]\[])(?=.*[a-z])(?=.*[A-Z])[0-9a-zA-Z!@#$%^&*:.>\/<,;+?~–}{)(\]\[]{17,}$"
REGEX_USERNAME_RULE = r"^[0-9a-zA-Z._-]{3,}$"
REGEX_ITEMNAME_RULE = r"^[0-9a-zA-Z._\]\[\s/-]{3,}$"
REGEX_COMMENT_RULE = r"^[:/0-9a-zA-Zа-яА-Я.\s_-]*$"

def check_json_correct(text):
    try:
        json.loads(text)
        return True
    except BaseException as e:
        return False

def check_regex_rule(password, password_rule):
    search = re.search(password_rule, password)
    if search:
        return True
    else:
        return False

def check_ip_in_whitelist(from_db_access_networks, address, current_state):
    try:
        for network in from_db_access_networks:
            if network[1] != 0:
                if ipaddress.ip_address(address) in ipaddress.ip_network(network[0]):
                    return True
        return False
    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False

def check_current_user_status(current_state):
    current_user_is_active = False
    current_users_roles = []
    current_user_with_allowed_ip = False
    # получаем данные по пользователю из БД
    db_get_user_result = db_get_user({"username":current_state["username"]}, current_state)
    # данные из БД по пользователю были получены корректно?
    if db_get_user_result[0] == False:
        logger_log(syslog.LOG_ERR, get_log_message("db_get_user_result data is unavailable", currentFuncName(), current_state))
        return current_user_is_active, current_users_roles, current_user_with_allowed_ip, db_get_user_result
    # пользователь не заблокирован?
    if db_get_user_result[3][0] == 0:
        logger_log(syslog.LOG_ALERT, get_log_message("disabled account working attempt", currentFuncName(), current_state))
        return current_user_is_active, current_users_roles, current_user_with_allowed_ip, db_get_user_result
    # пользователь активен
    current_user_is_active = True
    # забираем роли пользователя
    current_users_roles_raw = db_get_user_result[3][3]

    # пытаемся собрать лист ролей
    if check_json_correct(current_users_roles_raw) == False:
        logger_log(syslog.LOG_ERR, get_log_message("error with json.loads(current_users_roles_raw)", currentFuncName(), current_state))
    current_users_roles = json.loads(current_users_roles_raw)    

    # получаем разрешённые сети из БД
    from_db_access_networks = db_get_access_networks(current_state)
    # данные из БД по разрешённым адресам получены корректно?
    if from_db_access_networks[0] == False:
        logger_log(syslog.LOG_ERR, get_log_message(f"from_db_access_networks error: {from_db_access_networks[1]}", currentFuncName(), current_state))
        return current_user_is_active, current_users_roles, current_user_with_allowed_ip, db_get_user_result
    # проверяем адрес пользователя на вхождение в разрешённые сети
    if check_ip_in_whitelist(from_db_access_networks[3], current_state["client_ip_address"], current_state) == False:
        logger_log(syslog.LOG_ERR, get_log_message("client address is not in access networks", currentFuncName(), current_state))
        return current_user_is_active, current_users_roles, current_user_with_allowed_ip, db_get_user_result
    # пользователь работает с разрешённого ip
    current_user_with_allowed_ip = True
    
    return current_user_is_active, current_users_roles, current_user_with_allowed_ip, db_get_user_result

def scenario_validator(with_task_id: bool, scenario: dict, current_state: dict) -> Tuple[bool, str, str, None]:
    # Иногда бывает так, что при отладке запускаются таски с пустым сценарием, мы должны это учитывать

    if "empty" in scenario:
        if isinstance(scenario["empty"], bool):
            if scenario["empty"] == True:
                return True, "OK for empty scenario", currentFuncName(), None

    # тут мы проверим валидность json сценария, наличие нужных нод и полей
    # scenario должен быть dict
    #     Вот пример json сценария:
    # {
    # 	"steps":[
    # 		{
    #             "step_name":"Имя шага из  таблицы steps",
    #             "data_name":"Уникальный идентификатор данных (имя таблицы) в рамках сценария",
    #             "current_task_id":"uuid4, появляется только в момент исполнения",
    #             "show": True
    #         },
    #         {
    #             "step_name":"Имя другого шага из  таблицы steps",
    #             "show": False
    #         }
    # 	],
    # 	"conjoined_parameters":[
    # 		"ip_address":[
    # 			"step1:ip_address", "step2:ip_address"
    # 		]
    # 	],
    # 	"description":""
    # }


    if "steps" not in scenario:
        error_message = "steps not in scenario"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    if isinstance(scenario["steps"], list) == False:
        error_message = "steps is not a list"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    for i, step in enumerate(scenario["steps"]):
        if "step_name" not in step:
            error_message = f"step_name not in step {i}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if isinstance(step["step_name"], str) == False:
            error_message = f"step_name is not a str in step {i}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if "data_name" not in step:
            error_message = f"data_name not in step {i}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if isinstance(step["data_name"], str) == False:
            error_message = f"data_name is not a str in step {i}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if with_task_id == True:
            if "current_task_id" not in step:
                error_message = f"current_task_id not in step {i}"
                logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            if isinstance(step["current_task_id"], str) == False:
                error_message = f"current_task_id is not a str in step {i}"
                logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            # доп проверка на uuid?
        if "show" not in step:
            error_message = f"show not in step {i}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if isinstance(step["show"], bool) == False:
            error_message = f"show is not a bool in step {i}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
    
    if "conjoined_parameters" in scenario:
        # conjoined_parameters не является обязательной нодой, но если она есть, то нужно проверить её корректность
        if isinstance(scenario["conjoined_parameters"], dict) == False:
            error_message = "conjoined_parameters is not a dict"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        for conj_parameter in scenario["conjoined_parameters"].keys():
            if isinstance(scenario["conjoined_parameters"][conj_parameter], list) == False:
                error_message = "conj_parameter is not a list"
                logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            for conj_parameter_candidate in scenario["conjoined_parameters"][conj_parameter]:
                if isinstance(conj_parameter_candidate, str) == False:
                    error_message = "conj_parameter_candidate is not a str"
                    logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None
                # for parameter in conj_parameter_dict[conj_parameter]:
                #     if isinstance(parameter, str) == False:
                #         error_message = f"parameter for {conj_parameter} is not a str"
                #         logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                #         return False, error_message, currentFuncName(), None
    return True, "OK", currentFuncName(), None

def step_validator(step: dict, current_state: dict) -> Tuple[bool, str, str, None]:
    # функция проверяет наличие основных полей в шаге, чтобы не пихнулась совсем какая-то дичь
    if "source_function" not in step:
        error_message = "source_function not in step"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    if "input_parameters" not in step:
        error_message = "input_parameters not in step"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    if isinstance(step["input_parameters"], dict) == False:
        error_message = "input_parameters is not a dict"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    if "query" not in step:
        error_message = "query not in step"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    return True, "OK", currentFuncName(), None

def client_auth_token_validation(client_auth_token: str, current_state: dict) -> Tuple[bool, str, str, Dict]:
    try:
        if not client_auth_token == base64.b64encode(base64.b64decode(client_auth_token)).decode("utf-8"):
            error_message = "base64 check error"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        unbase64_client_auth_token = base64.b64decode(client_auth_token).decode("utf-8")

        if check_json_correct(unbase64_client_auth_token) == False:
            error_message = "unbase64 token is not a valid json"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        client_auth_token_dict = json.loads(unbase64_client_auth_token)

        if "username" not in client_auth_token_dict:
            error_message = "username not in client_auth_token_dict"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if "password" not in client_auth_token_dict:
            error_message = "password not in client_auth_token_dict"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(client_auth_token_dict["username"], REGEX_USERNAME_RULE) == False:
            error_message = "incorrect username in client_auth_token_dict"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        # if check_regex_rule(client_auth_token_dict["password"], REGEX_PASSWORD_RULE) == False:
        #     error_message = "incorrect password in client_auth_token_dict"
        #     logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        #     return False, error_message, currentFuncName(), None
        
        return True, "OK", currentFuncName(), client_auth_token_dict

    except BaseException as e:
        error_message = f"base exception error: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

def client_auth_token_test(client_auth_token_dict: dict, current_state: dict) -> Tuple[bool, str, str, Dict]:
    """Тут сверка токена пользователя с данными в БД"""

    ###############################################
    # сначала делаем запрос в БД по данным system и account
    ###############################################

    db_get_key_result = db_get_key(client_auth_token_dict, current_state)
    if db_get_key_result[0] == False:
        error_message = db_get_key_result[1]
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    db_key = db_get_key_result[3][2]

    ###############################################
    # расшифровываем из бд 
    ###############################################

    decrypted_db_key = decrypt(current_state["master_key"], db_key)

    ###############################################
    # тестируем секрет 
    ###############################################
    if client_auth_token_dict["key"] == decrypted_db_key:
        logger_log(syslog.LOG_DEBUG, get_log_message(f"successful api login {client_auth_token_dict["system"]}:{client_auth_token_dict["account"]}", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), current_state
    else:
        error_message = f"unsuccessful api login {client_auth_token_dict["system"]}:{client_auth_token_dict["account"]}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), current_state
    
def scheduler_jobs_validator(jobs: list, current_state: dict) -> Tuple[bool, str, str, List]:
    try:
        for job in jobs:
            if check_json_correct(job["json"]) == False:
                job["valid"] = False
                continue
            job["json"] = json.loads(job["json"])

            if "scenario_name" not in job["json"]:
                job["valid"] = False
                continue

            if "parameters" not in job["json"]:
                job["valid"] = False
                continue
            
            if "actions" not in job["json"]:
                job["valid"] = False
                continue

            job["valid"] = True
        return True, "OK", currentFuncName(), jobs

    except BaseException as e:
        error_message = f"base exception error: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []

def validate_scenario_input_fields(scenario_name: str, roles: List[str], json_data: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    if check_regex_rule(scenario_name, REGEX_ITEMNAME_RULE) == False:
        error_message = f"wrong username"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    for role in roles:
        if check_regex_rule(role, REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong role"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
    if check_json_correct(json_data) == False:
        error_message = f"wrong json"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

    return True, "OK", currentFuncName(), None

def validate_data_for_scenario_update(data, current_state):
        # data = {
        #     "scenario_original_name":scenario["scenario_name"],
        #     "scenario_new_name": scenario_name_input.value,
        #     "roles": new_roles,
        #     "json": json_input.value
        # }
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        ##########################################
        # тут у нас вводимые пользователем данные, надо их проверить
        ##########################################
        if "scenario_new_name" not in data:
            error_message = "scenario_new_name is not in data"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        if isinstance(data["scenario_new_name"] ,str) == False:
            error_message = "scenario_new_name is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(data["scenario_new_name"], REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong scenario_new_name"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        #######
        if "scenario_original_name" not in data:
            error_message = "scenario_original_name is not in data"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        if isinstance(data["scenario_original_name"] ,str) == False:
            error_message = "scenario_original_name is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(data["scenario_original_name"], REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong scenario_original_name"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        #######
        if isinstance(data["roles"] ,str) == False:
            error_message = "roles is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if check_json_correct(data["roles"]) == False:
            error_message = "roles is not a correct json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if isinstance(json.loads(data["roles"]),list) == False:
            error_message = "roles is not a list in json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        for role in json.loads(data["roles"]):
            if check_regex_rule(role, REGEX_ITEMNAME_RULE) == False:
                error_message = f"wrong role"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
        #####
        if isinstance(data["json"] ,str) == False:
            error_message = "json is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if check_json_correct(data["json"]) == False:
            error_message = "json is not a correct json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if isinstance(json.loads(data["json"]),dict) == False:
            error_message = "json is not a dict in json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None

    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None
    
def validate_data_for_scenario_insert(data, current_state):
        # data = {
        #     "scenario_new_name": scenario_name_input.value,
        #     "roles": new_roles,
        #     "json": json_input.value
        # }
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    try:
        ##########################################
        # тут у нас вводимые пользователем данные, надо их проверить
        ##########################################
        if "scenario_new_name" not in data:
            error_message = "scenario_new_name is not in data"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        if isinstance(data["scenario_new_name"] ,str) == False:
            error_message = "scenario_new_name is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(data["scenario_new_name"], REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong scenario_new_name"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        #######
        #######
        if isinstance(data["roles"] ,str) == False:
            error_message = "roles is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if check_json_correct(data["roles"]) == False:
            error_message = "roles is not a correct json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if isinstance(json.loads(data["roles"]),list) == False:
            error_message = "roles is not a list in json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        for role in json.loads(data["roles"]):
            if check_regex_rule(role, REGEX_ITEMNAME_RULE) == False:
                error_message = f"wrong role"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
        #####
        if isinstance(data["json"] ,str) == False:
            error_message = "json is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if check_json_correct(data["json"]) == False:
            error_message = "json is not a correct json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if isinstance(json.loads(data["json"]),dict) == False:
            error_message = "json is not a dict in json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None

    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def validate_data_for_fetch_scenarios(scenario, current_state):
    """функция валидирует данные, получаемые из БД (таблица scenarios). на случай, если произвели замену данных прямо в базе"""
    try:
        if 'scenario_name' not in scenario:
            error_message = "scenario_name is not in scenario"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        if isinstance(scenario['scenario_name'] ,str) == False:
            error_message = "scenario_name is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(scenario['scenario_name'], REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong scenario_name"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        #####
        if 'author' not in scenario:
            error_message = f"author is not in scenario {scenario['scenario_name']}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        if isinstance(scenario['author'] ,str) == False:
            error_message = f"author is not a string in scenario {scenario['scenario_name']}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(scenario['author'], REGEX_USERNAME_RULE) == False:
            error_message = f"wrong author in scenario {scenario['scenario_name']}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        #######
        if isinstance(scenario["roles"] ,str) == False:
            error_message = f"roles in scenario {scenario['scenario_name']} is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if check_json_correct(scenario["roles"]) == False:
            error_message = f"roles in scenario {scenario['scenario_name']} is not a correct json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        if isinstance(json.loads(scenario["roles"]),list) == False:
            error_message = f"roles in scenario {scenario['scenario_name']} is not a list in json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        for role in json.loads(scenario["roles"]):
            if check_regex_rule(role, REGEX_ITEMNAME_RULE) == False:
                error_message = f"wrong role in scenario {scenario['scenario_name']}"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
        ####
        if isinstance(scenario["json"],str) == False:
            error_message = f"json in scenario {scenario['scenario_name']} is not a string"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_json_correct(scenario["json"]) == False:
            error_message = f"json in scenario {scenario['scenario_name']} is not a valid json representation"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), None
        
    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None

def raw_login_validation(raw_login: str, current_state: dict):
    try:
        if check_regex_rule(raw_login, REGEX_USERNAME_RULE) == False:
            error_message = f"wrong raw login"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
def validate_key_fields(key_list: list, system: str, account: str, key: str, comment: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    try:
        if check_regex_rule(system, REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong system"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(account, REGEX_USERNAME_RULE) == False:
            error_message = f"wrong account"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if not key:
            error_message = f"empty key"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(comment, REGEX_COMMENT_RULE) == False:
            error_message = f"wrong comment"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if f"{system}&{account}" in key_list:
            error_message = f"key already exests"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
def validate_comment(comment: str, current_state: Dict) -> Tuple[bool, str, str, None]:
    try:
        if check_regex_rule(comment, REGEX_COMMENT_RULE) == False:
            error_message = f"wrong account"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

def validate_new_username(new_username: str, current_state: dict) -> Tuple[bool, str, str, None]:
    try:
        if check_regex_rule(new_username, REGEX_USERNAME_RULE) == False:
            error_message = f"wrong username (must {REGEX_USERNAME_RULE})"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
def validate_new_password(new_user_password: str, current_state: dict) -> Tuple[bool, str, str, None]:
    try:
        if check_regex_rule(new_user_password, REGEX_PASSWORD_RULE) == False:
            error_message = f"wrong password (must {REGEX_PASSWORD_RULE})"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
def validate_itemname(new_user_password: str, current_state: dict) -> Tuple[bool, str, str, None]:
    try:
        if check_regex_rule(new_user_password, REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong password (must {REGEX_ITEMNAME_RULE})"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
def validate_new_roles(new_roles: list, current_state: dict) -> Tuple[bool, str, str, None]:
    try:
        for role in new_roles:
            if check_regex_rule(role, REGEX_ITEMNAME_RULE) == False:
                error_message = f"wrong roles (must {REGEX_ITEMNAME_RULE} for each role)"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None

        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None


#def validate_user_creation(new_username: str, new_user_password: str, roles_data: str, json_string: str, current_state: dict) -> Tuple[bool, str, str, None]:

def validate_step_fields(stepname: str, sourcename: str, sourcetype: str, roles: List[str], json_data: str, sources: List[Dict], current_state: Dict) -> Tuple[bool, str, str, None]:
    try:
        if not stepname or not sourcename or not sourcetype or not json_data:
            return False, "All fields must not be empty", currentFuncName(), None
        
        if check_regex_rule(stepname, REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong stepname (must {REGEX_ITEMNAME_RULE})"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(sourcename, REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong sourcename (must {REGEX_ITEMNAME_RULE})"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if check_regex_rule(sourcetype, REGEX_ITEMNAME_RULE) == False:
            error_message = f"wrong sourcetype (must {REGEX_ITEMNAME_RULE})"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        for role in roles:
            if check_regex_rule(role, REGEX_ITEMNAME_RULE) == False:
                error_message = f"wrong roles (must {REGEX_ITEMNAME_RULE} for each role)"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None

        if check_json_correct(json_data) == False:
            error_message = f"wrong json"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        # Проверка sourcename и sourcetype
        source = next((s for s in sources if s["sourcename"] == sourcename), None)
        if not source:
            return False, f"Source '{sourcename}' does not exist", currentFuncName(), None
        if source["type"] != sourcetype:
            return False, f"Source type '{sourcetype}' does not match source '{sourcename}' type '{source['type']}'", currentFuncName(), None
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
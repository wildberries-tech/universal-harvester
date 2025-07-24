import ipaddress
from datetime import datetime, timezone
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
import json
from app.validation import *
from typing import Tuple, List, Dict, Optional
import copy

TYPE_MAP = {
    "string":{
        "example":"foo_bar",
        "autofill":{},
        "required_fields":{
            "max_length":1024
        },
        "validator": lambda x: str(x),
        "filler":"please fill me"
    },
    "ip_address":{
        "example":"127.0.0.1",
        "autofill":{
            "client_ip":{"function":lambda x: str(x[0]),"args":["client_ip"]}
        },
        "validator": lambda x: ipaddress.ip_address(x),
        "filler":"please fill me"
    },
    "datetime":{
        "example":"2025-01-01T00:00:00.000Z",
        "required_fields":{
            "format":"%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "autofill":{
            "now":{"function":lambda x: datetime.now(timezone.utc).strftime(x[0]),"args":["format"]}
        },
        "validator":{"function":lambda x: datetime.strptime(x[0], x[1]),"args":["value","format"]},
        "filler":"please fill me"
    },
    "integer":{
        "example":12345,
        "autofill":{},
        "validator": lambda x: int(x),
        "filler":0
    },
    "float":{
        "example":1.2345,
        "autofill":{},
        "validator": lambda x: float(x),
        "filler":0.0
    },
    "boolean":{
        "example":True,
        "autofill":{},
        "validator": lambda x: bool(x),
        "filler":False
    },
    "list":{
        "example":[1,"2"],
        "autofill":{},
        "validator": lambda x: list(x),
        "filler":["please fill me"]
    },
    "dict":{
        "example":{1:"2"},
        "autofill":{},
        "validator": lambda x: dict(x),
        "filler":{"please":"fill me"}
    }
}
def step_parameter_validator(step_parameter_name, step_parameter_json, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
    # это должен быть dict
    if not isinstance(step_parameter_json, dict):
        error_message = f'{step_parameter_name} in input_parameters is not a dict'
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
        
    # должно быть поле type
    if "type" not in step_parameter_json:
        error_message = f'type field value is not in {step_parameter_name} parameter'
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

    # должно быть поле обязательности параметра
    if "required" not in step_parameter_json:
        error_message = f'required field is not in {step_parameter_name} parameter'
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

    # поле обязательно параметра должно быть boolean
    if not isinstance(step_parameter_json["required"], bool):
        error_message = f'required field is not a bool in {step_parameter_name} parameter'
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
        
    # проверяем, а допустимый ли у нас type
    if step_parameter_json["type"] not in TYPE_MAP:
        error_message = f'type field is not in TYPE_MAP'
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

    # проверяем наличие необходимых полей
    
    if "required_fields" in TYPE_MAP[step_parameter_json["type"]]:
        if not isinstance(TYPE_MAP[step_parameter_json["type"]]["required_fields"], dict):
            error_message = f'required_fields in TYPE_MAP {step_parameter_json["type"]} is not a dict'
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        for required_field in TYPE_MAP[step_parameter_json["type"]]["required_fields"].keys():
            if required_field not in step_parameter_json:
                error_message = f'required_field {required_field} is not in {step_parameter_name} parameter'
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            if not isinstance(step_parameter_json[required_field], type(TYPE_MAP[step_parameter_json["type"]]["required_fields"][required_field])):
                error_message = f'wrong variable type of {required_field} in {step_parameter_name} parameter'
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None

    # если есть поле default, то оно должно быть dict и содержать ссылку на существующее автозаполнение
    if "default" in step_parameter_json:
        # какими типами не может быть default
        # if isinstance(step_parameter_json["default"], dict):
        #     error_message = f'default field is a dict in {step_parameter_name} parameter'
        #     logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        #     return False, error_message, currentFuncName(), None
        # if isinstance(step_parameter_json["default"], list):
        #     error_message = f'default field is a list in {step_parameter_name} parameter'
        #     logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        #     return False, error_message, currentFuncName(), None
        # if isinstance(step_parameter_json["default"], bool):
        #     return False, f'default field is a bool in {step_parameter_name} parameter', currentFuncName(), None
        if "autofill" in TYPE_MAP[step_parameter_json["type"]]:
            if not isinstance(TYPE_MAP[step_parameter_json["type"]]["autofill"], dict):
                error_message = f'autofill in TYPE_MAP {step_parameter_json["type"]} is not a dict'
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            # if step_parameter_json["default"] in TYPE_MAP[step_parameter_json["type"]]["autofill"]:
            #     pass
        else:
            if not isinstance(step_parameter_json["default"], type(TYPE_MAP[step_parameter_json["type"]]["example"])):
                error_message = f'wrong default variable type in {step_parameter_name} parameter'
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
        
    # готово
    logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
    return True, f'OK', currentFuncName(), None


def get_parameters_from_step(mode: str, step_name: str, step_json, scenario_json, step_num, current_state: dict) -> Tuple[bool, str, str, dict]:
    logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
    # mode отвечает за правило генерирования имени параметров "simple" -- генерируем по исходному названию
    # "with_step_name" -- генерируем с именени шага

    #################################################
    # проверка входных данных
    #################################################
    if isinstance(step_json, dict) == False:
        if check_json_correct(step_json) == False:
            error_message = f"step_json is not valid JSON"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(),{}
        current_json = json.loads(step_json)
    else:
        current_json = copy.deepcopy(step_json)

    if isinstance(scenario_json, dict) == False:
        if check_json_correct(scenario_json) == False:
            error_message = f"scenario_json is not valid JSON"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(),{}
        current_scenario_json = json.loads(scenario_json)
    else:
        current_scenario_json = scenario_json

    default_parameters_replacement = {}
    # if "default_parameters_replacement" in current_scenario_json:
    #     if isinstance(current_scenario_json["default_parameters_replacement"], dict) == True:
    #         default_parameters_replacement = current_scenario_json["default_parameters_replacement"]
    if "steps" in current_scenario_json:
        if isinstance(current_scenario_json["steps"], list):
            if "default_parameters_replacement" in current_scenario_json["steps"][step_num]:
                if isinstance(current_scenario_json["steps"][step_num]["default_parameters_replacement"], dict) == True:
                    default_parameters_replacement = current_scenario_json["steps"][step_num]["default_parameters_replacement"]

    if "input_parameters" not in current_json:
        error_message = f"there is not input_parameters in current_json"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {}

    if not isinstance(current_json["input_parameters"], dict):
        error_message = f"input_parameters is not dict"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {}

    dummy_step_parameters = {}
    
    for parameter in current_json["input_parameters"].keys():
        # для интерактивного тестирования мы выводим все параметры
        # проверка параметра
        
        step_parameter_validator_result = step_parameter_validator(parameter, current_json["input_parameters"][parameter], current_state)
        if step_parameter_validator_result[0] == False:
            error_message = f"step_parameter_validator_result is false: {step_parameter_validator_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, step_parameter_validator_result[2], {}
        # если есть default, заполняем с помощью него
        if "default" in current_json["input_parameters"][parameter]:
            # перезаписываем default на тот, что в сценарии
            # if f"{step_num}:{parameter}" in default_parameters_replacement:
            #     current_json["input_parameters"][parameter]["default"] = default_parameters_replacement[f"{step_num}:{parameter}"]
            if parameter in default_parameters_replacement:
                current_json["input_parameters"][parameter]["default"] = default_parameters_replacement[parameter]

            
            if current_json["input_parameters"][parameter]["type"] not in ["list", "dict"]: # данные типы данных unhashable, для них автозаполнение пока не работает
                if current_json["input_parameters"][parameter]["default"] in TYPE_MAP[current_json["input_parameters"][parameter]["type"]]["autofill"]:
                    try:
                        autofill_executer = TYPE_MAP[current_json["input_parameters"][parameter]["type"]]["autofill"][current_json["input_parameters"][parameter]["default"]]
                        current_args = []
                        for arg in autofill_executer["args"]:
                            if arg == "client_ip":
                                current_args.append(current_state["client_ip_address"])
                            elif arg == "format":
                                current_args.append(current_json["input_parameters"][parameter]["format"])

                            if mode == "with_step_name":
                                dummy_step_parameters[f"{step_name}:{parameter}"] = autofill_executer["function"](current_args)
                            elif mode == "simple":
                                dummy_step_parameters[f"{parameter}"] = autofill_executer["function"](current_args)
                            else:
                                dummy_step_parameters[f"{parameter}"] = autofill_executer["function"](current_args)

                    except BaseException as e:
                        error_message = f"autofill fail: {str(e)}"
                        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), {}
                else:
                    if mode == "with_step_name":
                        dummy_step_parameters[f"{step_name}:{parameter}"] = current_json["input_parameters"][parameter]["default"]
                    elif mode == "simple":
                        dummy_step_parameters[f"{parameter}"] = current_json["input_parameters"][parameter]["default"]
                    else:
                        dummy_step_parameters[f"{parameter}"] = current_json["input_parameters"][parameter]["default"]
            else:
                if mode == "with_step_name":
                    dummy_step_parameters[f"{step_name}:{parameter}"] = current_json["input_parameters"][parameter]["default"]
                elif mode == "simple":
                    dummy_step_parameters[f"{parameter}"] = current_json["input_parameters"][parameter]["default"]
                else:
                    dummy_step_parameters[f"{parameter}"] = current_json["input_parameters"][parameter]["default"]
        else: # если в default нет, то пишем приглашение к заполнению
            if mode == "with_step_name":
                dummy_step_parameters[f"{step_name}:{parameter}"] = TYPE_MAP[current_json["input_parameters"][parameter]["type"]]["filler"]
            elif mode == "simple":
                dummy_step_parameters[f"{parameter}"] = TYPE_MAP[current_json["input_parameters"][parameter]["type"]]["filler"]
            else:
                dummy_step_parameters[f"{parameter}"] = TYPE_MAP[current_json["input_parameters"][parameter]["type"]]["filler"]

    logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
    return True, f'OK', currentFuncName(), dummy_step_parameters

def input_parameter_validator(input_parameters, step, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))
    valid_parameters = {}
    if isinstance(step, dict) == False:
        error_message = 'step is not a dict'
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    if isinstance(input_parameters, dict) == False:
        error_message = 'input_parameters is not a dict'
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

    if "input_parameters" not in step:
        error_message = 'there is not input_parameters in step'
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

    for step_parameter in step["input_parameters"]:
        if step_parameter in input_parameters:
            # нашли нужный параметр
            test_value = input_parameters[step_parameter]
            test_type = step["input_parameters"][step_parameter]["type"]
            test_node = step["input_parameters"][step_parameter]
            
            if test_type == "IPv4":
                try:
                    ipaddress.ip_address(test_value)
                except BaseException as e:
                    error_message = f'parameter {step_parameter} is not a valid ip_address: {str(e)}'
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None
            if test_type == "integer":        
                try:
                    int(test_value)
                except BaseException as e:
                    error_message = f'parameter {step_parameter} is not a valid integer: {str(e)}'
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None
            if test_type == "float":        
                try:
                    float(test_value)
                except BaseException as e:
                    error_message = f'parameter {step_parameter} is not a valid float: {str(e)}'
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None
            if test_type == "boolean":        
                try:
                    bool(test_value)
                except BaseException as e:
                    error_message = f'parameter {step_parameter} is not a valid boolean: {str(e)}'
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None
            if test_type == "datetime":
                try:                
                    datetime.strptime(test_value, test_node["format"])  
                except BaseException as e:
                    error_message = f'parameter {step_parameter} is not a valid datetime: {str(e)}'
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None
            if test_type == "string":        
                try:
                    str(test_value)
                except BaseException as e:
                    error_message = f'parameter {step_parameter} is not a valid string: {str(e)}'
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None
                try:
                    if len(test_value) > test_node["max_length"]:
                        error_message = f'len parameter {step_parameter} > max_length'
                        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), None
                except BaseException as e:
                    error_message = f'test len error with {step_parameter}: {str(e)}'
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None
            
            valid_parameters[step_parameter] = test_value
        else:
            # параметра нет
            if step["input_parameters"][step_parameter]["required"] == True:
                error_message = f'there is not a required parameter {step_parameter}'
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            else:
                if "default" in step["input_parameters"][step_parameter]:
                    if step["input_parameters"][step_parameter]["default"] in TYPE_MAP[step["input_parameters"][step_parameter]["type"]]["autofill"]:
                        try:
                            autofill_executer = TYPE_MAP[step["input_parameters"][step_parameter]["type"]]["autofill"][step["input_parameters"][step_parameter]["default"]]
                            current_args = []
                            for arg in autofill_executer["args"]:
                                if arg == "client_ip":
                                    current_args.append(current_state["client_ip_address"])
                                elif arg == "format":
                                    current_args.append(step["input_parameters"][step_parameter]["format"])

                                valid_parameters[step_parameter] = autofill_executer["function"](current_args)

                        except BaseException as e:
                            error_message = f'autofill fail: {str(e)}'
                            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                            return False, error_message, currentFuncName(), None
                    else:
                        valid_parameters[step_parameter] = step["input_parameters"][step_parameter]["default"]
                else:
                    error_message = f'there is not a default value for parameter {step_parameter}'
                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), None

    logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))
    return True, f'OK', currentFuncName(), valid_parameters



import requests
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.engine.engine import get_key

def send_telegram_notify(bot_token, chat_id, message_text, current_state):
    try:
        # блок для получения chat_id
        # блок для получения для внесения нового chat_id можно воспользоваться данной функцией
        # пусть сначала пользователь напишет боту
        # url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        # print(requests.get(url).json())

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message_text}"
        response = requests.get(url)#.json()

        if response.status_code < 200 or response.status_code >=300:
            # ошибка, не можем получить себя
            error_message = f"Cannot GET to telegram server"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        response_json = response.json()
        
        if "ok" not in response_json:
            error_message = f"ok node is not in telegram response json"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        if response_json["ok"] != True:
            error_message = f"ok is not true in telegram response json"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

    except BaseException as e:
        error_message = f"Generic exeption: {e}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    return True, "OK", currentFuncName(), None

def notify_telegram_proc(user_telegram_json_node, notify_text, current_state):
    if "enabled" not in user_telegram_json_node:
        logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации telegram: отсутствует флаг enabled", currentFuncName(), current_state))
        return
    if user_telegram_json_node["enabled"]:
        if "chat_id" not in user_telegram_json_node:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации telegram: отсутствует строка chat_id", currentFuncName(), current_state))
            return
        if "key" not in user_telegram_json_node:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации telegram: отсутствует нода key", currentFuncName(), current_state))
            return
        get_key_result = get_key(user_telegram_json_node["key"], current_state)
        if get_key_result[0] == False:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка получения ключей для нотификации telegram: {get_key_result[1]}", currentFuncName(), current_state))
            return
        key = get_key_result[3]

        send_telegram_notify_result = send_telegram_notify(
                            key, 
                            user_telegram_json_node["chat_id"], 
                            notify_text, 
                            current_state)
        if send_telegram_notify_result[0] == False:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации telegram: {send_telegram_notify_result[1]}", currentFuncName(), current_state))
            return
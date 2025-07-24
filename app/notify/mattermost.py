import requests
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.engine.engine import get_key
def send_mattermost_notify(mattermost_host, api_key, target_username, message_text, current_state):
    try:
        ###############################################################
        # Сначала надо получить собственный user id бота в mattermost
        ###############################################################
        response = requests.get("https://"+mattermost_host+"/api/v4/users/me",headers = {'Authorization': f"Bearer {api_key}"})
        if response.status_code < 200 or response.status_code >=300:
            # ошибка, не можем получить себя
            error_message = f"Cannot get bot mattermost account for {mattermost_host}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        bot_id = response.json()["id"]

        ###############################################################
        # Получаем пользователя по его юзернейму (id кому отправляем уведомление)
        ###############################################################
        response = requests.post("https://"+mattermost_host+"/api/v4/users/usernames",headers = {'Authorization': f"Bearer {api_key}",'Content-type': 'content_type_value'}, json = [target_username])
        if response.status_code < 200 or response.status_code >=300:
            # ошибка, не можем получить пользователя
            error_message = f"Cannot get target user mattermost account {target_username} for server {mattermost_host}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        target_user_id = ""
    
        for responsed_user in response.json():
            if responsed_user["username"] == target_username:
                target_user_id = responsed_user["id"]
    
        if target_user_id == "":
            # ошибка, получен не тот пользователь
            error_message = f"Mattermost server username is not equal config username {target_username}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
        ###############################################################
        # создаём приватный канал бот<->пользователь
        ###############################################################
        response = requests.post("https://"+mattermost_host+"/api/v4/channels/direct",headers = {'Authorization': f"Bearer {api_key}",'Content-type': 'content_type_value'}, json = [bot_id, target_user_id])
        if response.status_code < 200 or response.status_code >=300:
            # ошибка создания канала
            error_message = f"Cannot create private bot<->user channel"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
    
        channel_id = response.json()["id"]
    
        # 4. отправка сообщения
        response = requests.post("https://"+mattermost_host+"/api/v4/posts",headers = {'Authorization': f"Bearer {api_key}",'Content-type': 'content_type_value'}, json = {"channel_id":channel_id,"message":message_text})
        if response.status_code < 200 or response.status_code >=300:
            # ошибка отправки
            error_message = f"Cannot send message to user {target_username}"
            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        
    except BaseException as e:
        error_message = f"Generic exeption: {e}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    return True, "OK", currentFuncName(), None
def notify_mattermost_proc(user_mattermost_json_node, notify_text, current_state):
    if "enabled" not in user_mattermost_json_node:
        logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации mattermost: отсутствует флаг enabled", currentFuncName(), current_state))
        return
    if user_mattermost_json_node["enabled"]:
        if "server" not in user_mattermost_json_node:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации mattermost: отсутствует строка server", currentFuncName(), current_state))
            return
        if "username" not in user_mattermost_json_node:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации mattermost: отсутствует строка username", currentFuncName(), current_state))
            return
        if "key" not in user_mattermost_json_node:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации mattermost: отсутствует нода key", currentFuncName(), current_state))
            return
        get_key_result = get_key(user_mattermost_json_node["key"], current_state)
        if get_key_result[0] == False:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка получения ключей для нотификации mattermost: {get_key_result[1]}", currentFuncName(), current_state))
            return
        key = get_key_result[3]

        send_mattermost_notify_result = send_mattermost_notify(
                            user_mattermost_json_node["server"], 
                            key, 
                            user_mattermost_json_node["username"], 
                            notify_text, 
                            current_state)
        if send_mattermost_notify_result[0] == False:
            logger_log(syslog.LOG_ERR, get_log_message(f"Ошибка нотификации mattermost: {send_mattermost_notify_result[1]}", currentFuncName(), current_state))
            return
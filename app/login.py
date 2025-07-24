import uuid
import bcrypt
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.database.users import db_get_user
from app.validation import raw_login_validation

def try_login(input_login, input_pass, current_state):  # local function to avoid passing username and password as arguments
    # cначала получаем текущий список пользователей
    # это можно сделать с локальной копией, но пока что будем обращаться в базу на лету

        
        # client_ip = client.environ['asgi.scope']['client'][0]
        # client_port = client.environ['asgi.scope']['client'][1]
        new_session_id = str(uuid.uuid4())
        
        logger_log(syslog.LOG_DEBUG, get_log_message(f"login start: {input_login}", currentFuncName(), current_state))

        raw_login_validation_result = raw_login_validation(input_login, current_state)
        if raw_login_validation_result[0] == False:
            error_message = f"login is not valid"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName, None
            
        from_db_user = db_get_user({"username":input_login}, current_state)
        if from_db_user[0] == False:
            error_message = f"login {input_login} not in db"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName, None
        
        # активность УЗ пользователя
        if from_db_user[3][0] == 0:
            # попытка логина из заблокированной УЗ
            error_message = f"disabled account {input_login} login attempt"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName, None
        
        from_db_user_password = from_db_user[3][2]

        if isinstance(from_db_user_password, str):
             from_db_user_password = from_db_user_password.encode('utf-8')

        if bcrypt.checkpw(input_pass.encode('utf-8'), from_db_user_password):
            logger_log(syslog.LOG_DEBUG, get_log_message(f"successful login {input_login}", currentFuncName(), current_state))
            # возможна ли тут подмена юзернейма?
            # app.storage.user.update({'username': input_login, 'authenticated': True, 'session_id': NEW_SESSION_ID})
            # ui.navigate.to(app.storage.user.get('referrer_path', '/'))  # go back to where the user wanted to go

            return True, "OK", currentFuncName, {'username': input_login, 'authenticated': True, 'session_id': new_session_id}
        else:
            error_message = "wrong password for login {input_login}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName, None
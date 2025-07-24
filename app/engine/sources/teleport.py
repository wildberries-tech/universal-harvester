# teleport
import subprocess
import pyotp
import pexpect

import datetime
import pandas
import json
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.engine.cache import get_data_from_cache

# функции интеграции с телепортом
# реализовано только подключение с использованием OTP
def teleport_auth(teleport_host, SECRET_TELEPORT, ACCOUNT_TELEPORT, SECRET_TOTP, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
    subprocess.run(
        f"tsh logout --proxy={teleport_host} --user={ACCOUNT_TELEPORT}".split()
    )
    p = pexpect.spawn(
        f"tsh login --proxy={teleport_host} --user {ACCOUNT_TELEPORT} --mfa-mode otp --auth local"
    )

    try:
        expected = f"Enter password for Teleport user {ACCOUNT_TELEPORT}:"
        print("Expecting '{}'", expected)
        p.expect_exact(expected)
    except pexpect.exceptions.TIMEOUT as e:
        error_message = f"Not authorized and could not get password prompt; {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return 0

    password=SECRET_TELEPORT
    
    totp = pyotp.TOTP(SECRET_TOTP)

    p.sendline(password)

    try:
        expected = "Enter an OTP code from a device:"
        #print("Expecting '{}'", expected)
        p.expect_exact(expected)
    except pexpect.exceptions.TIMEOUT:
        error_message = f"Not authorized and could not get OTP prompt; {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return 0

    p.sendline(totp.now())

    try:
        expected = "> Profile URL:"
        #print("Expecting '{}'", expected)
        p.expect_exact(expected)
    except pexpect.exceptions.TIMEOUT:
        error_message = f"Not authorized and did not get successful auth; {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return 0
    
    #print("Authenticated successfully")
    logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
    return 1

def teleport_get_hosts(current_state):
    try:
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
        result = subprocess.run(['/usr/local/bin/tsh', 'ls', '--format=json'], stdout=subprocess.PIPE).stdout.decode('utf-8')
        data = json.loads(result)
        data = pandas.json_normalize(data).to_dict('records')
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return data
    except Exception as e:
        error_message = f"Error loading data from Teleport: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return []

def execute_function_get_hosts_teleport(data_map, source, query, step, parameters, current_state):
    try: 
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))

        current_data = []
        host = source["host"]
        for key in source["key"]:
            if "TOTP" in key["account"]:
                SECRET_TOTP = key["value"]
            else:
                ACCOUNT_TELEPORT = key["account"]
                SECRET_TELEPORT = key["value"]

        # проверяем, можно ли взять данные из локального кеша
        get_data_from_cache_result = get_data_from_cache(step, query["ttl"], current_state)
        if get_data_from_cache_result[0] == True: #!!!!
            logger_log(syslog.LOG_DEBUG, get_log_message("done from cache", currentFuncName(), current_state))
            return True, "ОК from cache", currentFuncName(), get_data_from_cache_result[3]
        #------------
        # сначала логин в телепортио
        try:
            teleport_login_status = teleport_auth(
                host, 
                SECRET_TELEPORT,
                ACCOUNT_TELEPORT, 
                SECRET_TOTP, current_state
            )
        except BaseException as e:
            error_message = f"Any problem with teleport login: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        if teleport_login_status == 0:
            error_message = f"Teleport login faild"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        try:
            current_data = teleport_get_hosts(current_state)
        except BaseException as e:
            error_message = f"Any problem with teleport getting hosts data"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []

        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), current_data
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
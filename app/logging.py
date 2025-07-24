import syslog
import datetime
import sys
import json

LOG_JSON_DUMPS_INDENT = None

# получение текущего времени
currentTimestamp = lambda: datetime.datetime.now().astimezone().isoformat()
# получение названия текущей функции
currentFuncName = lambda n=0: sys._getframe(n + 1).f_code.co_name
# функция генерации сообщения для логирования
def get_log_message(message, function_name, current_state):
    return {
            "application":current_state["app_name"],
            "application_version":current_state["app_version"],
            "main_session_id":current_state["main_session_id"],
            "user_session_id":current_state["user_session_id"],
            "client_ip_address":current_state["client_ip_address"],
            "client_port":current_state["client_port"],
            "username":current_state["username"],
            "message":message,
            "function_name":function_name,
            "event_timestamp":currentTimestamp()
        }


# общая функция логирования, при необходимости позволит поменять механизм логирования в приложении
#https://docs.python.org/3/library/syslog.html
# The module defines the following constants:

# syslog.LOG_EMERG
# syslog.LOG_ALERT
# syslog.LOG_CRIT
# syslog.LOG_ERR
# syslog.LOG_WARNING
# syslog.LOG_NOTICE
# syslog.LOG_INFO
# syslog.LOG_DEBUG
# Priority levels (high to low).

# syslog.LOG_AUTH
# syslog.LOG_AUTHPRIV
# syslog.LOG_CRON
# syslog.LOG_DAEMON
# syslog.LOG_FTP
# syslog.LOG_INSTALL
# syslog.LOG_KERN
# syslog.LOG_LAUNCHD
# syslog.LOG_LPR
# syslog.LOG_MAIL
# syslog.LOG_NETINFO
# syslog.LOG_NEWS
# syslog.LOG_RAS
# syslog.LOG_REMOTEAUTH
# syslog.LOG_SYSLOG
# syslog.LOG_USER
# syslog.LOG_UUCP
# syslog.LOG_LOCAL0
# syslog.LOG_LOCAL1
# syslog.LOG_LOCAL2
# syslog.LOG_LOCAL3
# syslog.LOG_LOCAL4¶
# syslog.LOG_LOCAL5
# syslog.LOG_LOCAL6
# syslog.LOG_LOCAL7
def logger_log(syslog_level, message):
    syslog.syslog(syslog_level, json.dumps(message, indent = LOG_JSON_DUMPS_INDENT, ensure_ascii=False))
    message["syslog_level"] = syslog_level
    # для логирования через docker syslog
    print(json.dumps(message, indent = LOG_JSON_DUMPS_INDENT, ensure_ascii=False))
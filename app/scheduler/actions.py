import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from typing import Tuple, List, Dict, Optional

def action_syslog(log_level, message, current_state: Dict):
    try:
        syslog.syslog(log_level, message)
        return True, "OK", currentFuncName(), None
    except BaseException as e:
        error_message = f"action fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
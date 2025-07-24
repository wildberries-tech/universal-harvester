import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
import pickle
import asyncio
import lzma
import os
import time
import aiofiles
import json

STEP_SUBDIR = "/steps"
SCENARIO_SUBDIR = "/scenarios"
MAX_READ_ITERATIONS = 100

def write_step_to_storage(data, current_state):
    # проверяем, что имеется storage_path
    if "storage_path" not in current_state:
        error_message = "there is not storage_path in current_state"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    # проверяем существование пути
    if os.path.isdir(current_state["storage_path"]) == False:
        # директории нет, пробуем создать
        try:
            os.makedirs(current_state["storage_path"])
        except BaseException as e:
            error_message = f"makedirs error: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
    # тут путь точно существует, проверяем существование поддиректории для шагов
    if os.path.isdir(current_state["storage_path"] + STEP_SUBDIR) == False:
        # поддиректории нет, пробуем создать
        try:
            os.makedirs(current_state["storage_path"] + STEP_SUBDIR)
        except BaseException as e:
            error_message = f"makedirs error (subdir): {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
    # поддиректория существует, можно туда писать
    try:
        output_file_name = f"{current_state["storage_path"]}{STEP_SUBDIR}/{current_state["target_id"]}.pickle.xz"
        with lzma.open(output_file_name, 'wb') as handle:
            #pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
            json_string = json.dumps(data)
            json_bytes = json_string.encode('utf-8')
            handle.write(json_bytes)

        # sync
        os.system(f"sync {current_state["storage_path"]}{STEP_SUBDIR}")
    except BaseException as e:
        error_message = f"write error: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    return True, "OK", currentFuncName(), None

# async def async_read(filename):
#     async with aiofiles.open(filename, 'rb') as f:
#         contents = await f.read()
#         decompressed = lzma.decompress(contents)
#         try:
#             data = json.loads(decompressed)
#         except:
#             try:
#                 data = pickle.loads(decompressed)
#             except:
#                 data = {}
#         # with lzma.open(contents, 'rb') as handle:
#         #     import_data = pickle.load(handle) # import data validation?
#     return data

def simple_read(filename):
    with open(filename, "rb") as f:
        contents = f.read()
        decompressed = lzma.decompress(contents)
        try:
            data = json.loads(decompressed)
        except:
            try:
                data = pickle.loads(decompressed)
            except:
                data = {}
    return data

def read_step_from_storage(data, current_state):
    # проверяем, что имеется storage_path
    if "storage_path" not in current_state:
        error_message = "there is not storage_path in current_state"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    # проверяем существование пути
    if os.path.isdir(current_state["storage_path"]) == False:
        # директории нет, читать нечего
        error_message = "there is not storage_path dir"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    # тут путь точно существует, проверяем существование поддиректории для шагов
    if os.path.isdir(current_state["storage_path"] + STEP_SUBDIR) == False:
        error_message = f"there is not storage_path step subdir"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    
    input_file_name = f"{current_state["storage_path"]}{STEP_SUBDIR}/{data["target_id"]}.pickle.xz"
    # поддиректория существует, можно оттуда читать

    try:
        input_file_name = f"{current_state["storage_path"]}{STEP_SUBDIR}/{data["target_id"]}.pickle.xz"

        # проверям существование файла, возможна долгая дозапись
        # sync
        os.system(f"sync")
        read_iterations = 0
        while not os.path.exists(input_file_name):
            read_iterations = read_iterations + 1
            if read_iterations >= MAX_READ_ITERATIONS:
                error_message = f"MAX_READ_ITERATIONS {MAX_READ_ITERATIONS} overflow"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), None
            time.sleep(1)
        import_data = simple_read(input_file_name)

    except BaseException as e:
        error_message = f"read error: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
    return True, "OK", currentFuncName(), import_data
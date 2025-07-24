from multiprocessing import shared_memory
import syslog
from app.logging import get_log_message, logger_log, currentFuncName

SHARED_MEMORY_LIST_POSITIONS = {
    # ключ доступа к секретам
    "master_key":0,
    # параметры подключения к БД
    "db_conf":1,
    # параметры поиска задачи
    "target_id":2,
    # параметры логирования
    "main_session_id":3,
    "user_session_id":4,
    "client_ip_address":5,
    "client_port":6,
    "username":7,
    "storage_path":8,
    "itself_link":9,
    "engine_path":10
}

def create_shared_memory_block(TARGET_ID, current_state):
    """ Создаёт блок shared_memory для передачи параметров между интерфейсом и движком исполнения (engine)
    
    Применение shared_memory обусловлено безопасностью передачи мастер-ключа таблицы keys для расшифровывания
    кредов источников данных (source) и нотификаторов. Передача происходит через создания шарного объекта в памяти, 
    приёмку объекта движком и его удаление. Мастер-ключ не будет обнаруживаться в логах аудита, но его можно
    забрать после создания объекта и до обработки его движком (доли секунды?). Движок при чтении его сразу же удаляет.

    Порядок параметров указывается в SHARED_MEMORY_LIST_POSITIONS. Для добавления нового передаваемого от интерфейса
    к движку параметра нужно сначала добавить его в ShareableList, а затем позицию ShareableList указать в SHARED_MEMORY_LIST_POSITIONS.
    Таким образом функция-приёмщик данных get_data_from_shared_memory корректно разберёт ShareableList
    """

    try:
        shared_memory_block = shared_memory.ShareableList([
            current_state["master_key"], 
            current_state["db_conf"], 
            TARGET_ID, 
            current_state["main_session_id"], 
            current_state["user_session_id"], 
            current_state["client_ip_address"], 
            current_state["client_port"], 
            current_state["username"],
            current_state["storage_path"],
            current_state["itself_link"],
            current_state["engine_path"]
        ])
        shared_memory_block_name = shared_memory_block.shm.name
        shared_memory_block.shm.close()
        return True, "OK", currentFuncName(), shared_memory_block_name
    except BaseException as e:
        return False, str(e), currentFuncName(), None
    
def get_data_from_shared_memory(shared_memory_name, current_state): # + global    
    """Читает блок shared_memory по имени от интерфейса. Таким образом движок принимает основыне параметры запуска.
    После чтени движок сразу же закрывает блок shared_memory, чтобы он существовал как можно более меньший промежуток времени.
    Чтение ShareableList происходит в порядке, указанном в SHARED_MEMORY_LIST_POSITIONS.

    Результат записывается в блок current_state, который будет использоваться в работе экземпляра движка.
    Проще говоря эта связка функций нужна для +- безопасной передачи current_state.
    """

    try:
        logger_log(syslog.LOG_DEBUG, get_log_message(f"start", currentFuncName(), current_state))

        # получаем доступ к shareable_list
        front_shareable_list = shared_memory.ShareableList(name=shared_memory_name)
        # забираем данные
        for key in SHARED_MEMORY_LIST_POSITIONS.keys():
            current_state[key] = front_shareable_list[SHARED_MEMORY_LIST_POSITIONS[key]]
        # очищаем данные   
        front_shareable_list.shm.close()
        front_shareable_list.shm.unlink()
    except BaseException as e:
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {str(e)}", currentFuncName(),current_state))
        return False, str(e), currentFuncName(), None
        
    logger_log(syslog.LOG_DEBUG, get_log_message(f"done", currentFuncName(), current_state))    
    return True, "OK", currentFuncName(), current_state
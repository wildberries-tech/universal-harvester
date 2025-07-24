from nicegui import ui, run
from functools import partial
import syslog
import pandas as pd
from io import BytesIO
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.database.users import fetch_user_data
from app.database.tasks import db_get_tasks, fetch_tasks, update_task_field, fetch_task_by_id
from app.engine.storage import read_step_from_storage
from typing import Tuple, List, Dict, Optional
from app.database.scenarios import get_scenario_history_line, db_get_scenario_by_name
from app.validation import scenario_validator, check_json_correct
from app.engine.scenarios import get_scenarios_data_from_storage
from app.engine.steps import get_parameters_from_step

from app.engine.engine import get_step_dependency, process_injections
from app.database.steps import fetch_step_by_name
from app.database.sources import db_get_source
import zipfile
import json 
import datetime
import copy


    

def prepare_aggrid_for_result(result: List[Dict]) -> Dict:
    """Подготовка настроек ui.aggrid для отображения результата задачи"""
    if not result or not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
        return {"columnDefs": [], "rowData": []}
    
    # Преобразуем ключи с точками в подчёркивания и обрабатываем None
    transformed_result = []
    for item in result:
        transformed_item = {}
        for k, v in item.items():
            #new_key = k.replace(".", "_")  # Заменяем точки на подчёркивания
            new_key = k
            transformed_item[new_key] = "" if v is None else v
        transformed_result.append(transformed_item)

    column_defs = [
        #{"headerName": k.replace("_", "."), "field": k, "filter": True, "sortable": True, "minWidth": 150}
        {"headerName": k, "field": k, "filter": True, "sortable": True, "minWidth": 150}
        for k in transformed_result[0].keys()
    ]
    return {
        "defaultColDef": {
            "wrapText": True,
            "autoHeight": True,
        },
        "suppressFieldDotNotation": True,
        "enableCellTextSelection" : True,
        "columnDefs": column_defs,
        "rowData": transformed_result,
        "pagination": True,
        "paginationPageSize": 10,
        "domLayout": "normal",  # Отключаем автоматическую подгонку высоты
    }


# Функции экспорта на Python с использованием pandas
def export_to_csv(result: List[Dict], filename: str):
    df = pd.DataFrame(result)
    buffer = BytesIO()
    df.to_csv(buffer, index=False, encoding='utf-8')
    buffer.seek(0)
    #return ui.download(buffer.getvalue(), filename)
    return buffer.getvalue(), filename

def export_to_xlsx(result: List[Dict], filename: str):
    df = pd.DataFrame(result)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.getvalue(), filename

def scenario_export_to_xlsx(task_results: Dict[str, List[Dict]]):
    def excel_list_char_filter(list_name: str):
        filler = "_"
        wrong_symbols = ["/","\\","?","|","<",">",":","*",'"'," ","[","]"]
        for wrong_symbol in wrong_symbols:
            if wrong_symbol in list_name:
                list_name = list_name.replace(wrong_symbol, filler)
        return list_name
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for task_id, result in task_results.items():
            df = pd.DataFrame(result)
            df.to_excel(writer, sheet_name=excel_list_char_filter(task_id)[:31], index=False)  # Ограничение длины имени листа
    buffer.seek(0)
    return buffer

def scenario_export_to_zip_csv(task_results: Dict[str, List[Dict]]):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for task_id, result in task_results.items():
            df = pd.DataFrame(result)
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            zip_file.writestr(f"{task_id}.csv", csv_buffer.getvalue())
    buffer.seek(0)
    return buffer

def scenario_export_to_zip_json(task_results: Dict[str, List[Dict]]):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        json_data = json.dumps(list(task_results.values()), ensure_ascii=False, indent=2)
        zip_file.writestr("results.json", json_data)
    buffer.seek(0)
    return buffer

def scenario_export_to_raw_json(task_results: Dict[str, List[Dict]]):
    buffer = BytesIO()
    buffer.write(json.dumps(task_results, ensure_ascii=False).encode())
    # with open(buffer, 'w') as f:
    #    json.dumps(task_results, f)
    buffer.seek(0)
    return buffer

# Функция для отображения полноэкранной таблицы в новой вкладке
async def create_fullscreen_result_page(task_id: str, current_state: dict):
    @ui.page(f'/task_fullscreen_result/{task_id}')
    async def fullscreen_result_page():
        ui.colors(
            primary="#F97316",  # Оранжевый для основных элементов
            secondary="#1F2937",  # Тёмно-серый для второстепенных элементов
            accent="#F97316"    # Оранжевый для акцентов
        )
        dark_mode = ui.dark_mode()
        dark_mode.enable()
        ui.page_title(f'{current_state["app_name"]}')

        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = fetch_user_data(current_user, current_state)
        if not user_success:
            ui.label("Error").classes('text-negative')#("text-h5 text-red-500")
            return
        
        task_success, task_msg, _, task = fetch_task_by_id(task_id, current_state)
        if not task_success:
            ui.label(f"Error").classes('text-negative')#("text-h5 text-red-500")
            return
        
        has_tasks_admin = False
        if "tasks_admin" in user_data["roles"]:
            has_tasks_admin = True
        if "fullmaster" in user_data["roles"]:
            has_tasks_admin = True

        if task["username"] != current_user and not has_tasks_admin:
            ui.label("Error: You do not have permission to view this task").classes('text-negative')
            return

        read_step_from_storage_result = await run.cpu_bound(read_step_from_storage,{"target_id":task['id']}, current_state)
        if read_step_from_storage_result[0] == False:
            error_message = f"Failed to load task {task['id']}: {read_step_from_storage_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            ui.notify(error_message, type="negative")
            result = []
                                                
        result = read_step_from_storage_result[3]['data']

        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            ui.label("Error: Invalid task result").classes("text-h5 text-red-500")
            return
        #["id", "pid", "status_code", "status", "step_name", "source_name", "username", "timestamp_start", "timestamp_stop", "in_scenario", "json", "result_rows_count"]
        task_status_code = task["status_code"]
        column_text_class = "text-positive"
        if task_status_code < 0:
            column_text_class = "text-negative"

        with ui.column().classes("w-full"):
            ui.label(f"Task id: {task_id}").classes(column_text_class)
            ui.label(f"Step name: {task["step_name"]}").classes(column_text_class)
            ui.label(f"Source name: {task["source_name"]}").classes(column_text_class)
            ui.label(f"Time start: {task["timestamp_start"]}").classes(column_text_class)
            ui.label(f"Time stop: {task["timestamp_stop"]}").classes(column_text_class)
            ui.label(f"Scenario id: {task["in_scenario"]}").classes(column_text_class)
            grid_config = await run.cpu_bound(prepare_aggrid_for_result, result)
            fullscreen_data_aggrid = ui.aggrid(grid_config).classes("w-full h-[calc(100vh-120px)]").classes(add=current_state["aggrid_theme"])
            #fullscreen_data_aggrid.classes(add=current_state["aggrid_theme"])
            with ui.row().classes("mt-2"):
                async def prepare_export_csv(result, filename):
                    prepare_export_result = await run.cpu_bound(export_to_csv, result, filename)
                    ui.download(prepare_export_result[0], prepare_export_result[1])
                async def prepare_export_xlsx(result, filename):
                    prepare_export_result = await run.cpu_bound(export_to_xlsx, result, filename)
                    ui.download(prepare_export_result[0], prepare_export_result[1])
                ui.button("Export to CSV", on_click=partial(prepare_export_csv, result, f"task_{task_id}_result.csv")).classes("mr-2")
                ui.button("Export to XLSX", on_click=partial(prepare_export_xlsx, result, f"task_{task_id}_result.xlsx")).classes("mr-2")
                ui.button("Close", on_click=lambda: ui.run_javascript("window.close()"))

async def create_fullscreen_scenario_result_page(session_id: str, output_type: str, current_state: dict):
    ui.colors(
        primary="#F97316",  # Оранжевый для основных элементов
        secondary="#1F2937",  # Тёмно-серый для второстепенных элементов
        accent="#F97316"    # Оранжевый для акцентов
    )
    dark_mode = ui.dark_mode()
    dark_mode.enable()
    ui.page_title(f'{current_state["app_name"]}')
    #######################################
    # сюда можно попасть только через аутентификацию, а значит получаем данные по текущему пользователю
    #######################################
    current_user = current_state.get("username", "unknown")

    #user_success, user_msg, _, user_data = fetch_user_data(current_state["db_path"], current_user)
    fetch_user_data_result = await run.io_bound(fetch_user_data, current_user, current_state)
    if fetch_user_data_result[0] == False:
        ui.label("Error").classes('text-negative')
        return
    user_data = fetch_user_data_result[3]

    #######################################
    # пробуем получить о выполненном сценарии из истории db scenarios_history
    #######################################
    get_scenario_history_line_result = await run.io_bound(get_scenario_history_line, session_id, current_state)
    if fetch_user_data_result[0] == False:
        ui.label("Error: Scenario session not found").classes('text-negative')
        return
    scenario_data = get_scenario_history_line_result[3]
    #######################################
    # получаем разрешенные роли для сценария дл проверки прав доступа
    #######################################
    db_get_scenario_by_name_result = await run.io_bound(db_get_scenario_by_name, scenario_data["scenario_name"], current_state)
    if db_get_scenario_by_name_result[0] == False:
        ui.label("Error: Scenario not found").classes('text-negative')
        return

    allow_flag = False
    
    if "fullmaster" in user_data["roles"]:
        allow_flag = True
    for user_role in user_data["roles"]:
        if user_role in db_get_scenario_by_name_result[3]["roles"]:
            allow_flag = True
            break
    
    if allow_flag == False:
        ui.label("Error: You do not have permission to view this scenario result").classes('text-negative')
        return
    
    
    #######################################
    # на всякий случай валидируем сценарий
    #######################################
    scenario_validator_result = await run.io_bound(scenario_validator, True, scenario_data["json"]["scenario"], current_state)
    if scenario_validator_result[0] == False:
        error_message = f"scenario_validator_result is False: {scenario_validator_result[1]}"
        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
        ui.label("Error: Scenario data is not valid").classes('text-negative')
        return
    
    #######################################
    # Выводим шапку со статусом выполнения
    #######################################
    # статус
    if scenario_data["status_code"] == 0:
        ui.label("Status: scenario is not started yet").classes('text-positive')
    if scenario_data["status_code"] == 1:
        ui.label("Status: successful").classes('text-positive')
    if scenario_data["status_code"] > 1:
        ui.label("Status: scenario is processed yet").classes('text-positive')
    if scenario_data["status_code"] < 0:
        ui.label(f"Status: scenario was finished with error: {scenario_data["status"]}").classes('text-negative')
    # заголовок
    ui.label(f"Scenario {scenario_data["session_id"]} of user {scenario_data["username"]} was started {scenario_data["timestamp_start"]} with parameters:").classes('text-positive')
    # параметры запуска
    ui.codemirror(value=json.dumps(scenario_data["json"]["parameters"],indent = 4, ensure_ascii=False),language='JSON',line_wrapping=True, theme = current_state["codemirror_theme"]).style('width: 100%; height: auto')#'width: 100%; height: 12rem'
    # описание сценария
    ui.label(f"Description: {scenario_data["json"]["scenario"]["description"]}")#.classes("text-h5 text-red-500")
    #######################################
    # получаем данные
    #######################################
    tasks_data_list = {}

    spinner = ui.spinner('dots', size='lg', color="#F97316")
    scenario_results = await run.cpu_bound(get_scenarios_data_from_storage, scenario_data, current_state)
    spinner.delete()

    for_table_result = {}
    for task_name in scenario_results.keys():
        for_table_result[task_name] = scenario_results[task_name]["data"]

    for task_name in scenario_results.keys():

        task_status_code = scenario_results[task_name]["status_code"]
        column_text_class = "text-positive"
        if task_status_code < 0:
            column_text_class = "text-negative"
        with ui.row():
            ui.label(f"Task id: {scenario_results[task_name]["id"]}").classes(column_text_class)
            ui.label(f"Description: {scenario_results[task_name]["description"]}").classes(column_text_class)
            ui.label(f"Step name: {scenario_results[task_name]["step_name"]}").classes(column_text_class)
            ui.label(f"Data name: {scenario_results[task_name]["data_name"]}").classes(column_text_class)
        with ui.row():
            ui.label(f"Source name: {scenario_results[task_name]["source_name"]}").classes(column_text_class)
            ui.label(f"Time start: {scenario_results[task_name]["timestamp_start"]}").classes(column_text_class)
            ui.label(f"Time stop: {scenario_results[task_name]["timestamp_stop"]}").classes(column_text_class)
            time_difference = datetime.datetime.fromisoformat(scenario_results[task_name]["timestamp_stop"]) - datetime.datetime.fromisoformat(scenario_results[task_name]["timestamp_start"])
            ui.label(f"Execution: {time_difference.total_seconds()}").classes(column_text_class)


        # ui.label(f"Step: {task_name}").classes("text-h5 text-red-500")
        # ui.label(f"Task_id: {scenario_results[task_name]["task_id"]}").classes("text-h5 text-red-500")
        # ui.label(f"Status: {scenario_results[task_name]["status"]}").classes("text-h5 text-red-500")

        # ui.label(f"Description: {scenario_results[task_name]["description"]}").classes("text-h5 text-red-500")

        if output_type == "pretty":
            with ui.column().classes("w-full"):#"w-full h-screen p-4"
                grid_config = await run.cpu_bound(prepare_aggrid_for_result, scenario_results[task_name]["data"])
                if len(grid_config["rowData"]) == 0:
                    ui.aggrid(grid_config).classes("w-full h-auto").classes(add=current_state["aggrid_theme"]) # "w-full h-[calc(100vh-120px)]"
                else:
                    h_calc_vh = len(grid_config["rowData"])*16
                    if h_calc_vh > 50: h_calc_vh = 50
                    ui.aggrid(grid_config).classes(f"w-full h-[calc({h_calc_vh}vh)]").classes(add=current_state["aggrid_theme"]) # "w-full h-[calc(100vh-120px)]"
                    with ui.row().classes("mt-2"):
                        async def prepare_export_csv(result, filename):
                            prepare_export_result = await run.cpu_bound(export_to_csv, result, filename)
                            ui.download(prepare_export_result[0], prepare_export_result[1])
                        async def prepare_export_xlsx(result, filename):
                            prepare_export_result = await run.cpu_bound(export_to_xlsx, result, filename)
                            ui.download(prepare_export_result[0], prepare_export_result[1])
                        ui.button("Export to CSV", on_click=partial(prepare_export_csv, scenario_results[task_name]["data"], f"task_{task_name.replace(":", "_")}_result.csv")).classes("mr-2")
                        ui.button("Export to XLSX", on_click=partial(prepare_export_xlsx, scenario_results[task_name]["data"], f"task_{task_name.replace(":", "_")}_result.xlsx")).classes("mr-2")

    if output_type == "xlsx":
        buffer = await run.cpu_bound(scenario_export_to_xlsx, for_table_result)
        filename = f"report_{session_id.replace(":", "_")}.xlsx"
        ui.download(buffer.getvalue(), filename)
    if output_type == "csv":
        buffer = await run.cpu_bound(scenario_export_to_zip_csv, for_table_result)
        filename = f"report_{session_id.replace(":", "_")}.csv.zip"
        ui.download(buffer.getvalue(), filename)
    if output_type == "jsonzip":
        buffer = await run.cpu_bound(scenario_export_to_zip_json, for_table_result)
        filename = f"report_{session_id.replace(":", "_")}.json.zip"
        ui.download(buffer.getvalue(), filename)
    if output_type == "json":
        buffer = await run.cpu_bound(scenario_export_to_raw_json, for_table_result)
        filename = f"report_{session_id.replace(":", "_")}.json"
        ui.download(buffer.getvalue(), filename)

def mermaid_variable_cleaner(var: str):
    """Функция-очиститель для того, чтобы не ломался mermaid"""
    filler_char = "_"
    replace_chars = [" ", "[", "]", "(", ")", "%"]
    for char in replace_chars:
        var = var.replace(char, filler_char)
    return var

def get_mermaid_content_for_steps(steps_list: List, scenario: dict, current_state: Dict):
    """Важная визуализационная функция. Она ис списка шаго должна собрать кодя для mermaid https://mermaid.live
    Отрисовать каждый шаг, показать стрелками зависимости от других шагов. Зависимости как раз и определяют порядок выполнения тасок"""

    steps_map = {}

    for i, step in enumerate(steps_list):
        # steps_list это конструкция шагов из сценария
        ##########################################
        # получаем нагрузку шага из БД по имени
        ##########################################
        fetch_step_by_name_result = fetch_step_by_name(step["step_name"], current_state)
        if fetch_step_by_name_result[0] == False:
            error_message = f"fetch_step_by_name error: {fetch_step_by_name_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), ""
        
        step_source_name = fetch_step_by_name_result[3]["sourcename"]
        step_json = fetch_step_by_name_result[3]["json"]

        ##########################################
        # получаем дефолтные параметры шага для обогащения зависимостей
        ##########################################
        get_current_step_parameters_result = get_parameters_from_step("simple", step["step_name"], step_json, scenario, i, current_state)
        if not get_current_step_parameters_result[0]:
            error_message = f"get_parameters_from_step error: {get_current_step_parameters_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), ""
        parameters = get_current_step_parameters_result[3]

        ######################################
        # добавление блока apply, если он был переопределён сценарием
        ######################################
        if "steps" in scenario:
            if "apply_replacement" in scenario["steps"][i]:
                step_json["apply"] = scenario["steps"][i]["apply_replacement"]

        ######################################
        # инпут-инъектирование
        ######################################
        
        process_injections_result = process_injections(step_json["query"], parameters, current_state)
        if process_injections_result[0] == False:
            error_message = f"process_injections error: {process_injections_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), ""

        step_json["query"] = process_injections_result[3]  

        ######################################
        # инпут-инъектирование apply, если имеется
        ######################################
        # apply через apply инъектить нельзя, только через параметры
        if "apply" in step_json:
            process_injections_result = process_injections(step_json["apply"], parameters, current_state)
            if process_injections_result[0] == False:
                error_message = f"apply process_injections error: {process_injections_result[1]}"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), ""

            step_json["apply"] = process_injections_result[3]
        ##########################################
        # получаем данные источника по текущему шагу
        ##########################################

        db_get_source_result = db_get_source({"sourcename":step_source_name}, current_state)
        if db_get_source_result[0] == False:
            error_message = f"db_get_source error: {db_get_source_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), ""
        
        source = db_get_source_result[3][1]

         # Проверяем, что это валидный json
        if check_json_correct(source) == False:
            error_message = f"from_db_source is not a valid json"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), ""
        
        current_source = json.loads(source)

        ####################################
        # получаем список зависимостей
        ####################################
        get_step_dependency_result = get_step_dependency(step_json, current_source, step_json["query"], current_state)
        if get_step_dependency_result[0] == False:
            error_message = f"Ошибка получения списка зависимостей шага {step["step_name"]}: {get_step_dependency_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(),current_state))
            return False, error_message, currentFuncName(), ""
            
        dependency = get_step_dependency_result[3] # тут используется step_scenario_name
        
        current_step_name = f"{i}:{step["step_name"]}"
        steps_map[current_step_name] = {}
        steps_map[current_step_name]["dependency"] = dependency
        steps_map[current_step_name]["source_name"] = step_source_name
        steps_map[current_step_name]["data_name"] = step["data_name"]
        steps_map[current_step_name]["description"] = step["description"]
        steps_map[current_step_name]["show"] = step["show"]


    data_name_to_step_name_map = {}
    for i, step in enumerate(steps_list):
        current_step_name = f"{i}:{step["step_name"]}"
        data_name_to_step_name_map[step["data_name"]] = current_step_name

#     """ ---
# config:
#     theme: default
#     flowchart:
#         curve: linear
# ---"""
    mermaid_text = "flowchart LR"

    for step_name in reversed(steps_map.keys()):
        current_dependency = steps_map[step_name]["dependency"]
        if len(current_dependency) > 0:
            for dep in current_dependency:
                # случай, когда у нас прямая зависимость
                if dep in data_name_to_step_name_map:
                    dep_name = data_name_to_step_name_map[dep]
                    dep_description = steps_map[dep_name]["description"]
                # случай зависимости в параметре
                elif dep[2:-2] in step_json["input_parameters"]:
                    if "default" in step_json["input_parameters"][dep[2:-2]]:
                        if step_json["input_parameters"][dep[2:-2]]["default"] in data_name_to_step_name_map:
                            dep_name = data_name_to_step_name_map[step_json["input_parameters"][dep[2:-2]]["default"]]
                            dep_description = steps_map[dep_name]["description"]
                        else:
                            dep_name = f"[INPUT PARAMETER] {dep[2:-2]}"
                            if "description" in step_json["input_parameters"][dep[2:-2]]:
                                dep_description = step_json["input_parameters"][dep[2:-2]]["description"]
                            else:
                                dep_description = "Without description"

                    dep_name = f"[INPUT PARAMETER] {dep[2:-2]}"
                    if "description" in step_json["input_parameters"][dep[2:-2]]:
                        dep_description = step_json["input_parameters"][dep[2:-2]]["description"]
                    else:
                        dep_description = "Without description"
                else:
                    dep_name = f"[UNKNOWN] {dep[2:-2]}"
                    dep_description = "Without description"

                if dep_name in steps_map:
                    if "source_name" in steps_map[dep_name]:
                        deb_source_name = steps_map[dep_name]["source_name"]
                    else:
                        deb_source_name = "?"
                else:
                    deb_source_name = "?"
                    
                if step_name in steps_map:
                    if "source_name" in steps_map[step_name]:
                        step_source_name = steps_map[step_name]["source_name"]
                    else:
                            deb_source_name = "?"
                else:
                    step_source_name = "?"

                mermaid_text = mermaid_text + "\n"
                mermaid_text = mermaid_text + f"""{mermaid_variable_cleaner(dep_name)}_{mermaid_variable_cleaner(dep)}["{dep_name}: ({deb_source_name}) {dep_description}"] -->|"{dep}"| {mermaid_variable_cleaner(step_name)}_{mermaid_variable_cleaner(steps_map[step_name]["data_name"])}["{step_name}: ({step_source_name}) {steps_map[step_name]["description"]}"]"""
                #mermaid_text = mermaid_text + "\n" + f"style {step_name}_{steps_map[step_name]["data_name"]} text-align:left"
                #mermaid_text = mermaid_text + f"{dep_name}/{dep}/{steps_map[dep_name]["description"]} --> {step_name}/{steps_map[step_name]["data_name"]}/{steps_map[step_name]["description"]}"
        else:
            pass
            #mermaid_text = mermaid_text + "\n"
            #mermaid_text = mermaid_text + f"""Start --> {step_name.replace("[", "_").replace("]", "_").replace(" ", "_")}_{steps_map[step_name]["data_name"]}["{step_name}: {steps_map[step_name]["description"]}"]"""
    #print(mermaid_text)
    return True, "OK", currentFuncName(), mermaid_text

def get_mermaid_content_for_conjoined_parameters(current_parameters: Dict, scenario_json: Dict, current_state: Dict):
    """Важная визуализационная функция. Она из объединяемых параметров должна собрать код для mermaid https://mermaid.live
    Отрисовать каждый объединённый параметр"""
    conjoined_parameters = scenario_json["conjoined_parameters"]
    # {
    #         "search_value":
    #         [
    #             "0:search_value"
    #         ],
    #         "time_delta":
    #         [
    #             "0:time_delta"
    #         ]
    # }

    steps = scenario_json["steps"]
    # [
    #     {
    #         "step_name": "wb_openvpn_requests",
    #         "data_name": "vpn_data",
    #         "description": "Запрос по VPN WB",
    #         "show": true
    #     },
    #     {
    #         "step_name": "openvpn_sessions",
    #         "data_name": "wb_vpn_sessions",
    #         "description": "Периоды пользователей по владению ip-адресами",
    #         "show": true
    #     }
    # ]

    # current_parameters
    # {
    #     "0:timestamp_field": "event.agent.timestamp",
    #     "0:timestamp": "2025-04-07T09:40:19.288220Z",
    #     "time_delta": 432000,
    #     "search_value": "[please fill me]",
    #     "0:index": "vector-vpn*"
    # }
    try:
        mermaid_text = "flowchart LR"

        original_steps_parameters_buffer = {}

        for i, parameter in enumerate(current_parameters.keys()):
            if ":" in parameter: # это значит параметр напрямую наследуемый из шага
                step_num = int(parameter.split(":")[0])
                parameter_name = parameter.split(":")[1]
                step_name = steps[step_num]["step_name"]

                if step_num not in original_steps_parameters_buffer:
                    # теперь получаем шаг из БД чтобы прочитать description параметра
                    fetch_step_by_name_result= fetch_step_by_name(step_name, current_state)
                    if fetch_step_by_name_result[0] == False:
                        original_steps_parameters_buffer[step_num] = {"error":fetch_step_by_name_result[1]}
                    else:
                        original_steps_parameters_buffer[step_num] = fetch_step_by_name_result[3]["json"]["input_parameters"]

                original_step_parameters = original_steps_parameters_buffer[step_num]

                if parameter_name not in original_step_parameters:
                    if "error" in original_step_parameters:
                        mermaid_text = mermaid_text + "\n"
                        mermaid_text = mermaid_text + f"""Param_{i}["{step_num}: **{step_name}** (**{parameter_name}**): error: {original_step_parameters['error']}"]"""
                    else:
                        mermaid_text = mermaid_text + "\n"
                        mermaid_text = mermaid_text + f"""Param_{i}["{step_num}: **{step_name}** (**{parameter_name}**) not in original step?"]"""
                else:
                    if "description" in original_step_parameters[parameter_name]:
                        parameter_description = original_step_parameters[parameter_name]["description"]

                        mermaid_text = mermaid_text + "\n"
                        mermaid_text = mermaid_text + f"""Param_{i}["{step_num}: **{step_name}** (**{parameter_name}**): {parameter_description}"]"""
                    else:
                        mermaid_text = mermaid_text + "\n"
                        mermaid_text = mermaid_text + f"""Param_{i}["{step_num}: **{step_name}** (**{parameter_name}**): without description"]"""
            else:
                # это conjoined
                if parameter not in conjoined_parameters:
                    # мисконфиг параметров
                    pass
                else:
                    for j, conjoined_part in enumerate(conjoined_parameters[parameter]):
                        if ":" in conjoined_part: # это значит параметр напрямую наследуемый из шага
                            step_num = int(conjoined_part.split(":")[0])
                            conj_part_parameter_name = conjoined_part.split(":")[1]
                            step_name = steps[step_num]["step_name"]

                            if step_num not in original_steps_parameters_buffer:
                                # теперь получаем шаг из БД чтобы прочитать description параметра
                                fetch_step_by_name_result= fetch_step_by_name(step_name, current_state)
                                if fetch_step_by_name_result[0] == False:
                                    original_steps_parameters_buffer[step_num] = {"error":fetch_step_by_name_result[1]}
                                else:
                                    original_steps_parameters_buffer[step_num] = fetch_step_by_name_result[3]["json"]["input_parameters"]

                            original_step_parameters = original_steps_parameters_buffer[step_num]

                            if conj_part_parameter_name not in original_step_parameters:
                                if "error" in original_step_parameters:
                                    mermaid_text = mermaid_text + "\n"
                                    mermaid_text = mermaid_text + f"""Param_{i}[{parameter}] --> Param_{i}_{j}["{step_num}: **{step_name}** (**{conj_part_parameter_name}**): error: {original_step_parameters['error']}"]"""
                                else:
                                    mermaid_text = mermaid_text + "\n"
                                    mermaid_text = mermaid_text + f"""Param_{i}[{parameter}] --> Param_{i}_{j}["{step_num}: **{step_name}** (**{conj_part_parameter_name}**) not in original step?"]"""
                            else:
                                if "description" in original_step_parameters[conj_part_parameter_name]:
                                    parameter_description = original_step_parameters[conj_part_parameter_name]["description"]

                                    mermaid_text = mermaid_text + "\n"
                                    mermaid_text = mermaid_text + f"""Param_{i}[{parameter}] --> Param_{i}_{j}["{step_num}: **{step_name}** (**{conj_part_parameter_name}**): {parameter_description}"]"""
                                else:
                                    mermaid_text = mermaid_text + "\n"
                                    mermaid_text = mermaid_text + f"""Param_{i}[{parameter}] --> Param_{i}_{j}["{step_num}: **{step_name}** (**{conj_part_parameter_name}**): without description"]"""

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(),current_state))
        return False, error_message, currentFuncName(), ""
    #print(mermaid_text)
    return True, "OK", currentFuncName(), mermaid_text
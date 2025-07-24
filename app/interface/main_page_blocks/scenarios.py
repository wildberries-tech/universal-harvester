import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from nicegui import ui, app, run
from app.validation import *
from app.database.scenarios import fetch_scenarios_history, fetch_scenarios
from app.database.tasks import db_get_tasks, fetch_tasks, update_task_field, fetch_task_by_id
from app.database.users import fetch_user_data

from typing import Tuple, Optional, Dict, List
from app.engine.storage import read_step_from_storage
import os, signal
import pandas as pd
from io import BytesIO
import zipfile

from app.engine.engine import engine_hasshin

from app.engine.scenarios import get_parameters_from_scenario, run_scenario, scenario_filter_by_roles
from app.interface.additional import get_mermaid_content_for_steps, get_mermaid_content_for_conjoined_parameters

# # Функции экспорта
# def export_to_csv(result: List[Dict], filename: str):
#     df = pd.DataFrame(result)
#     buffer = BytesIO()
#     df.to_csv(buffer, index=False, encoding='utf-8')
#     buffer.seek(0)
#     #return ui.download(buffer.getvalue(), filename)
#     return buffer.getvalue(), filename

# def scenario_export_to_xlsx(task_results: Dict[str, List[Dict]], filename: str):
#     buffer = BytesIO()
#     with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
#         for task_id, result in task_results.items():
#             df = pd.DataFrame(result)
#             df.to_excel(writer, sheet_name=task_id[:31], index=False)  # Ограничение длины имени листа
#     buffer.seek(0)
#     return buffer.getvalue(), filename

# def scenario_export_to_zip_csv(task_results: Dict[str, List[Dict]], filename: str):
#     buffer = BytesIO()
#     with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#         for task_id, result in task_results.items():
#             df = pd.DataFrame(result)
#             csv_buffer = BytesIO()
#             df.to_csv(csv_buffer, index=False, encoding='utf-8')
#             zip_file.writestr(f"{task_id}.csv", csv_buffer.getvalue())
#     buffer.seek(0)
#     return buffer.getvalue(), filename

# def scenario_export_to_zip_json(task_results: Dict[str, List[Dict]], filename: str):
#     buffer = BytesIO()
#     with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#         json_data = json.dumps(list(task_results.values()), ensure_ascii=False, indent=2)
#         zip_file.writestr("results.json", json_data)
#     buffer.seek(0)
#     return ui.download(buffer.getvalue(), filename)

# Заглушки




def fetch_task_result_by_id(task_id: str) -> List[Dict]:
    return []  # Реализуете самостоятельно
# Основная функция отрисовки
def draw_scenarios(interface_container: ui.card, current_state: dict) -> Tuple[bool, str, str, None]:
    func_name = "draw_scenarios"
    
    try:
        logger_log(syslog.LOG_INFO, get_log_message("Starting draw_scenarios", func_name, current_state))

        interface_container.clear()

        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = fetch_user_data(current_user, current_state)
        if not user_success:
            logger_log(syslog.LOG_ERR, get_log_message(user_msg, func_name, current_state))
            return False, user_msg, func_name, None
        user_roles = user_data["roles"]

        has_scenarios_admin = False
        if "scenarios_admin" in user_roles:
            has_scenarios_admin = True
        if "fullmaster" in user_roles:
            has_scenarios_admin = True

        #default_limit = 5000 if has_scenarios_admin else 1000

        # scenarios_success, scenarios_msg, _, all_scenarios = fetch_scenarios(has_scenarios_admin, current_state)
        # if not scenarios_success:
        #     logger_log(syslog.LOG_ERR, get_log_message(scenarios_msg, func_name, current_state))
        #     return False, scenarios_msg, func_name, None

        with interface_container:
            with ui.column().classes("w-full"):
                ui.label("Scenarios Management").classes("text-h5 mb-4")

                # limit_input = ui.number(
                #     label="Scenarios Limit",
                #     value=default_limit,
                #     min=1,
                #     max=5000 if has_scenarios_admin else 1000,
                #     step=100
                # ).classes("w-32")

                scenarios_container = ui.column().classes("w-full mt-4")
                grid = None

                def refresh_scenarios():
                    nonlocal grid
                    scenarios_container.clear()
                    # limit = int(limit_input.value)
                    scenarios_success, scenarios_msg, _, scenarios = fetch_scenarios(True, current_state)
                    if not scenarios_success:
                        ui.notify(scenarios_msg, type="negative")
                        return
                    
                    scenario_filter_by_roles_result = scenario_filter_by_roles(scenarios, user_roles, current_state)
                    if scenario_filter_by_roles_result[0] == False:
                        error_message = f"get allowed scenarios fail: {scenario_filter_by_roles_result[1]}"
                        ui.notify(error_message, type="negative")
                        return
                    scenarios = scenario_filter_by_roles_result[3]

                    with scenarios_container:
                        grid_data = [
                            {
                                "scenario_name": scenario["scenario_name"],
                                "description": scenario["json"]["description"],
                                "author": scenario["author"],
                                "roles": json.dumps(scenario["roles"], indent=0, ensure_ascii=False)
                            } for scenario in scenarios
                        ]
                        grid = ui.aggrid({
                            "defaultColDef": {
                                "wrapText": True,
                                "autoHeight": True,
                            },
                            "columnDefs": [
                                {"headerName": "Name", "field": "scenario_name", "filter": True, "sortable": True, "minWidth": 150},
                                {"headerName": "Description", "field": "description", "filter": True, "sortable": True, "minWidth": 150},
                                {"headerName": "Author", "field": "author", "filter": True, "sortable": True, "minWidth": 120},
                                {"headerName": "Roles", "field": "roles", "filter": True, "sortable": True, "minWidth": 120},
                            ],
                            "rowData": grid_data,
                            "rowSelection": "single",
                            "pagination": True,
                            "paginationPageSize": 20,
                            "domLayout": "normal",
                        }).classes("w-full h-[calc(80vh)]").classes(add=current_state["aggrid_theme"])

                        scenario_action_container = ui.column().classes("w-full mt-4")
                        async def update_scenario_actions():
                            scenario_action_container.clear()
                            selected_row = (await grid.get_selected_row()) or {}
                            if not selected_row:
                                return
                            scenario = next(s for s in scenarios if s["scenario_name"] == selected_row["scenario_name"])
                            with scenario_action_container:
                                with ui.card().classes("w-full"):
                                    ui.label(f"Scenario: {scenario['scenario_name']}").classes("text-h6")
                                    scenario_json = scenario["json"]
                                    ui.label(f"Description: {scenario_json.get('description', '')}").classes("mt-2")
                                    
                                    # Просмотр шагов
                                    #print(scenario_json.get("steps", []))
                                    
                                    get_mermaid_content_for_steps_result = get_mermaid_content_for_steps(scenario_json.get("steps", []), scenario_json, current_state)
                                    if get_mermaid_content_for_steps_result[0] == False:
                                        error_message = f"get_mermaid_content_for_steps_result is False: {get_mermaid_content_for_steps_result[1]}"
                                        ui.notify(error_message, type="negative")
                                        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                                        mermaid_scenario_flag = False
                                    else:
                                        pass
                                        mermaid_scenario_flag = True
                                        #ui.mermaid(content = get_mermaid_content_for_steps_result[3], config = {"theme": "dark"}).style('width: 100%; border: 1px solid black; border-radius: 8px; padding: 10px;')

                                    #########################################
                                    # Визуализация параметрво и правил объединяния, сначала получаем параметры, затем рисуем
                                    #########################################
                                    # получаем параметры
                                    get_parameters_from_scenario_result = get_parameters_from_scenario(scenario["json"], current_state)
                                    if get_parameters_from_scenario_result[0] == False:
                                        ui.notify("Invalid scenario parameters", type="negative")
                                        error_message = f"get_parameters_from_scenario_result is False: {get_parameters_from_scenario_result[1]}"
                                        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))

                                        current_parameters = {}
                                    else:
                                        current_parameters = get_parameters_from_scenario_result[3]

                                    # Просмотр правил объединения
                                    #ui.label("Parameters info:").classes("mt-2")
                                    #print(current_parameters, scenario_json)
                                    get_mermaid_content_for_conjoined_parameters_result = get_mermaid_content_for_conjoined_parameters(current_parameters, scenario_json, current_state)
                                    if get_mermaid_content_for_conjoined_parameters_result[0] == False:
                                        error_message = f"get_mermaid_content_for_conjoined_parameters_result is False: {get_mermaid_content_for_conjoined_parameters_result[1]}"
                                        ui.notify(error_message, type="negative")
                                        logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                                        mermaid_parameters_flag = False
                                    else:
                                        pass
                                        mermaid_parameters_flag = True
                                        #print(get_mermaid_content_for_conjoined_parameters_result[3])
                                        #ui.mermaid(content = get_mermaid_content_for_conjoined_parameters_result[3], config = {"theme": "dark"}).style('width: 100%; border: 1px solid black; border-radius: 8px; padding: 10px;')
                                    with ui.tabs().classes('w-full') as tabs:
                                        one = ui.tab('Scenario scheme')
                                        two = ui.tab('Parameters schema')
                                    with ui.tab_panels(tabs, value=one).classes('w-full'):
                                        with ui.tab_panel(one):
                                            if mermaid_scenario_flag == True:
                                                ui.mermaid(content = get_mermaid_content_for_steps_result[3], config = {"theme": "dark"}).style('width: 100%; border: 1px solid black; border-radius: 8px; padding: 10px;')
                                            else:
                                                ui.label(f"Error").classes("text-h6")
                                        with ui.tab_panel(two):
                                            if mermaid_parameters_flag == True:
                                                ui.mermaid(content = get_mermaid_content_for_conjoined_parameters_result[3], config = {"theme": "dark"}).style('width: 100%; border: 1px solid black; border-radius: 8px; padding: 10px;')
                                            else:
                                                ui.label(f"Error").classes("text-h6")
                                    # Параметры запуска, доступные для редактирования
                                    ui.label("Run Parameters:").classes("mt-4")
                                    scenario_parameters_codemirror = ui.codemirror(json.dumps(current_parameters, indent=2, ensure_ascii=False), language='json', theme = current_state["codemirror_theme"]).classes("w-full h-48")

                                    # Кнопка запуска
                                    need_scenario_notify = True
                                    #run_scenario(user_roles: List, scenario_name: str, scenario_json: str, scenario_parameters: str, current_state: Dict)
                                    async def run_scenario_decorator():
                                        run_scenario_result = await run.cpu_bound(run_scenario,user_roles, scenario["scenario_name"],scenario["json"], scenario_parameters_codemirror.value, need_scenario_notify, "", current_state)
                                        if run_scenario_result[0] == False:
                                            ui.notify("Scenario run fail", type="negative")
                                            error_message = f"run_scenario_result is False: {run_scenario_result[1]}"
                                            logger_log(syslog.LOG_ERR, get_log_message(f"fail: {error_message}", currentFuncName(), current_state))
                                        else:
                                            ui.notify(f"Scenario {run_scenario_result[3]} run OK", type="positive")
                                            refresh_history()
                                    ui.button("Run Scenario", on_click=run_scenario_decorator).classes("mt-2")


                        grid.on("selectionChanged", update_scenario_actions)

                        # История выполнения
                        history_container = ui.column().classes("w-full mt-4")
                        history_grid = None
                        def refresh_history():
                            nonlocal history_grid
                            history_container.clear()
                            history_success, history_msg, _, history = fetch_scenarios_history(has_scenarios_admin, current_state)
                            if not history_success:
                                ui.notify(history_msg, type="negative")
                                return
                            with history_container:
                                ui.label("Execution History (click for get results)").classes("text-h6 mb-2")
                                history_data = [
                                    {
                                        "scenario_name": h["scenario_name"],
                                        "scenario_parameters": json.dumps(h["json"]["parameters"], indent = 2, ensure_ascii=False),
                                        "username": h["username"],
                                        "status_code": h["status_code"],
                                        "status": h["status"],
                                        "timestamp_start": h["timestamp_start"],
                                        "timestamp_stop": h["timestamp_stop"],
                                        "session_id": h["session_id"]
                                    } for h in history
                                ]
                                history_grid = ui.aggrid({
                                        "defaultColDef": {
                                            "wrapText": True,
                                            "autoHeight": True,
                                        },
                                        "columnDefs": [
                                        {"headerName": "Scenario", "field": "scenario_name", "filter": True, "sortable": True, "minWidth": 150},
                                        {"headerName": "Parameters", "field": "scenario_parameters", "filter": True, "sortable": True, "minWidth": 150},
                                        {"headerName": "User", "field": "username", "filter": True, "sortable": True, "minWidth": 120},
                                        {"headerName": "Status Code", "field": "status_code", "filter": True, "sortable": True, "minWidth": 120},
                                        {"headerName": "Status", "field": "status", "filter": True, "sortable": True, "minWidth": 150},
                                        {"headerName": "Start", "field": "timestamp_start", "filter": True, "sortable": True, "minWidth": 180},
                                        {"headerName": "Stop", "field": "timestamp_stop", "filter": True, "sortable": True, "minWidth": 180},
                                        {"headerName": "Session ID", "field": "session_id", "filter": True, "sortable": True, "minWidth": 150},
                                    ],
                                    "rowData": history_data,
                                    "rowSelection": "single",
                                    "pagination": True,
                                    "paginationPageSize": 10,
                                    "domLayout": "normal",
                                }).classes("w-full h-96").classes(add=current_state["aggrid_theme"])

                                async def history_grid_click():
                                    selected_row = (await history_grid.get_selected_row()) or {}
                                    if not selected_row:
                                        return
                                    history_scenario_id = selected_row["session_id"]
                                    dummy_link = f"{current_state['itself_link']}result/{history_scenario_id}"
                                    ui.button("Open pretty", on_click=lambda: ui.navigate.to(f"{dummy_link}/pretty", new_tab=True)).classes("mt-2")
                                    ui.button("Export to CSV", on_click=lambda: ui.navigate.to(f"{dummy_link}/csv", new_tab=True)).classes("mt-2")
                                    ui.button("Export to XLSX", on_click=lambda: ui.navigate.to(f"{dummy_link}/xlsx", new_tab=True)).classes("mt-2")
                                    

                                history_grid.on("selectionChanged", history_grid_click)


                        refresh_history()

                refresh_scenarios()
                # limit_input.on("change", refresh_scenarios)

        return True, "OK", func_name, None

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
        return False, error_message, func_name, None
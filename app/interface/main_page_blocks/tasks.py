import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from nicegui import ui, app, run
from functools import partial
from app.validation import *
from app.database.tasks import db_get_tasks, fetch_tasks, update_task_field, fetch_task_by_id
from app.database.users import fetch_user_data
from typing import Tuple, Optional, Dict, List
from app.engine.storage import read_step_from_storage
from app.interface.additional import prepare_aggrid_for_result, export_to_csv, export_to_xlsx, create_fullscreen_result_page
from app.interface.main_page_blocks.steps import run_step
import os, signal
import copy

async def tasks_function_halt(tasks_grid, current_state):
    rows = await tasks_grid.get_selected_rows()
    if rows:
        for row in rows:
            pass
            ui.notify(f"{row['pid']}")
    else:
        ui.notify('No rows selected.')


# Основная функция отрисовки
async def draw_tasks(interface_container: ui.card, current_state: dict) -> Tuple[bool, str, str, None]:
    func_name = "draw_tasks"
    try:
        # Логирование начала работы
        logger_log(syslog.LOG_INFO, get_log_message("Starting draw_tasks", func_name, current_state))

        # Очистка контейнера перед отрисовкой
        interface_container.clear()

        # Получение данных пользователя
        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = await run.io_bound(fetch_user_data, current_user, current_state)
        if not user_success:
            logger_log(syslog.LOG_ERR, get_log_message(user_msg, func_name, current_state))
            return False, user_msg, func_name, None
        user_roles = user_data["roles"]
        has_tasks_admin = False
        if "tasks_admin" in user_roles:
            has_tasks_admin = True
        if "fullmaster" in user_roles:
            has_tasks_admin = True

        default_limit = 5000 if has_tasks_admin else 1000

        # Получение задач
        #tasks_success, tasks_msg, _, all_tasks = fetch_tasks(current_user, has_tasks_admin, current_state)

        # if not tasks_success:
        #     logger_log(syslog.LOG_ERR, get_log_message(tasks_msg, func_name, current_state))
        #     return False, tasks_msg, func_name, None

        with interface_container:
            with ui.column().classes("w-full"):
                ui.label("Tasks Management").classes("text-h5 mb-4")

                limit_input = ui.number(
                    label="Tasks Limit",
                    value=default_limit,
                    min=1,
                    max=5000 if has_tasks_admin else 1000,
                    step=100
                ).classes("w-32")

                username_input = ui.input(value=current_state["username"])
                username_input.enabled = has_tasks_admin

                

                tasks_container = ui.column().classes("w-full h-full")
                grid = None

                async def refresh_tasks():
                    nonlocal grid
                    tasks_container.clear()
                    #limit = int(limit_input.value)
                    current_user = username_input.value
                    tasks_success, tasks_msg, _, tasks = await run.io_bound(fetch_tasks, current_user, has_tasks_admin, current_state)
                    if not tasks_success:
                        ui.notify(tasks_msg, type="negative")
                        logger_log(syslog.LOG_ERR, get_log_message(tasks_msg, func_name, current_state))
                        return
                    with tasks_container:
                        grid_data = [
                            {
                                "id": task["id"],
                                "pid": task["pid"],
                                "status_code": task["status_code"],
                                "status": task["status"],
                                "result_rows_count": task["result_rows_count"],
                                "step_name": task["step_name"],
                                "source_name": task["source_name"],
                                "username": task["username"],
                                "timestamp_start": task["timestamp_start"],
                                "timestamp_stop": task["timestamp_stop"],
                                "in_scenario": task["in_scenario"]
                            } for task in tasks
                        ]
                        grid = ui.aggrid({
                            "defaultColDef": {
                                            "wrapText": True,
                                            "autoHeight": True,
                            },
                            "columnDefs": [
                                {"headerName": "ID", "field": "id", "filter": True, "sortable": True, "minWidth": 150},
                                {"headerName": "PID", "field": "pid", "filter": True, "sortable": True, "minWidth": 100},
                                {"headerName": "Status Code", "field": "status_code", "filter": True, "sortable": True, "minWidth": 120},
                                {"headerName": "Status", "field": "status", "filter": True, "sortable": True, "minWidth": 150},
                                {"headerName": "Result rows count", "field": "result_rows_count", "filter": True, "sortable": True, "minWidth": 150},
                                {"headerName": "Step Name", "field": "step_name", "filter": True, "sortable": True, "minWidth": 150},
                                {"headerName": "Source Name", "field": "source_name", "filter": True, "sortable": True, "minWidth": 150},
                                {"headerName": "Username", "field": "username", "filter": True, "sortable": True, "minWidth": 120},
                                {"headerName": "Start Time", "field": "timestamp_start", "filter": True, "sortable": True, "minWidth": 180},
                                {"headerName": "Stop Time", "field": "timestamp_stop", "filter": True, "sortable": True, "minWidth": 180},
                                {"headerName": "Scenario", "field": "in_scenario", "filter": True, "sortable": True, "minWidth": 150},
                            ],
                            "rowData": grid_data,
                            "rowSelection": "single",
                            "pagination": True,
                            "paginationPageSize": 20,
                            "domLayout": "normal",
                        }).classes("w-full h-[calc(80vh)]").classes(add=current_state["aggrid_theme"])

                        task_action_container = ui.column().classes("w-full mt-4")
                        async def update_task_actions():
                            task_action_container.clear()
                            selected_row = (await grid.get_selected_row()) or {}
                            if not selected_row:
                                return
                            task = next(t for t in tasks if t["id"] == selected_row["id"])
                            if task["username"] != current_user and not has_tasks_admin:
                                return
                            with task_action_container:
                                with ui.card().classes("w-full"):
                                    ui.label(f"Task: {task['id']}").classes("text-h6")

                                    if task["status_code"] > 1:
                                        async def terminate_task():
                                            pid = task["pid"]
                                            executable_name = current_state.get("executable_name", "")
                                            if not pid or not executable_name:
                                                ui.notify("Cannot terminate: PID or executable name missing", type="negative")
                                                return
                                            try:
                                                os.kill(pid, signal.SIGTERM)
                                                upd_success, upd_msg, _, _ = update_task_field(task["id"], "status_code", -1, current_state)
                                                if not upd_success:
                                                    ui.notify(upd_msg, type="negative")
                                                    return
                                                upd_success, upd_msg, _, _ = update_task_field(task["id"], "timestamp_stop", currentTimestamp(), current_state)
                                                if not upd_success:
                                                    ui.notify(upd_msg, type="negative")
                                                    return
                                                upd_success, upd_msg, _, _ = update_task_field(task["id"], "status", "Terminated by user", current_state)
                                                if not upd_success:
                                                    ui.notify(upd_msg, type="negative")
                                                    return
                                                ui.notify(f"Task {task['id']} terminated", type="positive")
                                                draw_tasks(interface_container, current_state)
                                            except BaseException as e:
                                                ui.notify(f"Failed to terminate task: {str(e)}", type="negative")
                                        ui.button("Terminate Task", on_click=terminate_task).classes("mt-2")

                                    if task["status_code"] == 1:
                                        try:
                                            read_step_from_storage_result = await run.cpu_bound(read_step_from_storage, {"target_id":task['id']}, current_state)
                                            if read_step_from_storage_result[0] == False:
                                                error_message = f"Failed to load task {task['id']}: {read_step_from_storage_result[1]}"
                                                logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
                                                ui.notify(error_message, type="negative")
                                                result = []
                                                
                                            result = read_step_from_storage_result[3]['data']
                                            if isinstance(result, list) and all(isinstance(item, dict) for item in result):
                                                if len(result) > 1000:
                                                    show_result = result[:999]
                                                    ui.label(f"Task Result (first 1000 lines from {len(result)})").classes("text-h6 mt-4")
                                                else:
                                                    show_result = result
                                                    ui.label(f"Task Result (full {len(result)} lines)").classes("text-h6 mt-4")
                                                ui.aggrid(prepare_aggrid_for_result(show_result)).classes("w-full h-[calc(70vh)]").classes(add=current_state["aggrid_theme"])
                                                with ui.row().classes("mt-2"):
                                                    async def prepare_export_csv(result, filename):
                                                        prepare_export_result = await run.cpu_bound(export_to_csv, result, filename)
                                                        ui.download(prepare_export_result[0], prepare_export_result[1])
                                                    async def prepare_export_xlsx(result, filename):
                                                        prepare_export_result = await run.cpu_bound(export_to_xlsx, result, filename)
                                                        ui.download(prepare_export_result[0], prepare_export_result[1])
                                                    ui.button("Open pretty", on_click=lambda: open_fullscreen(task["id"])).classes("mr-2")
                                                    ui.button("Export to CSV", on_click= partial(prepare_export_csv, result, f"task_{task['id']}_result.csv")).classes("mr-2")
                                                    ui.button("Export to XLSX", on_click= partial(prepare_export_xlsx, result, f"task_{task['id']}_result.xlsx")).classes("mr-2")      
                                            else:
                                                ui.label("No valid result available").classes("mt-4")
                                        except json.JSONDecodeError:
                                            ui.label("Invalid result JSON").classes("mt-4")
                                    
                                    # вариант для кнопки перезапуска таски
                                    if task["status_code"] < 0 or task["status_code"] == 1:
                                        if isinstance(task["json"], dict) == False:
                                            task["json"] = json.loads(task["json"])
                                        ui.button("Restart task", on_click=lambda: run_step_decorator(task, current_state)).classes("mr-2")

                        grid.on("selectionChanged", update_task_actions)

                async def open_fullscreen(task_id: str):
                    await create_fullscreen_result_page(task_id, current_state)
                    ui.navigate.to(f'/task_fullscreen_result/{task_id}', new_tab=True)
                
                async def run_step_decorator(task: dict, current_state):
                    if task["in_scenario"] == "Null":
                        scenario = {"empty":True}
                    else:
                        scenario = task["json"]["scenario"]
                    #print(task["step_name"], task["source_name"], json.dumps(task["json"]["step"]), json.dumps(task["json"]["parameters"]), task["in_scenario"], scenario, current_state)
                    #run_step(task["step_name"], task["source_name"], json.dumps(task["json"]["step"]), json.dumps(task["json"]["parameters"]), task["in_scenario"], scenario, current_state)
                    #refresh_tasks()

                await refresh_tasks()
                #limit_input.on("change", refresh_tasks)

                ui.button('Refresh', on_click=refresh_tasks)

        return True, "OK", func_name, None

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
        return False, error_message, func_name, None

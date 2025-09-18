import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from nicegui import ui, app, run, events
from functools import partial
from app.validation import *
from app.database.static_data import db_get_static_data_list, db_get_static_data_by_name, db_delete_static_data_by_name, db_upload_static_data
from app.database.users import fetch_user_data
from typing import Tuple, Optional, Dict, List
from app.engine.storage import read_step_from_storage
from app.interface.additional import prepare_aggrid_for_result, export_to_csv, export_to_xlsx, create_fullscreen_result_page
from app.interface.main_page_blocks.steps import run_step
import os, signal
import copy

# Основная функция отрисовки
async def draw_static_data(interface_container: ui.card, current_state: dict) -> Tuple[bool, str, str, None]:
    try:
        # Логирование начала работы
        logger_log(syslog.LOG_INFO, get_log_message("Starting static_data", currentFuncName(), current_state))

        # Очистка контейнера перед отрисовкой
        interface_container.clear()

        # Получение данных пользователя
        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = await run.io_bound(fetch_user_data, current_user, current_state)
        if not user_success:
            logger_log(syslog.LOG_ERR, get_log_message(user_msg, currentFuncName(), current_state))
            return False, user_msg, currentFuncName(), None
        user_roles = user_data["roles"]

        is_admin = False
        if "static_data_admin" in user_roles:
            is_admin = True
        if "fullmaster" in user_roles:
            is_admin = True

        if is_admin == False:
            with interface_container:
                with ui.column().classes("w-full"):
                    ui.label("Access Denied").classes("text-h5")
                    ui.label("You need the 'static_data_admin' role to access this page.")
            return True, "OK", currentFuncName(), None

        with interface_container:
            with ui.column().classes("w-full"):
                ui.label("Static data").classes("text-h5 mb-4")

                static_data_container = ui.column().classes("w-full h-full")
                grid = None

                """Главная функция отрисовки интерфейса статичных данных (словарей)
                Забираем список из таблицы и формируем список имён данных с размером,
                датой загрузки и комментарием"""
                async def refresh_static_data():
                    nonlocal grid
                    static_data_container.clear()
                    # забираем список статичных данных
                    db_get_static_data_list_result = await run.io_bound(db_get_static_data_list, current_state)
                    if not db_get_static_data_list_result[0]:
                        ui.notify("Ошибка получения списка статичных данных", type="negative")
                        logger_log(syslog.LOG_ERR, get_log_message(f"{db_get_static_data_list_result[2]} error: {db_get_static_data_list_result[1]}", currentFuncName(), current_state))
                        return
                    current_static_data_list = db_get_static_data_list_result[3]
                    
                    with static_data_container:
                        #grid_data = current_static_data_list
                        grid = ui.aggrid({
                            "defaultColDef": {
                                            "wrapText": True,
                                            "autoHeight": True,
                            },
                            "columnDefs": [
                                {"headerName": "Name", "field": "name", "filter": True, "sortable": True, "minWidth": 150},
                                {"headerName": "Timestamp", "field": "timestamp", "filter": True, "sortable": True, "minWidth": 180},
                                {"headerName": "Username", "field": "owner", "filter": True, "sortable": True, "minWidth": 120},
                                {"headerName": "Comment", "field": "comment", "filter": True, "sortable": True, "minWidth": 200},
                                {"headerName": "Lines", "field": "lines", "filter": True, "sortable": True, "minWidth": 100},

                            ],
                            "rowData": current_static_data_list,
                            "rowSelection": "single",
                            "enableCellTextSelection" : True,
                            "pagination": True,
                            "paginationPageSize": 20,
                            "domLayout": "normal",
                        }).classes("w-full h-[calc(80vh)]").classes(add=current_state["aggrid_theme"])

                        # описываем клик по выбранным статичным данным
                        static_data_action_container = ui.column().classes("w-full mt-4")
                        async def static_data_click_actions():
                            static_data_action_container.clear()
                            selected_row = (await grid.get_selected_row()) or {}
                            if not selected_row:
                                return
                            
                            #static_data = next(sd for sd in current_static_data_list if sd["name"] == selected_row["name"])

                            with static_data_action_container:
                                with ui.card().classes("w-full"):
                                    STATIC_DATA_SHOW_LIMIT = 1000

                                    ui.label(f"Data: {selected_row["name"]}").classes("text-h6")
                                    ui.label(f"Timestamp: {selected_row["timestamp"]}").classes("text-h6")
                                    ui.label(f"Owner: {selected_row["owner"]}").classes("text-h6")
                                    ui.label(f"Lines: {selected_row["lines"]} (Show limit {STATIC_DATA_SHOW_LIMIT})").classes("text-h6")
                                    ui.label(f"Comment: {selected_row["comment"]}").classes("text-h6")

                                    try:
                                        # получение payload
                                        db_get_static_data_by_name_result = await run.io_bound(db_get_static_data_by_name, selected_row["name"], STATIC_DATA_SHOW_LIMIT, current_state)
                                        if not db_get_static_data_by_name_result[0]:
                                            ui.notify("Ошибка получения статичных данных", type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(f"{db_get_static_data_by_name_result[2]} error: {db_get_static_data_by_name_result[1]}", currentFuncName(), current_state))
                                            return
                                        current_static_data_payload = db_get_static_data_by_name_result[3]
                                                
                                        if isinstance(current_static_data_payload, list) and all(isinstance(item, dict) for item in current_static_data_payload):
                                            ui.aggrid(prepare_aggrid_for_result(current_static_data_payload)).classes("w-full h-[calc(70vh)]").classes(add=current_state["aggrid_theme"])

                                            # выгрузка должна работать без лимита ?
                                            with ui.row().classes("mt-2"):
                                                async def prepare_export_csv(result, filename):
                                                        prepare_export_result = await run.cpu_bound(export_to_csv, result, filename)
                                                        ui.download(prepare_export_result[0], prepare_export_result[1])
                                                async def prepare_export_xlsx(result, filename):
                                                        prepare_export_result = await run.cpu_bound(export_to_xlsx, result, filename)
                                                        ui.download(prepare_export_result[0], prepare_export_result[1])
                                                ui.button("Export to CSV", on_click= partial(prepare_export_csv, current_static_data_payload, f"static_data_{selected_row["name"]}.csv")).classes("mr-2")
                                                ui.button("Export to XLSX", on_click= partial(prepare_export_xlsx, current_static_data_payload, f"static_data_{selected_row["name"]}.xlsx")).classes("mr-2")      
                                        else:
                                            ui.label("No valid result available").classes("mt-4")
                                    except BaseException as e:
                                        ui.notify("Ошибка отображения статичных данных", type="negative")
                                        error_message = f"fail: {str(e)}"
                                        logger_log(syslog.LOG_ERR, get_log_message(f"error: {str(e)}", currentFuncName(), current_state))
                                        return
                                    
                                    # Удаление статичных данных
                                    async def delete_static_data():
                                        db_delete_static_data_by_name_result = db_delete_static_data_by_name(selected_row["name"], current_state)
                                        if not db_delete_static_data_by_name_result[0]:
                                            ui.notify("Ошибка удаления данных", type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(f"{db_delete_static_data_by_name_result[2]} error: {db_delete_static_data_by_name_result[1]}", currentFuncName(), current_state))
                                        else:
                                            ui.notify(f"Static data {selected_row["name"]} deleted", type="positive")
                                            logger_log(syslog.LOG_INFO, get_log_message(f"Key {selected_row['system']} - {selected_row['account']} deleted", currentFuncName(), current_state))
                                            await draw_static_data(interface_container, current_state)  # Обновление страницы

                                    ui.button("Delete static data", on_click=delete_static_data).classes("mt-2")
                                    
                        grid.on("selectionChanged", static_data_click_actions)

                await refresh_static_data()

                #интерфейс добавление статичных данных
                static_data_upload_container = ui.column().classes("w-full h-full")
                with static_data_upload_container:
                    static_data_name_input = ui.input("New static data name", value="").classes("w-full")
                    static_data_comment_input = ui.input("Comment", value="").classes("w-full")

                    current_upload_text = ""

                    # сначала загрузка, а потом проверяем коммент и имя, пока так

                    async def handle_upload(e: events.UploadEventArguments):
                        """
                        Handles the file upload event, reads the content of the uploaded text file
                        """
                        try:
                            # Read the content of the uploaded file and decode it as UTF-8
                            current_upload_text = e.content.read().decode("utf-8")
                            #uploaded_content.set_content(f"## Uploaded File: {e.name}\n```\n{text_content}\n```")
                            ui.notify(f"File '{e.name}' uploaded successfully.")

                            # валидация введённого в comment
                            validate_comment_result = validate_comment(static_data_comment_input.value, current_state)
                            if validate_comment_result[0] == False:
                                ui.notify(f"Ошибка валидации комментария: {validate_comment_result[1]}", type="negative")
                                logger_log(syslog.LOG_ERR, get_log_message(validate_comment_result[1], currentFuncName(), current_state))
                                return
                            
                            # валидация введённого в comment
                            validate_itemname_result = validate_itemname(static_data_name_input.value, current_state)
                            if validate_itemname_result[0] == False:
                                ui.notify(f"Ошибка валидации имени данных: {validate_itemname_result[1]}", type="negative")
                                logger_log(syslog.LOG_ERR, get_log_message(validate_itemname_result[1], currentFuncName(), current_state))
                                return
                            
                            # загрузка данных в базу
                            db_upload_static_data_result = db_upload_static_data(static_data_name_input.value, static_data_comment_input.value, current_upload_text, current_state)
                            if db_upload_static_data_result[0] == False:
                                ui.notify(f"Ошибка импорта данных: {db_upload_static_data_result[1]}", type="negative")
                                logger_log(syslog.LOG_ERR, get_log_message(db_upload_static_data_result[1], currentFuncName(), current_state))
                                return
                            
                            ui.notify(f"Data imported successfully.", type="positive")
                            
                        except Exception as error:
                            ui.notify(f"Error processing file: {error}", type="negative")

                        await draw_static_data(interface_container, current_state)  # Обновление страницы

                    ui.upload(on_upload=handle_upload).props('accept=".txt,.csv"').classes("max-w-full")

        return True, "OK", currentFuncName(), None

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None

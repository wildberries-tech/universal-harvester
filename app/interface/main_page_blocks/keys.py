import syslog
import sqlite3
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from nicegui import ui, app, run
from app.validation import validate_key_fields, validate_comment
from app.database.keys import db_get_keys, fetch_all_keys, update_key_field, create_key, delete_key
from app.crptgrphy import encrypt
from app.database.users import *
from typing import Tuple, List, Dict, Optional



# Основная функция отрисовки
async def draw_keys(interface_container: ui.card, current_state: dict) -> Tuple[bool, str, str, None]:
    try:
        # Логирование начала работы
        logger_log(syslog.LOG_INFO, get_log_message("Starting draw_keys", currentFuncName(), current_state))

        # Очистка контейнера перед отрисовкой
        interface_container.clear()

        # Проверка роли keys_admin
        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = await run.io_bound(fetch_user_data, current_user, current_state)
        if not user_success:
            logger_log(syslog.LOG_ERR, get_log_message(user_msg, currentFuncName(), current_state))
            return False, user_msg, currentFuncName(), None

        is_admin = False
        if "keys_admin" in user_data["roles"]:
            is_admin = True
        if "fullmaster" in user_data["roles"]:
            is_admin = True

        if is_admin == False:
            with interface_container:
                with ui.column().classes("w-full"):
                    ui.label("Access Denied").classes("text-h5")
                    ui.label("You need the 'keys_admin' role to access this page.")
            return True, "OK", currentFuncName(), None

        # Получение всех ключей
        keys_success, keys_msg, _, all_keys = await run.io_bound(fetch_all_keys,current_state)
        if not keys_success:
            logger_log(syslog.LOG_ERR, get_log_message(keys_msg, currentFuncName(), current_state))
            return False, keys_msg, currentFuncName(), None
        key_list = [f"{key["system"]}&{key["account"]}" for key in all_keys]
        with interface_container:
            # Основной контейнер с ограниченной шириной
            with ui.column().classes("w-full"):
                ui.label("Keys Management").classes("text-h5 mb-4")

                # Таблица ключей с помощью ui.aggrid
                grid_data = [
                    {"system": key["system"], "account": key["account"], "key": key["key"], "comment": key["comment"]}
                    for key in all_keys
                ]
                grid = ui.aggrid({
                    "columnDefs": [
                        {"headerName": "System", "field": "system", "filter": True, "sortable": True},
                        {"headerName": "Account", "field": "account", "filter": True, "sortable": True},
                        {"headerName": "Key", "field": "key"},  # Нет фильтрации по ключу
                        {"headerName": "Comment", "field": "comment", "filter": True, "sortable": True},
                    ],
                    "rowData": grid_data,
                    "rowSelection": "single",
                    "pagination": True,
                    "paginationPageSize": 10,
                }).classes("w-full h-96")
                grid.classes(add=current_state["aggrid_theme"])

                # Контейнер для редактирования выбранного ключа
                edit_container = ui.column().classes("w-full mt-4")
                
                async def update_edit_interface():
                    edit_container.clear()
                    selected_row = (await grid.get_selected_row()) or {}
                    if not selected_row:
                        return
                    # Получаем реальные данные ключа из all_keys
                    key_data = next(k for k in all_keys if k["system"] == selected_row["system"] and k["account"] == selected_row["account"])
                    with edit_container:
                        with ui.card().classes("w-full"):
                            ui.label(f"Editing Key: {selected_row['system']} - {selected_row['account']}").classes("text-h6")
                            with ui.grid(columns=2).classes("w-full"):
                                key_input = ui.input("New Key (will be encrypted)", password=True, value="").classes("w-full")
                                comment_input = ui.input("Comment", value=key_data["comment"])

                            # Обновление ключа
                            async def update_key():
                                if key_input.value:
                                    encrypt_result = encrypt(key_input.value, current_state)
                                    if encrypt_result[0] == False:
                                        ui.notify(encrypt_result[1], type="negative")
                                        logger_log(syslog.LOG_ERR, get_log_message(encrypt_result[1], currentFuncName(), current_state))
                                        return

                                    encrypted_key = encrypt_result[3]
                                    upd_success, upd_msg, _, _ = update_key_field(
                                        selected_row["system"], selected_row["account"], "key", encrypted_key, current_state
                                    )
                                    if not upd_success:
                                        ui.notify(upd_msg, type="negative")
                                        logger_log(syslog.LOG_ERR, get_log_message(upd_msg, currentFuncName(), current_state))
                                        return
                                    
                                # валидация введённого в comment
                                validate_comment_result = validate_comment(comment_input.value, current_state)
                                if validate_comment_result[0] == False:
                                    ui.notify(upd_msg, type="negative")
                                    logger_log(syslog.LOG_ERR, get_log_message(validate_comment_result[0], currentFuncName(), current_state))
                                    return

                                upd_success, upd_msg, _, _ = update_key_field(selected_row["system"], selected_row["account"], "comment", comment_input.value, current_state)
                                if not upd_success:
                                    ui.notify(upd_msg, type="negative")
                                    logger_log(syslog.LOG_ERR, get_log_message(upd_msg, currentFuncName(), current_state))
                                else:
                                    ui.notify("Key updated successfully!", type="positive")
                                    logger_log(syslog.LOG_INFO, get_log_message("Key updated", currentFuncName(), current_state))
                                    draw_keys(interface_container, current_state)  # Обновление страницы
                            ui.button("Update Key", on_click=update_key).classes("mt-2")

                            # Удаление ключа
                            async def delete_selected_key():
                                del_success, del_msg, _, _ = delete_key(selected_row["system"], selected_row["account"], current_state)
                                if not del_success:
                                    ui.notify(del_msg, type="negative")
                                    logger_log(syslog.LOG_ERR, get_log_message(del_msg, currentFuncName(), current_state))
                                else:
                                    ui.notify(f"Key {selected_row['system']} - {selected_row['account']} deleted", type="positive")
                                    logger_log(syslog.LOG_INFO, get_log_message(f"Key {selected_row['system']} - {selected_row['account']} deleted", currentFuncName(), current_state))
                                    draw_keys(interface_container, current_state)  # Обновление страницы
                            ui.button("Delete Key", on_click=delete_selected_key).classes("mt-2")

                grid.on("selectionChanged", update_edit_interface)

                # Добавление нового ключа
                with ui.card().classes("w-full mt-4"):
                    ui.label("Add New Key").classes("text-h6")
                    with ui.grid(columns=2).classes("w-full"):
                        new_system = ui.input("System")
                        new_account = ui.input("Account")
                        new_key = ui.input("Key (will be encrypted)", password=True, value="").classes("w-full")
                        new_comment = ui.input("Comment")
                    async def add_new_key():
                        val_success, val_msg, _, _ = validate_key_fields(key_list, new_system.value, new_account.value, new_key.value, new_comment.value, current_state)
                        if not val_success:
                            ui.notify(val_msg, type="negative")
                            return
                        
                        encrypt_result = encrypt(new_key.value, current_state)
                        if encrypt_result[0] == False:
                            ui.notify(encrypt_result[1], type="negative")
                            logger_log(syslog.LOG_ERR, get_log_message(encrypt_result[1], currentFuncName(), current_state))
                            return

                        encrypted_key = encrypt_result[3]

                        create_success, create_msg, _, _ = create_key(
                            new_system.value, new_account.value, encrypted_key, new_comment.value, current_state
                        )
                        if not create_success:
                            ui.notify(create_msg, type="negative")
                            logger_log(syslog.LOG_ERR, get_log_message(create_msg, currentFuncName(), current_state))
                        else:
                            ui.notify(f"Key {new_system.value} - {new_account.value} created", type="positive")
                            logger_log(syslog.LOG_INFO, get_log_message(f"Key {new_system.value} - {new_account.value} created", currentFuncName(), current_state))
                            draw_keys(interface_container, current_state)  # Обновление страницы
                    ui.button("Add Key", on_click=add_new_key).classes("mt-2")

        return True, "OK", currentFuncName(), None

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None   
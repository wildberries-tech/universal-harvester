import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from nicegui import ui, app
from app.validation import validate_itemname, check_json_correct
from app.database.sources import fetch_all_sources, create_source, update_source_field, delete_source
from app.database.users import fetch_user_data
from typing import Tuple, List, Dict, Optional
from app.engine.engine import *


# Валидация данных
# def validate_source_fields(sourcename: str, sourcetype: str, json_data: str) -> Tuple[bool, str, str, None]:
#     func_name = "validate_source_fields"
#     if not sourcename or not json_data or not sourcetype:
#         return False, "Sourcename and JSON must not be empty", func_name, None
#     try:
#         json.loads(json_data)
#         return True, "OK", func_name, None
#     except json.JSONDecodeError:
#         return False, "Invalid JSON format", func_name, None

# Основная функция отрисовки
def draw_sources(interface_container: ui.card, current_state: dict) -> Tuple[bool, str, str, None]:
    func_name = "draw_sources"
    try:
        # Логирование начала работы
        logger_log(syslog.LOG_INFO, get_log_message("Starting draw_sources", func_name, current_state))

        # Очистка контейнера перед отрисовкой
        interface_container.clear()

        # Проверка роли sources_admin
        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = fetch_user_data(current_user, current_state)
        if not user_success:
            logger_log(syslog.LOG_ERR, get_log_message(user_msg, func_name, current_state))
            return False, user_msg, func_name, None

        is_admin = False
        if "sources_admin" in user_data["roles"]:
            is_admin = True
        if "fullmaster" in user_data["roles"]:
            is_admin = True

        if is_admin == False:
            with interface_container:
                with ui.column().classes("w-full"):
                    ui.label("Access Denied").classes("text-h5")
                    ui.label("You need the 'sources_admin' role to access this page.")
            return True, "OK", func_name, None

        # Получение всех источников  engine_source_parameters_validator(ENGINE_SOURCES_AND_FUNCTIONS_MAP, json_input.value, current_state)
        sources_success, sources_msg, _, all_sources = fetch_all_sources(current_state)
        if not sources_success:
            logger_log(syslog.LOG_ERR, get_log_message(sources_msg, func_name, current_state))
            return False, sources_msg, func_name, None

        with interface_container:
            # Основной контейнер с ограниченной шириной
            with ui.column().classes("w-full"):
                ui.label("Sources Management").classes("text-h5 mb-4")

                # Список источников через ui.select
                source_options = {source["sourcename"]: source["sourcename"] for source in all_sources}
                with ui.card().classes("w-full"):
                    ui.label("Sources List").classes("text-h6")
                    selected_source = ui.select(source_options, label="Select Source", value=None).classes("w-full")
                    edit_container = ui.column().classes("w-full mt-4")

                    def update_edit_interface():
                        edit_container.clear()
                        if not selected_source.value:
                            return
                        source = next(s for s in all_sources if s["sourcename"] == selected_source.value)
                        with edit_container:
                            with ui.card().classes("w-full"):
                                ui.label(f"Editing Source: {source['sourcename']}").classes("text-h6")
                                with ui.grid(columns=2).classes("w-full"):
                                    ui.label("Sourcename:")
                                    ui.label(source["sourcename"])
                                    ui.label("Type:")
                                    type_input = ui.input("Type", value=source["type"]).classes("w-full")
                                ui.label("JSON:")
                                json_input = ui.codemirror(
                                        value=source["json"], 
                                        language='JSON', 
                                        line_wrapping=True, theme = current_state["codemirror_theme"]
                                    ).style('width: 100%; height: 24rem')

                                # Обновление полей
                                async def update_source():
                                    try:
                                        # проверяем json
                                        if check_json_correct(json_input.value) == False:
                                            error_message = f"wrong json"
                                            logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
                                            ui.notify(error_message, type="negative")
                                            return
                                        # Обновление type
                                        validate_type_result = validate_itemname(type_input.value, current_state)
                                        if validate_type_result[0] == False:
                                            error_message = f"wrong type: {validate_type_result[1]}"
                                            logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
                                            ui.notify(error_message, type="negative")
                                            return
                                        
                                        upd_success, upd_msg, _, _ = update_source_field(
                                            source["sourcename"], "type", type_input.value, current_state
                                        )
                                        if not upd_success:
                                            ui.notify(upd_msg, type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(upd_msg, func_name, current_state))
                                            return
                                        # Обновление json
                                        upd_success, upd_msg, _, _ = update_source_field(
                                            source["sourcename"], "json", json_input.value, current_state
                                        )
                                        if not upd_success:
                                            ui.notify(upd_msg, type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(upd_msg, func_name, current_state))
                                        else:
                                            ui.notify("Source updated successfully!", type="positive")
                                            logger_log(syslog.LOG_INFO, get_log_message("Source updated", func_name, current_state))
                                            draw_sources(interface_container, current_state)  # Обновление страницы
                                    except json.JSONDecodeError:
                                        ui.notify("Invalid JSON format", type="negative")
                                ui.button("Update Source", on_click=update_source).classes("mt-2")

                                # Валидация JSON
                                async def validate_json():
                                    val_success, val_msg, _, val_result = engine_source_parameters_validator(ENGINE_SOURCES_AND_FUNCTIONS_MAP, json_input.value, current_state)
                                    if not val_success or not val_result:
                                        ui.notify(f"Validation failed: {val_msg}", type="negative")
                                        logger_log(syslog.LOG_ERR, get_log_message(f"Validation failed: {val_msg}", func_name, current_state))
                                    else:
                                        ui.notify("Source JSON is valid!", type="positive")
                                        logger_log(syslog.LOG_INFO, get_log_message("JSON validated successfully", func_name, current_state))
                                ui.button("Validate source JSON", on_click=validate_json).classes("mt-2")

                                # Удаление источника
                                async def delete_selected_source():
                                    # на всякий случай провалидировать текущий sourcename
                                    validate_sourcename_result = validate_itemname(source["sourcename"], current_state)
                                    if validate_sourcename_result[0] == False:
                                        error_message = f"wrong sourcename: {validate_sourcename_result[1]}"
                                        logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
                                        ui.notify(error_message, type="negative")
                                        return

                                    del_success, del_msg, _, _ = delete_source(source["sourcename"], current_state)
                                    if not del_success:
                                        ui.notify(del_msg, type="negative")
                                        logger_log(syslog.LOG_ERR, get_log_message(del_msg, func_name, current_state))
                                    else:
                                        ui.notify(f"Source {source['sourcename']} deleted", type="positive")
                                        logger_log(syslog.LOG_INFO, get_log_message(f"Source {source['sourcename']} deleted", func_name, current_state))
                                        draw_sources(interface_container, current_state)  # Обновление страницы
                                ui.button("Delete Source", on_click=delete_selected_source).classes("mt-2")

                    selected_source.on("update:model-value", update_edit_interface)

                # Добавление нового источника
                with ui.card().classes("w-full mt-4"):
                    ui.label("Add New Source").classes("text-h6")
                    with ui.grid(columns=2).classes("w-full"):
                        new_sourcename = ui.input("Sourcename")
                        new_type = ui.input("Type")
                    new_json = ui.codemirror(
                            value="{}", 
                            language='JSON', 
                            line_wrapping=True, theme = current_state["codemirror_theme"]
                        ).style('width: 100%; height: 24rem')
                    async def add_new_source():
                        validate_sourcename_result = validate_itemname(new_sourcename.value, current_state)
                        if validate_sourcename_result[0] == False:
                            error_message = f"wrong sourcename: {validate_sourcename_result[1]}"
                            logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
                            ui.notify(error_message, type="negative")
                            return
                        
                        validate_type_result = validate_itemname(new_type.value, current_state)
                        if validate_type_result[0] == False:
                            error_message = f"wrong type: {validate_type_result[1]}"
                            logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
                            ui.notify(error_message, type="negative")
                            return
                        
                        if check_json_correct(new_json.value) == False:
                            error_message = f"wrong json"
                            logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
                            ui.notify(error_message, type="negative")
                            return

                        create_success, create_msg, _, _ = create_source(new_sourcename.value, new_type.value, new_json.value, current_state)
                        if not create_success:
                            ui.notify(create_msg, type="negative")
                            logger_log(syslog.LOG_ERR, get_log_message(create_msg, func_name, current_state))
                        else:
                            ui.notify(f"Source {new_sourcename.value} created", type="positive")
                            logger_log(syslog.LOG_INFO, get_log_message(f"Source {new_sourcename.value} created", func_name, current_state))
                            draw_sources(interface_container, current_state)  # Обновление страницы
                    ui.button("Add Source", on_click=add_new_source).classes("mt-2")

        return True, "OK", func_name, None

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
        return False, error_message, func_name, None
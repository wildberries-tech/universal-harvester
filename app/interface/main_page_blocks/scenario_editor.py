import syslog
import uuid
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from nicegui import ui
from app.database.steps import db_get_steps, db_upsert_step
from app.engine.engine import engine_hasshin
from app.engine.steps import *
from app.database.sources import db_get_sources

from typing import Tuple, List, Dict, Optional
import time

from app.database.users import fetch_user_data
from app.database.steps import fetch_all_steps, update_step_field, create_step, delete_step
from app.database.sources import fetch_all_sources
from app.database.tasks import db_get_task_by_id
from app.engine.storage import read_step_from_storage

from app.database.scenarios import fetch_scenarios, db_update_scenario, db_insert_scenario

from app.interface.additional import prepare_aggrid_for_result, export_to_csv, export_to_xlsx, create_fullscreen_result_page
from app.validation import validate_data_for_scenario_update, validate_data_for_scenario_insert


# Основная функция отрисовки
def draw_scenario_editor(interface_container: ui.card, current_state: dict) -> Tuple[bool, str, str, None]:
    try:
        # Логирование начала работы
        logger_log(syslog.LOG_INFO, get_log_message("Starting scenario editor", currentFuncName(), current_state))

        # Очистка контейнера перед отрисовкой
        interface_container.clear()

        # Получение данных пользователя
        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = fetch_user_data(current_user, current_state)
        if not user_success:
            logger_log(syslog.LOG_ERR, get_log_message(user_msg, currentFuncName(), current_state))
            return False, user_msg, currentFuncName(), None
        user_roles = user_data["roles"]

        has_scenario_editor_admin = False
        if "scenario_editor_admin" in user_data["roles"]:
            has_scenario_editor_admin = True
        if "fullmaster" in user_data["roles"]:
            has_scenario_editor_admin = True


        # Получение всех шагов и источников
        fetch_scenarios_result = fetch_scenarios(has_scenario_editor_admin, current_state)
        if fetch_scenarios_result[0] == False:
            error_message = f"fail: {fetch_scenarios_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None
        all_scenarios = fetch_scenarios_result[3]


        # Фильтрация шагов по ролям
        visible_scenarios = [scenario for scenario in all_scenarios if has_scenario_editor_admin or any(role in user_roles for role in scenario["roles"])]


        with interface_container:
            # Основной контейнер
            with ui.column().classes("w-full"):
                ui.label("Scenario Editor").classes("text-h5 mb-4")

                # Список шагов через ui.select
                scenario_options = {scenario["scenario_name"]: scenario["scenario_name"] for scenario in all_scenarios}
                with ui.card().classes("w-full"):
                    ui.label("Scenarios list").classes("text-h6")
                    selected_scenario = ui.select(scenario_options, label="Select Scenario", value=None).classes("w-full")
                    scenario_container = ui.column().classes("w-full mt-4")

                    def update_scenario_interface():
                        scenario_container.clear()
                        if not selected_scenario.value:
                            return
                        scenario = next(s for s in all_scenarios if s["scenario_name"] == selected_scenario.value)
                        # запоминаем последний выбранный
                        current_state["last_selected_scenario_in_editor"] = scenario["scenario_name"]
                        # Проверка соответствия sourcename и sourcetype
                        
                        with scenario_container:
                            with ui.card().classes("w-full"):
                                ui.label(f"Scenario: {scenario['scenario_name']}").classes("text-h6")
                                with ui.grid(columns=2).classes("w-full"):
                                    ui.label("Scenario name:")
                                    ui.label(scenario["scenario_name"])
                                    ui.label("Roles:")
                                    ui.label(", ".join(scenario["roles"]))
                                ui.label("JSON:")
                                json_show = ui.codemirror(
                                            value=json.dumps(scenario["json"], indent = 2, ensure_ascii=False),
                                            language='JSON',
                                            line_wrapping=True, theme = current_state["codemirror_theme"]
                                        ).style('width: 100%; height: 96rem')
                                json_show.enabled = False

                    selected_scenario.on("update:model-value", update_scenario_interface)

                    # Админский функционал
                    if has_scenario_editor_admin:
                        ui.label("Admin Controls").classes("text-h5 mt-6 mb-4")

                        # Редактирование сценария
                        with ui.card().classes("w-full"):
                            ui.label("Edit Selected Scenario").classes("text-h6")
                            edit_scenario_container = ui.column().classes("w-full mt-4")

                            def update_edit_scenario_interface():
                                edit_scenario_container.clear()
                                if not selected_scenario.value:
                                    return
                                scenario = next(s for s in all_scenarios if s["scenario_name"] == selected_scenario.value)
                                with edit_scenario_container:
                                    with ui.grid(columns=2).classes("w-full"):
                                        scenario_name_input = ui.input("Scenario name", value=scenario["scenario_name"]).classes("w-full")
                                        roles_input = ui.input("Roles (comma-separated)", value=", ".join(scenario["roles"])).classes("w-full")
                                    json_input = ui.codemirror(
                                            value=json.dumps(scenario["json"], indent = 2, ensure_ascii=False),
                                            language='JSON',
                                            line_wrapping=True, theme = current_state["codemirror_theme"]
                                        ).style('width: 100%; height: 96rem')

                                    async def update_scenario_action():
                                        new_roles = [r.strip() for r in roles_input.value.split(",") if r.strip()]
                                        
                                        data = {
                                            "scenario_original_name":scenario["scenario_name"],
                                            "scenario_new_name": scenario_name_input.value,
                                            "roles": json.dumps(new_roles, ensure_ascii=False),
                                            "json": json_input.value
                                        }

                                        validate_data_for_scenario_update_result = validate_data_for_scenario_update(data, current_state)
                                        if validate_data_for_scenario_update_result[0] == False:
                                            error_message = f"data validation error: {validate_data_for_scenario_update_result[1]}"
                                            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                                            ui.notify(error_message, type="negative")
                                            return
                                        
                                        db_update_scenario_result = db_update_scenario(data, current_state)
                                        if db_update_scenario_result[0] == False:
                                            ui.notify(db_update_scenario_result[1], type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(db_update_scenario_result[1], currentFuncName(), current_state))
                                            return

                                        ui.notify("Step updated successfully!", type="positive")
                                        logger_log(syslog.LOG_INFO, get_log_message("Step updated", currentFuncName(), current_state))

                                        draw_scenario_editor(interface_container, current_state)  # Обновление страницы

                                    ui.button("Update Scenario", on_click=update_scenario_action).classes("mt-2")

                            selected_scenario.on("update:model-value", update_edit_scenario_interface)

                        # Добавление нового сценария
                        with ui.card().classes("w-full mt-4"):
                            ui.label("Add New Scenario").classes("text-h6")
                            with ui.grid(columns=2).classes("w-full"):
                                new_scenario_name = ui.input("Scenario name").classes("w-full")
                                new_roles = ui.input("Roles (comma-separated)").classes("w-full")
                            new_json = ui.codemirror(
                                    value="{}", 
                                    language='JSON', 
                                    line_wrapping=True, theme = current_state["codemirror_theme"]
                                ).style('width: 100%; height: 96rem')
                            
                            async def add_new_scenario():
                                new_roles_list = [r.strip() for r in new_roles.value.split(",") if r.strip()]


                                data = {
                                    "scenario_new_name": new_scenario_name.value,
                                    "roles": json.dumps(new_roles_list, ensure_ascii=False),
                                    "json": new_json.value
                                }
                                validate_data_for_scenario_insert_result = validate_data_for_scenario_insert(data, current_state)
                                if validate_data_for_scenario_insert_result[0] == False:
                                    error_message = f"data validation error: {validate_data_for_scenario_insert_result[1]}"
                                    logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                                    ui.notify(error_message, type="negative")
                                    return
                                
                                db_insert_scenario_result = db_insert_scenario(data, current_state)
                                if db_insert_scenario_result[0] == False:
                                    ui.notify(db_insert_scenario_result[1], type="negative")
                                    logger_log(syslog.LOG_ERR, get_log_message(db_insert_scenario_result[1], currentFuncName(), current_state))
                                else:
                                    ui.notify(f"Scenario {new_scenario_name.value} created", type="positive")
                                    logger_log(syslog.LOG_INFO, get_log_message(f"Scenario {new_scenario_name.value} created", currentFuncName(), current_state))
                                    draw_scenario_editor(interface_container, current_state)  # Обновление страницы

                            ui.button("Add Scenario", on_click=add_new_scenario).classes("mt-2")

                        # Копирование сценария
                        with ui.card().classes("w-full mt-4"):
                            ui.label("Copy Selected Scenario").classes("text-h6")
                            copy_step_container = ui.column().classes("w-full mt-4")

                            def update_copy_step_interface():
                                copy_step_container.clear()
                                if not selected_scenario.value:
                                    return
                                scenario = next(s for s in all_scenarios if s["scenario_name"] == selected_scenario.value)
                                with copy_step_container:
                                    new_copy_scenario_name = ui.input("New Scenario name", value=f"{scenario["scenario_name"]}_copy").classes("w-full")
                                    async def copy_step_action():
                                        data = {
                                            "scenario_new_name": new_copy_scenario_name.value,
                                            "roles": json.dumps(scenario["roles"], ensure_ascii=False),
                                            "json": json.dumps(scenario["json"], ensure_ascii=False)
                                        }
                                        validate_data_for_scenario_insert_result = validate_data_for_scenario_insert(data, current_state)
                                        if validate_data_for_scenario_insert_result[0] == False:
                                            error_message = f"data validation error: {validate_data_for_scenario_insert_result[1]}"
                                            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                                            ui.notify(error_message, type="negative")
                                            return
                                        
                                        db_insert_scenario_result = db_insert_scenario(data, current_state)
                                        if db_insert_scenario_result[0] == False:
                                            error_message = f"Scenario copy error: {db_insert_scenario_result[1]}"
                                            ui.notify(error_message, type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
                                        else:
                                            ui.notify(f"Scenario {new_scenario_name.value} copied from {scenario["scenario_name"]}", type="positive")
                                            logger_log(syslog.LOG_INFO, get_log_message(f"Scenario {new_scenario_name.value} copied from {scenario["scenario_name"]}", currentFuncName(), current_state))
                                            draw_scenario_editor(interface_container, current_state)  # Обновление страницы

                                    ui.button("Copy Scenario", on_click=copy_step_action).classes("mt-2")

                            selected_scenario.on("update:model-value", update_copy_step_interface)
                    # проверяем последний выбранный
                    if "last_selected_scenario_in_editor" in current_state:
                        for scnr in all_scenarios:
                            if scnr["scenario_name"] == current_state["last_selected_scenario_in_editor"]:
                                selected_scenario.set_value(current_state["last_selected_scenario_in_editor"])
                                update_scenario_interface()
                                if has_scenario_editor_admin:
                                    update_edit_scenario_interface()
                        


        return True, "OK", currentFuncName(), None

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
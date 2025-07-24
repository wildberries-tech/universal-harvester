import syslog
import uuid
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from nicegui import ui, run
from app.validation import validate_step_fields
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

from app.interface.additional import prepare_aggrid_for_result, export_to_csv, export_to_xlsx, create_fullscreen_result_page

# Предполагаемые заглушки для функций (уточните, если они уже есть)
def generate_parameters_json(step: Dict) -> str:
    # Заглушка для генерации parameters_json
    return json.dumps({"step": step["stepname"], "example": "parameters"}, indent=2, ensure_ascii=False)

def run_step(stepname: str, sourcename: str, step_json_string: str, parameters_json_string: str, in_scenario: str, scenario: dict, current_state: dict) -> List[Dict]:
    ############################################
    # Запуск выполнения шага
    # cначала создаём новый task_id и подготавливаем данные
    ############################################
    CURRENT_TARGET_ID = str(uuid.uuid4())

    data = {
        "id":CURRENT_TARGET_ID,
        "pid":-1,
        "status_code":0,
        "status":"New",
        "step_name":stepname,
        "source_name":sourcename,
        "username":current_state["username"],
        "timestamp_start": currentTimestamp(),
        "timestamp_stop": "-",
        "in_scenario": in_scenario,
        "json":json.dumps({
            "step":json.loads(step_json_string),
            "parameters":json.loads(parameters_json_string),
            "scenario":scenario,
            "need_scenario_notify": False
        }, indent = 0, ensure_ascii=False)
    }


    ##########################################
    # Собственно запуск движка
    ##########################################
    engine_hasshin_result = engine_hasshin(
        data, 
        current_state)
    if engine_hasshin_result[0] == False:
        error_message = f"Step start execution error: {engine_hasshin_result[1]}"
        ui.notify(error_message, color='negative')
        return CURRENT_TARGET_ID, [{"message": error_message}]
    else:
        ui.notify(f"Step start execution OK")

    ##########################################
    # ожидаем выполнение шага
    ##########################################

    # task_complete_flag = False

    # while(task_complete_flag == False):
    #     db_get_task_by_id_result = db_get_task_by_id({"target_id":CURRENT_TARGET_ID}, current_state)
    #     if db_get_task_by_id_result[0] == False:
    #         error_message = f"db_get_task_by_id_result (interactive) is False: {db_get_task_by_id_result[1]}"
    #         logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(),current_state))
    #         return CURRENT_TARGET_ID, [{"message": error_message}]
    #     current_target_status_code = db_get_task_by_id_result[3][2]
    #     if current_target_status_code == 1: # статус успешного завершения
    #         task_complete_flag = True
    #     elif current_target_status_code > 1 or current_target_status_code == 0: # ждём у моря погоды
    #         time.sleep(1) 
    #     else: # при этих статусах ждать выполнения не стоит
    #         error_message = f"Step execution error (interactive): {db_get_task_by_id_result[3][3]}"
    #         logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(),current_state))
    #         return CURRENT_TARGET_ID, [{"message": error_message}]

    ##########################################
    # Подгружаем полученный результат из хранилища
    ##########################################
    # loaded_task_data_result = read_step_from_storage({"target_id":CURRENT_TARGET_ID} ,current_state)
    # if loaded_task_data_result[0] == False:
    #     error_message = f"loaded_task_data_result (interactive) is False: {loaded_task_data_result[1]}"
    #     logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(),current_state))
    #     return CURRENT_TARGET_ID, [{"message": error_message}]
    # loaded_task_data = loaded_task_data_result[3]["data"]
    
    return CURRENT_TARGET_ID, None#, loaded_task_data


# Основная функция отрисовки
async def draw_steps(interface_container: ui.card, current_state: dict) -> Tuple[bool, str, str, None]:
    try:
        # Логирование начала работы
        logger_log(syslog.LOG_INFO, get_log_message("Starting draw_steps", currentFuncName(), current_state))

        # Очистка контейнера перед отрисовкой
        interface_container.clear()

        # Получение данных пользователя
        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = await run.io_bound(fetch_user_data, current_user, current_state)
        if not user_success:
            logger_log(syslog.LOG_ERR, get_log_message(user_msg, currentFuncName(), current_state))
            return False, user_msg, currentFuncName(), None
        user_roles = user_data["roles"]

        has_steps_admin = False
        if "steps_admin" in user_data["roles"]:
            has_steps_admin = True
        if "fullmaster" in user_data["roles"]:
            has_steps_admin = True


        # Получение всех шагов и источников
        steps_success, steps_msg, _, all_steps = await run.io_bound(fetch_all_steps, current_state)
        if not steps_success:
            logger_log(syslog.LOG_ERR, get_log_message(steps_msg, currentFuncName(), current_state))
            return False, steps_msg, currentFuncName(), None
        sources_success, sources_msg, _, all_sources = await run.io_bound(fetch_all_sources, current_state)
        if not sources_success:
            logger_log(syslog.LOG_ERR, get_log_message(sources_msg, currentFuncName(), current_state))
            return False, sources_msg, currentFuncName(), None
        all_step_list = [step["stepname"] for step in all_steps]
        # Фильтрация шагов по ролям
        visible_steps = [step for step in all_steps if has_steps_admin or any(role in user_roles for role in step["roles"])]

        async def open_fullscreen(task_id: str):
            await create_fullscreen_result_page(task_id, current_state)
            ui.navigate.to(f'/task_fullscreen_result/{task_id}', new_tab=True)

        with interface_container:
            # Основной контейнер
            with ui.column().classes("w-full"):
                ui.label("Steps Management").classes("text-h5 mb-4")
                

                # Список шагов через ui.select
                step_options = {step["stepname"]: step["stepname"] for step in visible_steps}
                with ui.card().classes("w-full"):
                    ui.label("Steps List").classes("text-h6")
                    # Список шагов через grid
                    grid_data = [
                        {
                            "stepname": step["stepname"],
                            "sourcename": step["sourcename"],
                            "sourcetype": step["sourcetype"],
                            "roles": json.dumps(step["roles"], indent=0, ensure_ascii=False)
                        } for step in visible_steps
                    ]
                    grid = ui.aggrid({
                        "defaultColDef": {
                            "wrapText": True,
                            "autoHeight": True,
                        },
                        "columnDefs": [
                            {"headerName": "Name", "field": "stepname", "filter": True, "sortable": True, "minWidth": 150},
                            {"headerName": "Source name", "field": "sourcename", "filter": True, "sortable": True, "minWidth": 150},
                            {"headerName": "Source type", "field": "sourcetype", "filter": True, "sortable": True, "minWidth": 120},
                            {"headerName": "Roles", "field": "roles", "filter": True, "sortable": True, "minWidth": 120},
                        ],
                        "rowData": grid_data,
                        "rowSelection": "single",
                        "pagination": True,
                        "paginationPageSize": 20,
                        "domLayout": "normal",
                    }).classes("w-full h-[calc(70vh)]").classes(add=current_state["aggrid_theme"])

                    
                    #selected_step = ui.select(step_options, label="Select Step", value=None).classes("w-full")
                    step_container = ui.column().classes("w-full mt-4")

                    async def update_step_interface():
                        step_container.clear()
                        # if not selected_step.value:
                        #     return
                        # step = next(s for s in all_steps if s["stepname"] == selected_step.value)
                        selected_row = (await grid.get_selected_row()) or {}
                        if not selected_row:
                            return
                        step = next(s for s in visible_steps if s["stepname"] == selected_row["stepname"])
                        # Проверка соответствия sourcename и sourcetype
                        source = next((s for s in all_sources if s["sourcename"] == step["sourcename"]), None)
                        if source and source["type"] != step["sourcetype"]:
                            ui.notify(
                                f"Warning: Sourcetype '{step['sourcetype']}' does not match source '{step['sourcename']}' type '{source['type']}'",
                                type="warning"
                            )
                        with step_container:
                            with ui.card().classes("w-full"):
                                ui.label(f"Step: {step['stepname']}").classes("text-h6")
                                with ui.grid(columns=2).classes("w-full"):
                                    ui.label("Stepname:")
                                    ui.label(step["stepname"])
                                    ui.label("Sourcename:")
                                    ui.label(step["sourcename"])
                                    ui.label("Sourcetype:")
                                    ui.label(step["sourcetype"])
                                    ui.label("Roles:")
                                    ui.label(", ".join(step["roles"]))
                                ui.label("JSON:")
                                json_show = ui.codemirror(
                                            value=step["json"],
                                            language='JSON',
                                            line_wrapping=True, theme = current_state["codemirror_theme"]
                                        ).style('width: 100%; height: 96rem')
                                json_show.enabled = False

                                # Генерация parameters_json
                                # тоже спрятано от неадминов, можно подумать над ролью step_executor
                                if has_steps_admin:
                                    params_container = ui.column().classes("w-full mt-4")
                                    async def generate_params():
                                        params_container.clear()
                                        with params_container:
                                            get_current_step_parameters_result = await run.io_bound(get_parameters_from_step, "simple", step["stepname"], step["json"],{},0, current_state)
                                            if not get_current_step_parameters_result[0]:
                                                ui.notify(f"Error: {get_current_step_parameters_result[1]}", type="negative")
                                                return
                                            params_json = json.dumps(get_current_step_parameters_result[3], indent=4, ensure_ascii=False)
                                            params_input = ui.codemirror(
                                                value=params_json,
                                                language='JSON',
                                                line_wrapping=True, theme = current_state["codemirror_theme"]
                                            ).style('width: 100%; height: 24rem')

                                            # Запуск шага
                                            result_container = ui.column().classes("w-full mt-4")
                                            async def run_step_action():
                                                result_container.clear()
                                                try:
                                                    json.loads(params_input.value)  # Проверка валидности JSON
                                                    with result_container:
                                                        with ui.spinner(size="lg"):
                                                            scenario = {"empty":True}
                                                            scenario_id = "Null"
                                                            task_id, result = await run.cpu_bound(run_step, step["stepname"], step["sourcename"], json_show.value, params_input.value, scenario_id, scenario, current_state)
                                                    with result_container:
                                                        if task_id:
                                                            ui.label(f"Task {task_id}").classes("text-h6 mt-4")
                                                        if result:
                                                            pass
                                                            # if isinstance(result, list) and all(isinstance(item, dict) for item in result):
                                                            #     ui.label("Result").classes("text-h6 mt-4")
                                                            #     task_result_grid = ui.aggrid(prepare_aggrid_for_result(result)).classes("w-full h-96")
                                                            #     task_result_grid.classes(add=current_state["aggrid_theme"])
                                                            #     with ui.row().classes("mt-2"):
                                                            #         ui.button("Export to CSV", on_click=lambda: export_to_csv(result, f"task_{task_id}_result.csv")).classes("mr-2")
                                                            #         ui.button("Export to XLSX", on_click=lambda: export_to_xlsx(result, f"task_{task_id}_result.xlsx")).classes("mr-2")
                                                            #         ui.button("Open Fullscreen", on_click=lambda: open_fullscreen(task_id)).classes("mr-2")
                                                        else:
                                                            ui.label("No results returned")
                                                except json.JSONDecodeError:
                                                    ui.notify("Invalid parameters JSON", type="negative")
                                            ui.button("Run Step", on_click=run_step_action).classes("mt-2")

                                    ui.button("Generate Parameters", on_click=generate_params).classes("mt-2")

                    #selected_step.on("update:model-value", update_step_interface)
                    grid.on("selectionChanged", update_step_interface)
                    # Админский функционал
                    if has_steps_admin:
                        ui.label("Admin Controls").classes("text-h5 mt-6 mb-4")

                        # Редактирование шага
                        with ui.card().classes("w-full"):
                            ui.label("Edit Selected Step").classes("text-h6")
                            edit_step_container = ui.column().classes("w-full mt-4")

                            async def update_edit_step_interface():
                                edit_step_container.clear()

                                selected_row = (await grid.get_selected_row()) or {}
                                if not selected_row:
                                    return
                                step = next(s for s in visible_steps if s["stepname"] == selected_row["stepname"])
                                
                                with edit_step_container:
                                    with ui.grid(columns=2).classes("w-full"):
                                        stepname_input = ui.input("Stepname", value=step["stepname"]).classes("w-full")
                                        sourcename_input = ui.select(
                                            {s["sourcename"]: s["sourcename"] for s in all_sources},
                                            label="Sourcename",
                                            value=step["sourcename"]
                                        ).classes("w-full")
                                        sourcetype_input = ui.select(
                                            {s["type"]: s["type"] for s in all_sources},
                                            label="Sourcetype",
                                            value=step["sourcetype"]
                                        ).classes("w-full")
                                        roles_input = ui.input("Roles (comma-separated)", value=", ".join(step["roles"])).classes("w-full")
                                    json_input = ui.codemirror(
                                            value=step["json"],
                                            language='JSON',
                                            line_wrapping=True, theme = current_state["codemirror_theme"]
                                        ).style('width: 100%; height: 96rem')

                                    async def update_step_action():
                                        new_roles = [r.strip() for r in roles_input.value.split(",") if r.strip()]
                                        val_success, val_msg, _, _ = validate_step_fields(
                                            stepname_input.value, sourcename_input.value, sourcetype_input.value, new_roles, json_input.value, all_sources, current_state
                                        )
                                        if not val_success:
                                            ui.notify(val_msg, type="negative")
                                            return
                                        fields = {
                                            "stepname": stepname_input.value,
                                            "sourcename": sourcename_input.value,
                                            "sourcetype": sourcetype_input.value,
                                            "roles": new_roles,
                                            "json": json_input.value
                                        }
                                        for field, value in fields.items():
                                            upd_success, upd_msg, _, _ = await run.io_bound(update_step_field, step["stepname"], field, value, current_state)
                                            if not upd_success:
                                                ui.notify(upd_msg, type="negative")
                                                logger_log(syslog.LOG_ERR, get_log_message(upd_msg, currentFuncName(), current_state))
                                                return
                                        ui.notify("Step updated successfully!", type="positive")
                                        logger_log(syslog.LOG_INFO, get_log_message("Step updated", currentFuncName(), current_state))
                                        
                                        # запоминаем исходные параметры, чтобы определить, нужно ли рефрешить страницу
                                        # страницу не нужно рефрешить, если изменяется только json
                                        if stepname_input.value == step["stepname"] and sourcename_input.value == step["sourcename"] and sourcetype_input.value == step["sourcetype"] and new_roles == ", ".join(step["roles"]):
                                            pass
                                            # зачем обновлять страницу, если поменяется только json, который в таблице не отображается?
                                        else:
                                            draw_steps(interface_container, current_state)  # Обновление страницы

                                    ui.button("Update Step", on_click=update_step_action).classes("mt-2")

                            #selected_step.on("update:model-value", update_edit_step_interface)
                            grid.on("selectionChanged", update_edit_step_interface)

                        # Добавление нового шага
                        with ui.card().classes("w-full mt-4"):
                            ui.label("Add New Step").classes("text-h6")
                            with ui.grid(columns=2).classes("w-full"):
                                new_stepname = ui.input("Stepname").classes("w-full")
                                new_sourcename = ui.select(
                                    {s["sourcename"]: s["sourcename"] for s in all_sources},
                                    label="Sourcename"
                                ).classes("w-full")
                                new_sourcetype = ui.select(
                                    {s["type"]: s["type"] for s in all_sources},
                                    label="Sourcetype"
                                ).classes("w-full")
                                new_roles = ui.input("Roles (comma-separated)").classes("w-full")
                            new_json = ui.codemirror(
                                    value="{}", 
                                    language='JSON', 
                                    line_wrapping=True, theme = current_state["codemirror_theme"]
                                ).style('width: 100%; height: 96rem')
                            async def add_new_step():
                                new_roles_list = [r.strip() for r in new_roles.value.split(",") if r.strip()]
                                if new_stepname.value in all_step_list:
                                    ui.notify("Step already exists", type="negative")
                                    return
                                val_success, val_msg, _, _ = validate_step_fields(
                                    new_stepname.value, new_sourcename.value, new_sourcetype.value, new_roles_list, new_json.value, all_sources, current_state
                                )
                                if not val_success:
                                    ui.notify(val_msg, type="negative")
                                    return
                                create_success, create_msg, _, _ = create_step(
                                    new_stepname.value, new_sourcename.value, new_sourcetype.value, new_roles_list, new_json.value, current_state
                                )
                                if not create_success:
                                    ui.notify(create_msg, type="negative")
                                    logger_log(syslog.LOG_ERR, get_log_message(create_msg, currentFuncName(), current_state))
                                else:
                                    ui.notify(f"Step {new_stepname.value} created", type="positive")
                                    logger_log(syslog.LOG_INFO, get_log_message(f"Step {new_stepname.value} created", currentFuncName(), current_state))
                                    draw_steps(interface_container, current_state)  # Обновление страницы
                            ui.button("Add Step", on_click=add_new_step).classes("mt-2")

                        # Копирование шага
                        with ui.card().classes("w-full mt-4"):
                            ui.label("Copy Selected Step").classes("text-h6")
                            copy_step_container = ui.column().classes("w-full mt-4")

                            async def update_copy_step_interface():
                                copy_step_container.clear()
                                # if not selected_step.value:
                                #     return
                                # step = next(s for s in all_steps if s["stepname"] == selected_step.value)
                                selected_row = (await grid.get_selected_row()) or {}
                                if not selected_row:
                                    return
                                step = next(s for s in visible_steps if s["stepname"] == selected_row["stepname"])
                                with copy_step_container:
                                    new_copy_stepname = ui.input("New Stepname", value=f"{step['stepname']}_copy").classes("w-full")
                                    async def copy_step_action():
                                        if new_copy_stepname.value in all_step_list:
                                            ui.notify("Step already exists", type="negative")
                                            return
                                        val_success, val_msg, _, _ = validate_step_fields(
                                            new_copy_stepname.value, step["sourcename"], step["sourcetype"], step["roles"], step["json"], all_sources, current_state
                                        )
                                        if not val_success:
                                            ui.notify(val_msg, type="negative")
                                            return
                                        create_success, create_msg, _, _ = create_step(
                                            new_copy_stepname.value, step["sourcename"], step["sourcetype"], step["roles"], step["json"], current_state
                                        )
                                        if not create_success:
                                            ui.notify(create_msg, type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(create_msg, currentFuncName(), current_state))
                                        else:
                                            ui.notify(f"Step {new_copy_stepname.value} copied", type="positive")
                                            logger_log(syslog.LOG_INFO, get_log_message(f"Step {new_copy_stepname.value} copied", currentFuncName(), current_state))
                                            draw_steps(interface_container, current_state)  # Обновление страницы
                                    ui.button("Copy Step", on_click=copy_step_action).classes("mt-2")

                            #selected_step.on("update:model-value", update_copy_step_interface)
                            grid.on("selectionChanged", update_copy_step_interface)

        return True, "OK", currentFuncName(), None

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None
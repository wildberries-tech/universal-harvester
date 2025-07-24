import json
import bcrypt
import syslog
import sqlite3
from typing import Tuple, List, Dict, Optional
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from nicegui import ui, app
from app.validation import validate_new_username, validate_new_password, validate_new_roles
from app.database.users import fetch_user_data, fetch_all_users, update_user_field, create_user


# Валидация данных
# def validate_password(password: str) -> Tuple[bool, str, str, None]:
#     func_name = "validate_password"
#     if len(password) < 8:
#         return False, "Password must be at least 8 characters long", func_name, None
#     return True, "OK", func_name, None

# def validate_username(username: str) -> Tuple[bool, str, str, None]:
#     func_name = "validate_username"
#     if not username or len(username) < 3:
#         return False, "Username must be at least 3 characters long", func_name, None
#     return True, "OK", func_name, None

# Основная функция отрисовки
def draw_users(interface_container: ui.card, current_state: dict) -> Tuple[bool, str, str, None]:
    func_name = "draw_users"
    try:
        # Логирование начала работы
        logger_log(syslog.LOG_INFO, get_log_message("Starting draw_users", func_name, current_state))

        # Очистка контейнера перед отрисовкой
        interface_container.clear()

        # Получение данных пользователя
        current_user = current_state.get("username", "unknown")

        user_success, user_msg, _, user_data = fetch_user_data(current_user, current_state)
        if not user_success:
            logger_log(syslog.LOG_ERR, get_log_message(user_msg, func_name, current_state))
            return False, user_msg, func_name, None

        has_admin_role = "users_admin" in user_data["roles"] or "fullmaster" in user_data["roles"]

        with interface_container:
            # Основной контейнер с ограниченной шириной для гармоничного вида
            with ui.column().classes("w-full"):
                ui.label(f"User: {current_user}").classes("text-h5 mb-4")

                # Базовый функционал: просмотр своих данных
                with ui.card().classes("w-full"):
                    ui.label("Your Data").classes("text-h6")
                    with ui.grid(columns=2).classes("w-full"):
                        ui.label("Active:")
                        ui.label(str(user_data["is_active"]))
                        ui.label("Username:")
                        ui.label(user_data["username"])
                        ui.label("Roles:")
                        ui.label(", ".join(user_data["roles"]))
                        ui.label("Additional Data (JSON):")
                        show_user_codemirror = ui.codemirror(value=json.dumps(user_data["json"], indent=2, ensure_ascii=False), language='JSON', line_wrapping = True, theme = current_state["codemirror_theme"]).classes("w-full h-96")
                        show_user_codemirror.disable()


                # Изменение пароля
                with ui.card().classes("w-full mt-4"):
                    ui.label("Change Password").classes("text-h6")
                    with ui.grid(columns=2).classes("w-full"):
                        new_password = ui.input("New Password", password=True)
                        confirm_password = ui.input("Confirm Password", password=True)
                    async def change_password():
                        if new_password.value != confirm_password.value:
                            ui.notify("Passwords do not match!", type="negative")
                            return
                        val_success, val_msg, _, _ = validate_new_password(new_password.value, current_state)
                        if not val_success:
                            ui.notify(val_msg, type="negative")
                            return
                        upd_success, upd_msg, _, _ = update_user_field(current_user, "hashed_pass", bcrypt.hashpw(new_password.value.encode('utf-8'), bcrypt.gensalt()).decode(), current_state)
                        if not upd_success:
                            ui.notify(upd_msg, type="negative")
                            logger_log(syslog.LOG_ERR, get_log_message(upd_msg, func_name, current_state))
                        else:
                            ui.notify("Password updated successfully!", type="positive")
                            logger_log(syslog.LOG_INFO, get_log_message("Password updated", func_name, current_state))
                            draw_users(interface_container, current_state)  # Обновление страницы
                    ui.button("Update Password", on_click=change_password).classes("mt-2")

                # Изменение JSON
                # with ui.card().classes("w-full mt-4"):
                #     ui.label("Update Additional Data (JSON)").classes("text-h6")
                #     json_input = ui.codemirror(value=json.dumps(user_data["json"], indent=2, ensure_ascii=False), language='JSON', line_wrapping = True, theme = current_state["codemirror_theme"]).classes("w-full h-96")
                #     async def update_json():
                #         try:
                #             json_data = json.loads(json_input.value)
                #             upd_success, upd_msg, _, _ = update_user_field(current_user, "json", json_data, current_state)
                #             if not upd_success:
                #                 ui.notify(upd_msg, type="negative")
                #                 logger_log(syslog.LOG_ERR, get_log_message(upd_msg, func_name, current_state))
                #             else:
                #                 ui.notify("JSON updated successfully!", type="positive")
                #                 logger_log(syslog.LOG_INFO, get_log_message("JSON updated", func_name, current_state))
                #                 draw_users(interface_container, current_state)  # Обновление страницы
                #         except json.JSONDecodeError:
                #             ui.notify("Invalid JSON format", type="negative")
                #     ui.button("Update JSON", on_click=update_json).classes("mt-2")

                # Админский функционал
                if has_admin_role:
                    ui.label("Admin Controls").classes("text-h5 mt-6 mb-4")

                    # Список всех пользователей через select
                    users_success, users_msg, _, all_users = fetch_all_users(current_state)
                    if not users_success:
                        logger_log(syslog.LOG_ERR, get_log_message(users_msg, func_name, current_state))
                        return False, users_msg, func_name, None
                    user_list = [user["username"] for user in all_users]
                    user_options = {user["username"]: user["username"] for user in all_users}
                    with ui.card().classes("w-full"):
                        ui.label("Manage Users").classes("text-h6")
                        selected_user = ui.select(user_options, label="Select User", value=None).classes("w-full")
                        admin_container = ui.column().classes("w-full mt-4")

                        def update_admin_interface():
                            admin_container.clear()
                            if not selected_user.value:
                                return
                            user = next(u for u in all_users if u["username"] == selected_user.value)
                            with admin_container:
                                with ui.grid(columns=2).classes("w-full"):
                                    ui.label("Active:")
                                    ui.label(str(user["is_active"]))
                                    ui.label("Username:")
                                    ui.label(user["username"])
                                    ui.label("Roles:")
                                    ui.label(", ".join(user["roles"]))
                                    ui.label("Additional Data (JSON):")
                                    show_user_codemirror_admin = ui.codemirror(value=json.dumps(user["json"], indent=2, ensure_ascii=False), language='JSON', line_wrapping = True, theme = current_state["codemirror_theme"]).classes("w-full h-96")
                                    show_user_codemirror_admin.disable()

                                # Изменение пароля
                                new_admin_password = ui.input("New Password", password=True).classes("mt-2")
                                async def change_user_password():
                                    val_success, val_msg, _, _ = validate_new_password(new_admin_password.value, current_state)
                                    if not val_success:
                                        logger_log(syslog.LOG_ERR, get_log_message(val_msg, func_name, current_state))
                                        ui.notify(val_msg, type="negative")
                                        return
                                    
                                    # на всякий случай провалидируем как нового
                                    validate_new_username_result = validate_new_username(user["username"], current_state)
                                    if validate_new_username_result[0] == False:
                                        logger_log(syslog.LOG_ERR, get_log_message(validate_new_username_result[1], func_name, current_state))
                                        ui.notify(validate_new_username_result[1], type="negative")
                                        return

                                    upd_success, upd_msg, _, _ = update_user_field(user["username"], "hashed_pass",bcrypt.hashpw(new_admin_password.value.encode('utf-8'), bcrypt.gensalt()).decode(), current_state)
                                    if not upd_success:
                                        ui.notify(upd_msg, type="negative")
                                        logger_log(syslog.LOG_ERR, get_log_message(upd_msg, func_name, current_state))
                                    else:
                                        ui.notify(f"Password updated for {user['username']}", type="positive")
                                        logger_log(syslog.LOG_INFO, get_log_message(f"Password updated for {user['username']}", func_name, current_state))
                                        draw_users(interface_container, current_state)  # Обновление страницы
                                ui.button("Change Password", on_click=change_user_password).classes("mt-2")

                                # Изменение ролей
                                roles_input = ui.codemirror(value=json.dumps(user["roles"], indent=2, ensure_ascii=False), language='JSON', line_wrapping = True, theme = current_state["codemirror_theme"]).classes("w-full h-32 mt-2")
                                async def update_roles():
                                    try:
                                        new_roles = json.loads(roles_input.value)
                                        if not isinstance(new_roles, list):
                                            ui.notify("Roles must be a JSON list", type="negative")
                                            return
                                        validate_new_roles_result = validate_new_roles(new_roles, current_state)
                                        if validate_new_roles_result[0] == False:
                                            ui.notify(validate_new_roles_result[1], type="negative")
                                            return
                                        
                                        # на всякий случай провалидируем как нового
                                        validate_new_username_result = validate_new_username(user["username"], current_state)
                                        if validate_new_username_result[0] == False:
                                            logger_log(syslog.LOG_ERR, get_log_message(validate_new_username_result[1], func_name, current_state))
                                            ui.notify(validate_new_username_result[1], type="negative")
                                            return
                                        
                                        upd_success, upd_msg, _, _ = update_user_field(user["username"], "roles", new_roles, current_state)
                                        if not upd_success:
                                            ui.notify(upd_msg, type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(upd_msg, func_name, current_state))
                                        else:
                                            ui.notify(f"Roles updated for {user['username']}", type="positive")
                                            logger_log(syslog.LOG_INFO, get_log_message(f"Roles updated for {user['username']}", func_name, current_state))
                                            draw_users(interface_container, current_state)  # Обновление страницы
                                    except json.JSONDecodeError:
                                        ui.notify("Invalid JSON format", type="negative")
                                ui.button("Update Roles", on_click=update_roles).classes("mt-2")

                                # Изменение JSON
                                user_json_input = ui.codemirror(value=json.dumps(user["json"], indent=2, ensure_ascii=False), language='JSON', line_wrapping = True, theme = current_state["codemirror_theme"]).classes("w-full h-48 mt-2")
                                async def update_user_json():
                                    try:
                                        json_data = json.loads(user_json_input.value)

                                        # на всякий случай провалидируем как нового
                                        validate_new_username_result = validate_new_username(user["username"], current_state)
                                        if validate_new_username_result[0] == False:
                                            logger_log(syslog.LOG_ERR, get_log_message(validate_new_username_result[1], func_name, current_state))
                                            ui.notify(validate_new_username_result[1], type="negative")
                                            return
                                        
                                        upd_success, upd_msg, _, _ = update_user_field(user["username"], "json", json_data, current_state)
                                        if not upd_success:
                                            ui.notify(upd_msg, type="negative")
                                            logger_log(syslog.LOG_ERR, get_log_message(upd_msg, func_name, current_state))
                                        else:
                                            ui.notify(f"JSON updated for {user['username']}", type="positive")
                                            logger_log(syslog.LOG_INFO, get_log_message(f"JSON updated for {user['username']}", func_name, current_state))
                                            draw_users(interface_container, current_state)  # Обновление страницы
                                    except json.JSONDecodeError:
                                        ui.notify("Invalid JSON format", type="negative")
                                ui.button("Update JSON", on_click=update_user_json).classes("mt-2")

                                # Блокировка пользователя
                                async def toggle_block():
                                    new_status = not user["is_active"]
                                    upd_success, upd_msg, _, _ = update_user_field(user["username"], "is_active", new_status, current_state)
                                    if not upd_success:
                                        ui.notify(upd_msg, type="negative")
                                        logger_log(syslog.LOG_ERR, get_log_message(upd_msg, func_name, current_state))
                                    else:
                                        action = "blocked" if not new_status else "unblocked"
                                        ui.notify(f"User {user['username']} {action}", type="positive")
                                        logger_log(syslog.LOG_INFO, get_log_message(f"User {user['username']} {action}", func_name, current_state))
                                        draw_users(interface_container, current_state)  # Обновление страницы
                                ui.button("Block/Unblock", on_click=toggle_block).classes("mt-2")

                        selected_user.on("update:model-value", update_admin_interface)

                    # Создание нового пользователя
                    with ui.card().classes("w-full mt-4"):
                        ui.label("Create New User").classes("text-h6")
                        with ui.grid(columns=2).classes("w-full"):
                            ui.label("Input username:")
                            ui.label("Input password:")
                            new_username = ui.input("Username")
                            new_user_password = ui.input("Password", password=True)
                            ui.label("Roles list:")
                            ui.label("Additional data:")
                            new_user_roles = ui.codemirror(value='["user"]', language='JSON', line_wrapping = True, theme = current_state["codemirror_theme"]).classes("w-full h-32")
                            new_user_json = ui.codemirror(value="{}", language='JSON', line_wrapping = True, theme = current_state["codemirror_theme"]).classes("w-full h-96")
                        async def create_new_user():
                            if new_username.value in user_list:
                                ui.notify("username already exists", type="negative")
                                return
                            val_uname_success, val_uname_msg, _, _ = validate_new_username(new_username.value, current_state)
                            if not val_uname_success:
                                ui.notify(val_uname_msg, type="negative")
                                return
                            val_pass_success, val_pass_msg, _, _ = validate_new_password(new_user_password.value, current_state)
                            if not val_pass_success:
                                ui.notify(val_pass_msg, type="negative")
                                return
                            try:
                                roles_data = json.loads(new_user_roles.value)
                                if not isinstance(roles_data, list):
                                    ui.notify("Roles must be a JSON list", type="negative")
                                    return
                                validate_new_roles_result = validate_new_roles(roles_data, current_state)
                                if validate_new_roles_result[0] == False:
                                    ui.notify(validate_new_roles_result[1], type="negative")
                                    return
                                json_data = json.loads(new_user_json.value)
                            except json.JSONDecodeError:
                                ui.notify("Invalid JSON format", type="negative")
                                return
                            create_success, create_msg, _, _ = create_user(
                                new_username.value, new_user_password.value, roles_data, json_data, current_state
                            )
                            if not create_success:
                                ui.notify(create_msg, type="negative")
                                logger_log(syslog.LOG_ERR, get_log_message(create_msg, func_name, current_state))
                            else:
                                ui.notify(f"User {new_username.value} created", type="positive")
                                logger_log(syslog.LOG_INFO, get_log_message(f"User {new_username.value} created", func_name, current_state))
                                draw_users(interface_container, current_state)  # Обновление страницы
                        ui.button("Create User", on_click=create_new_user).classes("mt-2")

        return True, "OK", func_name, None

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, func_name, current_state))
        return False, error_message, func_name, None
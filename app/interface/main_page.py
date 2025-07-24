from app.login import try_login
import syslog
from fastapi import Request
from nicegui import ui, app
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.validation import check_current_user_status
from app.interface.main_page_blocks.users import draw_users
from app.interface.main_page_blocks.keys import draw_keys
from app.interface.main_page_blocks.sources import draw_sources
from app.interface.main_page_blocks.steps import draw_steps
from app.interface.main_page_blocks.tasks import draw_tasks
from app.interface.main_page_blocks.scenarios import draw_scenarios
from app.interface.main_page_blocks.scenario_editor import draw_scenario_editor

def main_page(keycloak_openid, current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("Main page opened", currentFuncName(), current_state))
    # Устанавливаем глобальные цвета
    ui.colors(
        primary="#F97316",  # Оранжевый для основных элементов
        secondary="#1F2937",  # Тёмно-серый для второстепенных элементов
        accent="#F97316"    # Оранжевый для акцентов
    )
    # Включаем тёмную тему
    dark_mode = ui.dark_mode()
    dark_mode.enable()

    def logout() -> None:
        app.storage.user.clear()
        try:
            if current_state["keycloak_flag"] == True:
                refresh_token = app.storage.user.get('refresh_token', "")
                if refresh_token != "":
                    #await current_state["keycloak_openid"].a_logout(refresh_token)
                    keycloak_openid.logout(refresh_token)
        except BaseException as e:
            print("keycloak logout error: ", str(e))
        ui.navigate.to('/login')

    user_status = check_current_user_status(current_state)
    if user_status[0] == False or user_status[2] == False:
        logout()
    # user_roles = user_status[1]
    # user_json = user_status[3][3][4]

    with ui.header(elevated=True).classes("h-10 p-1") as top_panel:
        menu_button = ui.button('☰')
        #clock_label = ui.label('SYSTEM TIME: INITIALIZING...').classes('panel-item')
        #ui.timer(0.001, lambda: clock_label.set_text(f"SYSTEM TIME: {currentTimestamp()}"))
    
    with ui.left_drawer(fixed=False) as menu:
    
        menu_items = [
            ("Users", "Управление пользователями", 'pets' , lambda: draw_users(interface_container, current_state)),
            ("Keys", "Хранилище секретов", 'key', lambda: draw_keys(interface_container, current_state)),
            ("Sources", "Источники данных", 'source', lambda: draw_sources(interface_container, current_state)),
            ("Steps", "Шаги выполнения", 'stairs', lambda: draw_steps(interface_container, current_state)),
            ("Tasks", "Список задач", 'task', lambda: draw_tasks(interface_container, current_state)),
            ("Scenarios", "Сценарии выполнения", 'rocket_launch', lambda: draw_scenarios(interface_container, current_state)),
            ("Scenarios editor", "Редактор сценариев", 'design_services', lambda: draw_scenario_editor(interface_container, current_state)), 
            ("AI integration", "Интеграция с ИИ помощниками", 'psychology', None),
            ("Scheduler", "Планировщик задач", 'schedule', None),
            ("Logout", "Выход", 'logout', logout)
        ]
            
        for item, tooltip, icon, function in menu_items:
            menu_item = ui.button(item, icon=icon).tooltip(tooltip)
            menu_item.on('click', function)

        menu_button.on('click', lambda: menu.toggle())

    interface_container = ui.card()
    with interface_container.classes('w-full h-full'):
        pass

    with ui.footer().classes("h-6 p-1"):
        user_status_label = ui.label(f"USER: {current_state["username"]}").classes('panel-item')
        ip_label = ui.label(f"IP: {current_state["client_ip_address"]}").classes('panel-item')
        port_label = ui.label(f"PORT: {current_state["client_port"]}").classes('panel-item')
        app_session_label = ui.label(f"APP SESSION: {current_state["main_session_id"]}").classes('panel-item')
        user_session_label = ui.label(f"USER SESSION: {current_state["user_session_id"]}").classes('panel-item')
        
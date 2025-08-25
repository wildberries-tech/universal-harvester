from app.login import try_login
import syslog
import asyncio
import time
from fastapi import Request
from nicegui import ui, app, Client
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName

async def sleep():
    await asyncio.sleep(1)

async def login_page(current_state):
    logger_log(syslog.LOG_DEBUG, get_log_message("Login page opened", currentFuncName(), current_state))
    dark = ui.dark_mode()
    dark.enable()

    with ui.element('div').classes('main-container') as main_container:
        #main_container.classes('absolute-center')
        with ui.element('div').classes('top-panel') as top_panel:
            command_label = ui.label('> AUTHENTICATION REQUIRED: ENTER LOGIN').classes('glitch-text')

        
        
        with ui.column().classes('login-form') as column:
            column.classes('fixed-center')

            ui.label('UNIVERSAL HARVESTER AUTHENTICATION TERMINAL').classes('title glitch-text').style('color: #ff4500; font-size: 24px; text-align: center;')
            username_input = ui.input(label='USERNAME', placeholder='Enter username')
            username_input.tooltip("Место для ввода логина, сюда введите ваш логин")
            password_input = ui.input(label='PASSWORD', password=True, placeholder='Enter password')
            
            async def handle_login():
                
                login_result = try_login(username_input.value, password_input.value, current_state)
                await sleep()
                if login_result[0] == True:
                    login_data = login_result[3]
                    app.storage.user.update({'username': login_data['username'], 'authenticated': login_data['authenticated'], 'session_id': login_data['session_id']})

                    user_status_label.set_text(f"USER: {login_data['username']}")
                    user_session_label.set_text(f"USER SESSION: {login_data['session_id']}")
                    ui.navigate.to('/')
                else:
                    ui.notify(f"Login failed", type='negative')
            password_input.on('keydown.enter', handle_login)
            ui.button('LOGIN', on_click=handle_login).tooltip("Нажмите для входа в систему")
            if current_state["keycloak_flag"]:
                try:
                    #auth_url = await current_state["keycloak_openid"].a_auth_url(redirect_uri=f"{current_state["itself_link"]}login/callback")
                    auth_url = current_state["keycloak_openid"].auth_url(redirect_uri=f"{current_state['itself_link']}login/callback")
                    ui.button('LOGIN VIA KEYCLOAK', on_click=lambda: ui.navigate.to(auth_url)).tooltip("Keycloak auth")
                except BaseException as e:
                    ui.label("keycloak error")
    

    with ui.element('div').classes('bottom-panel'):
        with ui.element('div').classes('left-items'):
            user_status_label = ui.label('USER: NOT AUTHORIZED').classes('panel-item')
            ip_label = ui.label(f"IP: {current_state['client_ip_address']}").classes('panel-item')
            port_label = ui.label(f"PORT: {current_state['client_port']}").classes('panel-item')
            app_session_label = ui.label(f"APP SESSION: {current_state['main_session_id']}").classes('panel-item')
            user_session_label = ui.label('USER SESSION: NONE').classes('panel-item')
        #clock_label = ui.label('SYSTEM TIME: INITIALIZING...').classes('panel-item')
        #ui.timer(0.001, lambda: clock_label.set_text(f"SYSTEM TIME: {currentTimestamp()}"))
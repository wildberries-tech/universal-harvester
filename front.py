import termios
import argparse
import asyncio
#import nest_asyncio
#nest_asyncio.apply()

from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import app, ui, Client, run

import re

import uuid
import sys

from app.logging import currentTimestamp, get_log_message, logger_log#, currentFuncName
from app.interface.login_page import login_page
from app.interface.main_page import main_page

from app.database.init import db_init

from app.interface.additional import create_fullscreen_scenario_result_page
from app.interface.api.scenario_launch import api_scenario_launch_page

from app.crptgrphy import decrypt

from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
import syslog
import pwinput

#from fastapi_keycloak import FastAPIKeycloak, OIDCUser
from keycloak.keycloak_openid import KeycloakOpenID
#from keycloak import KeycloakOpenID
from app.database.keys import db_get_key

def main():
    APP_NAME = "Universal Harvester"
    APP_VERSION = "1.0.0"

    DUMMY_SESSION_ID = "00000000-0000-0000-0000-000000000000"
    DUMMY_IP = "127.0.0.1"
    DUMMY_PORT = 0
    DUMMY_USERNAME = "dummy"
    

    main_session_id = str(uuid.uuid4())
    ########################################
    # Ввод всех необходимых данных
    ########################################

    MASTER_KEY = pwinput.pwinput(prompt='The master key: ', mask='*')

    global args
    parser = argparse.ArgumentParser(description="Front UH")
    parser.add_argument(
        "--db_conf_object",
        type=str,
        #default = '',
        help="Объект конфигурации БД (генерируется и шифруется вспомогательным модулем)"
    )
    parser.add_argument(
        "--nicegui_storage_key_object",
        type=str,
        #default='',
        help="Ключ хранилища nicegui (sessions-key) (генерируется и шифруется вспомогательным модулем)"
    )
    parser.add_argument(
        "--engine_module_path",
        type=str,
        default="engine.py",
        help="Путь к исполняемому модулю engine (главный модуль исполнения)"
    )
    parser.add_argument(
        "--scheduler_module_path",
        type=str,
        default="scheduler.py",
        help="Путь к исполняемому модулю scheduler (планировщик заданий)"
    )
    parser.add_argument(
        "--health_module_path",
        type=str,
        default="health.py",
        help="Путь к исполняемому модулю health (контроль состояния)"
    )
    parser.add_argument(
        "--storage_path",
        type=str,
        default="../storage",
        help="Путь к хранилищу данных"
    )
    parser.add_argument(
        "--itself_link",
        type=str,
        default="http://127.0.0.1:8082/",
        help="Ссылка на себя (нужна для формирования ссылок при уведомлениях)"
    )
    parser.add_argument(
        "--ssl_certfile",
        type=str,
        default="crt.pem",
        help="SSL cert file path"
    )
    parser.add_argument(
        "--ssl_keyfile",
        type=str,
        default="key.pem",
        help="SSL key file path"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8082,
        help="Порт сервиса"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Хост поднимаемого сервиса (откуда ждём подключений)"
    )
    parser.add_argument(
        "--keycloak_url",
        type=str,
        default="",
        help="(Опционально) keycloak URL"
    )
    parser.add_argument(
        "--keycloak_client_id",
        type=str,
        default="harvester",
        help="(Опционально) keycloak client id"
    )
    parser.add_argument(
        "--keycloak_realm_id",
        type=str,
        default="harvester",
        help="(Опционально) keycloak realm"
    )
    parser.add_argument(
        "--keycloak_key",
        type=str,
        default="keycloak:harvester",
        help="(Опционально) Ключ keycloak в таблице keys"
    )

    args = parser.parse_args()

    DB_CONF = args.db_conf_object
    NICEGUI_STORAGE_KEY = args.nicegui_storage_key_object
    ENGINE_PATH = args.engine_module_path
    SCHEDULER_PATH = args.scheduler_module_path
    HEALTH_PATH = args.health_module_path
    STORAGE_PATH = args.storage_path
    ITSELF_LINK = args.itself_link

    KEYCLOAK_URL = args.keycloak_url
    KEYCLOAK_CLIENT_ID = args.keycloak_client_id
    KEYCLOAK_REALM_ID = args.keycloak_realm_id
    KEYCLOAK_DB_KEY = args.keycloak_key

    ########################################
    # Подготовка первичного current_state
    ########################################

    current_state = {
        "db_conf":DB_CONF,
        "app_name":APP_NAME,
        "app_version":APP_VERSION,
        "main_session_id":main_session_id,
        "user_session_id":DUMMY_SESSION_ID,
        "client_ip_address":DUMMY_IP,
        "client_port":DUMMY_PORT,
        "username":"system",
        "master_key": MASTER_KEY,
        "codemirror_theme":'monokai',
        "aggrid_theme":'ag-theme-balham-dark',
        "itself_link":ITSELF_LINK
        
    }
    ########################################
    # Валидация и раскрытие введённых параметров
    ########################################
    decrypt_result = decrypt(NICEGUI_STORAGE_KEY, current_state)
    if decrypt_result[0] == False:
        error_message = f"NICEGUI_STORAGE_KEY decrypt failed: {decrypt_result[1]}"
        logger_log(syslog.LOG_CRIT, get_log_message(error_message, currentFuncName(), current_state))
        print(error_message)
        return
    NICEGUI_STORAGE_KEY = decrypt_result[3]
    ########################################
    # инициализация БД
    ########################################
    db_status = db_init(current_state)
    if db_status[0] == False:
        error_message = f"db init error: {db_status[1]}"
        logger_log(syslog.LOG_CRIT, get_log_message(error_message, currentFuncName(), current_state))
        print(error_message)
        return
    ########################################
    # Создание объекта интеграции с keycloak
    ########################################
    try:
        db_get_key_result = db_get_key({"system":KEYCLOAK_DB_KEY.split(":")[0],"account":KEYCLOAK_DB_KEY.split(":")[1]}, current_state)
        if db_get_key_result[0] == True:
            keycloak_decrypt_result = decrypt(db_get_key_result[3][2], current_state)
            if keycloak_decrypt_result[0] == True:
                keycloak_flag = True
                keycloak_openid = KeycloakOpenID(
                    server_url=KEYCLOAK_URL,
                    client_id=KEYCLOAK_CLIENT_ID,
                    client_secret_key=keycloak_decrypt_result[3],
                    realm_name=KEYCLOAK_REALM_ID
                )
            else:
                keycloak_flag = False
                keycloak_openid = False
                error_message = f"keycloak init error: decrypt keycloak key error ({keycloak_decrypt_result[1]})"
                logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
        else:
            keycloak_flag = False
            keycloak_openid = False
            error_message = f"keycloak init error: get keycloak key from db error ({db_get_key_result[1]})"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
    except BaseException as e:
        keycloak_flag = False
        keycloak_openid = False
        error_message = f"keycloak init error: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))

    ########################################
    # Красивости nicegui
    ########################################

    ui.colors(
        primary="#F97316",  # Оранжевый для основных элементов
        secondary="#1F2937",  # Тёмно-серый для второстепенных элементов
        accent="#F97316"    # Оранжевый для акцентов
    )
    # Включаем тёмную тему
    dark_mode = ui.dark_mode()
    dark_mode.enable()

    ########################################
    # аутентификация
    ########################################
    unrestricted_page_routes_regex = ['/login', '/api/scenario/[^/]+/parameters/[^/]+/[^/]+']
    class AuthMiddleware(BaseHTTPMiddleware):
        """This middleware restricts access to all NiceGUI pages.

        It redirects the user to the login page if they are not authenticated.
        """
        async def dispatch(self, request: Request, call_next):
            if not app.storage.user.get('authenticated', False):
                if not request.url.path.startswith('/_nicegui'):
                    unrestricted_flag = False
                    for regex in unrestricted_page_routes_regex:
                        if re.search(regex, request.url.path):
                            unrestricted_flag = True
                    if unrestricted_flag == False:
                        app.storage.user['referrer_path'] = request.url.path  # remember where the user wanted to go
                        return RedirectResponse('/login')
            return await call_next(request)


    app.add_middleware(AuthMiddleware)

    ########################################
    # страница входа
    ########################################
    @ui.page('/login')
    async def _login_page(client: Client, request: Request):
        client_ip = request.client.host#client.environ['asgi.scope']['client'][0]
        client_port = request.client.port#client.environ['asgi.scope']['client'][1]
        current_state = {
            "db_conf":DB_CONF,
            "app_name":APP_NAME,
            "app_version":APP_VERSION,
            "main_session_id":main_session_id,
            "user_session_id":DUMMY_SESSION_ID,
            "client_ip_address":client_ip,
            "client_port":client_port,
            "username":DUMMY_USERNAME,
            "engine_path": ENGINE_PATH,
            "master_key": MASTER_KEY,
            "itself_link":ITSELF_LINK,
            "keycloak_flag":keycloak_flag,
            "keycloak_openid":keycloak_openid
        }
        ui.page_title(f'{current_state["app_name"]}')
        await login_page(current_state)
    ########################################
    # callback keycloak
    ########################################
    @ui.page('/login/callback')
    async def _login_callback(client: Client, request: Request, session_state: str, code: str):
        client_ip = request.client.host#client.environ['asgi.scope']['client'][0]
        client_port = request.client.port#client.environ['asgi.scope']['client'][1]
        current_state = {
            "db_conf":DB_CONF,
            "app_name":APP_NAME,
            "app_version":APP_VERSION,
            "main_session_id":main_session_id,
            "user_session_id":DUMMY_SESSION_ID,
            "client_ip_address":client_ip,
            "client_port":client_port,
            "engine_path": ENGINE_PATH,
            "username":DUMMY_USERNAME,
            "master_key": MASTER_KEY,
            "itself_link":ITSELF_LINK,
            "keycloak_flag":keycloak_flag,
            "keycloak_openid":keycloak_openid
        }
        ui.page_title(f'{current_state["app_name"]}')
        

        try:
            if current_state["keycloak_flag"] == True:
                #access_token = await keycloak_openid.a_token(
                access_token = keycloak_openid.token(
                    grant_type='authorization_code',#'authorization_code',
                    code=code,
                    redirect_uri=f"{current_state['itself_link']}login/callback"
                )

                new_session_id = str(uuid.uuid4())
                #current_user_info = await keycloak_openid.a_userinfo(access_token['access_token'])
                current_user_info = keycloak_openid.userinfo(access_token['access_token'])
                app.storage.user.update({
                    'username': current_user_info["preferred_username"], 
                    'authenticated': True, 
                    'session_id': new_session_id,
                    "access_token":access_token['access_token'],
                    "refresh_token":access_token['refresh_token'],
                    # "expires_in":access_token['expires_in'],
                    # "refresh_expires_in":access_token['refresh_expires_in']
                })
                ui.navigate.to('/')
        except BaseException as e:
            error_message = f"Keycloak access_token error: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))


    ########################################
    # основная страница приложения
    ########################################
    @ui.page('/')
    def _main_page(client: Client, request: Request):
        client_ip = request.client.host#client.environ['asgi.scope']['client'][0]
        client_port = request.client.port#client.environ['asgi.scope']['client'][1]
        CURRENT_SESSION_ID = app.storage.user['session_id']
        CURRENT_USERNAME = app.storage.user["username"]
        current_state = {
            "db_conf":DB_CONF,
            "app_name":APP_NAME,
            "app_version":APP_VERSION,
            "main_session_id":main_session_id,
            "user_session_id":CURRENT_SESSION_ID,
            "client_ip_address":client_ip,
            "client_port":client_port,
            "username":CURRENT_USERNAME,
            "master_key": MASTER_KEY,
            "codemirror_theme":'monokai',
            "aggrid_theme":'ag-theme-balham-dark',
            "engine_path": ENGINE_PATH,
            "storage_path":STORAGE_PATH,
            "itself_link":ITSELF_LINK,
            "keycloak_flag":keycloak_flag,
            #"keycloak_openid":keycloak_openid
        }
        ui.page_title(f'{current_state["app_name"]}')
        main_page(keycloak_openid, current_state)
    ########################################
    # страница просмотра результата
    ########################################
    @ui.page('/result/{session_id}/{output_type}')
    async def page(session_id: str, output_type: str, client: Client, request: Request):
        client_ip = request.client.host#client.environ['asgi.scope']['client'][0]
        client_port = request.client.port#client.environ['asgi.scope']['client'][1]
        CURRENT_SESSION_ID = app.storage.user['session_id']
        CURRENT_USERNAME = app.storage.user["username"]
        current_state = {
            "db_conf":DB_CONF,
            "app_name":APP_NAME,
            "app_version":APP_VERSION,
            "main_session_id":main_session_id,
            "user_session_id":CURRENT_SESSION_ID,
            "client_ip_address":client_ip,
            "client_port":client_port,
            "username":CURRENT_USERNAME, 
            "master_key": MASTER_KEY,
            "codemirror_theme":'monokai',
            "aggrid_theme":'ag-theme-balham-dark',
            "engine_path": ENGINE_PATH,
            "storage_path":STORAGE_PATH,
            "itself_link":ITSELF_LINK,
            #"keycloak_flag":keycloak_flag,
            #"keycloak_openid":keycloak_openid
        }
        ui.page_title(f'{current_state["app_name"]}')
        await create_fullscreen_scenario_result_page(session_id, output_type, current_state)
    ########################################
    # страница api запуска сценария curl
    ########################################
    @app.get("/api/scenario/{scenario_name}/parameters/{parameters}/{output_type}", response_class=StreamingResponse, response_model=None)
    async def download_report(scenario_name: str, parameters: str, output_type: str, request: Request):
        client_ip = request.client.host#client.environ['asgi.scope']['client'][0]
        client_port = request.client.port#client.environ['asgi.scope']['client'][1]
        CURRENT_SESSION_ID = str(uuid.uuid4())
        CURRENT_USERNAME = "api_user"
        current_state = {
            "db_conf":DB_CONF,
            "app_name":APP_NAME,
            "app_version":APP_VERSION,
            "main_session_id":main_session_id,
            "user_session_id":CURRENT_SESSION_ID,
            "client_ip_address":client_ip,
            "client_port":client_port,
            "username":CURRENT_USERNAME, 
            "master_key": MASTER_KEY,
            "codemirror_theme":'monokai',
            "aggrid_theme":'ag-theme-balham-dark',
            "engine_path": ENGINE_PATH,
            "storage_path":STORAGE_PATH,
            "itself_link":ITSELF_LINK,
            # "keycloak_flag":keycloak_flag,
            # "keycloak_openid":keycloak_openid
        }
        api_scenario_launch_page_result = await run.cpu_bound(api_scenario_launch_page, dict(request.headers), scenario_name, parameters, output_type, current_state)
        if api_scenario_launch_page_result[0] == False:
            raise HTTPException(status_code=api_scenario_launch_page_result[3]["response_code"], detail=api_scenario_launch_page_result[1])
        
        return StreamingResponse(
            api_scenario_launch_page_result[3]["buffer"],
            media_type=api_scenario_launch_page_result[3]["media_type"],
            headers={"Content-Disposition": f"attachment; filename={api_scenario_launch_page_result[3]['filename']}"})
    
    ########################################
    # запуск
    ########################################
    ui.run(host=args.host, storage_secret=NICEGUI_STORAGE_KEY,port=args.port, favicon="favicon.ico", reload=False, show=False, ssl_certfile=args.ssl_certfile, ssl_keyfile=args.ssl_keyfile)

main()
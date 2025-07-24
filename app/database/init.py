import sqlite3
import syslog
import sys
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.database.db_connection import create_db_connection
db_init_steps = [
    {
        "table":"users",
        "query":"""CREATE TABLE IF NOT EXISTS users
                (
                    is_active BOOLEAN,
                    username TEXT,
                    hashed_pass TEXT,
                    roles TEXT,
                    json TEXT
                );"""
    },
    {
        "table":"keys",
        "query":"""CREATE TABLE IF NOT EXISTS keys
                (
                    system TEXT,
                    account TEXT,
                    key TEXT,
                    comment TEXT
                );"""
    },
    {
        "table":"api_keys",
        "query":"""CREATE TABLE IF NOT EXISTS api_keys
                (
                    id INTEGER,
                    hashed_key TEXT,
                    is_active BOOLEAN,
                    username TEXT,
                    expired_timestamp INTEGER,
                    comment TEXT
                );"""
    },
    {
        "table":"access_networks",
        "query":"""CREATE TABLE IF NOT EXISTS access_networks
                (
                    ip_network TEXT,
                    allow BOOLEAN,
                    comment TEXT
                );"""
    },
    {
        "table":"default_access_networks",
        "query":"""INSERT INTO access_networks(ip_network, allow, comment)  
                    SELECT '127.0.0.0/8', true, 'localhost'
                    WHERE NOT EXISTS(SELECT * FROM access_networks);"""
    },
    {
        "table":"sources",
        "query":"""CREATE TABLE IF NOT EXISTS sources
                (
                    sourcename TEXT,
                    type TEXT,
                    json TEXT
                );"""
    },
    {
        "table":"default_sources",
        "query":"""INSERT INTO sources (sourcename, type, json) 
        SELECT 'sqlite3_in_memory', 'sqlite3_in_memory', '{"type":"sqlite3_in_memory","max_threads":999,"request_timeout":300}'
        WHERE NOT EXISTS(SELECT 1 FROM sources WHERE sourcename = 'sqlite3_in_memory' AND type = 'sqlite3_in_memory');"""
    },
    {
        "table":"default_sources",
        "query":"""INSERT INTO sources (sourcename, type, json) 
        SELECT 'pandas_in_memory', 'pandas', '{"type":"pandas","max_threads":999}'
        WHERE NOT EXISTS(SELECT 1 FROM sources WHERE sourcename = 'pandas_in_memory' AND type = 'pandas');"""
    },
    {
        "table":"steps",
        "query":"""CREATE TABLE IF NOT EXISTS steps
                (
                    stepname TEXT,
                    sourcename TEXT,
                    sourcetype TEXT,
                    roles TEXT,
                    json TEXT
                );"""
    },
    {
        "table":"scenarios",
        "query":"""CREATE TABLE IF NOT EXISTS scenarios
                (
                    scenario_name TEXT,
                    author TEXT, 
                    roles TEXT,
                    json TEXT
                );"""
    },
    {
        "table":"scenarios_history",
        "query":"""CREATE TABLE IF NOT EXISTS scenarios_history
                (
                    scenario_name TEXT, /*имя сценария, из таблицы scenarios*/
                    username TEXT, /*пользователь, что запустил сценарий*/
                    status_code INTEGER,  /*статус таски (не взята в работу, взята в работу, выполнена, не выполнена*/
                    status TEXT, /*описание статуса, в основном нужно для понимания ошибок выполнения*/
                    timestamp_start TEXT, /*время запуска выполнения сценария*/
                    timestamp_stop TEXT, /*время окончания выполнения сценария*/
                    session_id TEXT, /*уникальный идетификатор выполнения*/
                    json TEXT /*нагрузка*/
                );"""
    },
    {
        "table":"tasks",
        "query":"""CREATE TABLE IF NOT EXISTS tasks
                (
                    id TEXT, /*идентификатор таски*/
                    pid INTEGER, /*process_id исполнителя*/
                    status_code INTEGER,  /*статус таски (не взята в работу, взята в работу, выполнена, не выполнена*/
                    status TEXT, /*описание статуса, в основном нужно для понимания ошибок выполнения*/
                    result_rows_count INTEGER, 
                    step_name TEXT, /*какой шаг выполняем, он же идентификатор шага в сценарии*/
                    source_name TEXT,
                    username TEXT,
                    timestamp_start TEXT,
                    timestamp_stop TEXT,
                    in_scenario TEXT,
                    json TEXT /*остальные параметры таски*/
                );"""
    },
    {
        "table":"tasks_clear",
        "query":"""UPDATE tasks SET status_code=-99 WHERE status_code > 1;"""
    },
    {
        "table":"scheduler",
        "query":"""CREATE TABLE IF NOT EXISTS scheduler
                (
                    job_name TEXT, /*название задания*/
                    author TEXT, /*автор задания*/
                    every_minutes INTEGER, /*раз в сколько минут запускается задание*/
                    json TEXT /*остальные параметры задания*/
                );"""
    },
    {
        "table":"default_user",
        "query":"""INSERT INTO users(is_active, username, hashed_pass, roles, json)  
                    SELECT true, 'default_admin', '$2a$12$Mz5DDZmXZt3YFv2GbIM3uOEbH2lK5jGmZh8zJSgg.iZchSq6lyAcq', '[\"fullmaster\"]', '{}'
                    WHERE NOT EXISTS(SELECT * FROM users) AND NOT EXISTS(SELECT * FROM steps) AND NOT EXISTS(SELECT * FROM scenarios) AND NOT EXISTS(SELECT * FROM tasks);"""
    }
]

def db_init(current_state):
    try:
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))

        create_db_connection_result = create_db_connection(current_state)
        if create_db_connection_result[0] == False:
            error_message = f"create_db_connection_result is false: {create_db_connection_result[1]}"
            logger_log(syslog.LOG_ERR, get_log_message(error_message, currentFuncName(), current_state))
            return False, error_message, currentFuncName(), None

        connection = create_db_connection_result[3]

        cursor = connection.cursor()
        for i, db_init_step in enumerate(db_init_steps):
            logger_log(
                syslog.LOG_DEBUG, 
                get_log_message(
                    f"table {db_init_step['table']} initialization", 
                    currentFuncName(), 
                    current_state))
            cursor.execute(db_init_step['query'])
        connection.commit()
        cursor.close()
        connection.close()
    except BaseException as e:
        logger_log(syslog.LOG_CRIT, get_log_message(f"fail: {str(e)}", currentFuncName(), current_state))
        return False, str(e), currentFuncName(), None
    
    logger_log(syslog.LOG_DEBUG,get_log_message("done", currentFuncName(), current_state))
    return True, "OK", currentFuncName(), None
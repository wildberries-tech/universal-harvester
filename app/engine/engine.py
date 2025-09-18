import os
from copy import deepcopy
from datetime import datetime, timedelta
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName
from app.engine.shared_memory import create_shared_memory_block
from app.database.tasks import db_upsert_task
from app.validation import *
from app.crptgrphy import decrypt
from app.database.keys import db_get_key
import sys
import re
# импорт источников
from app.engine.sources.netbox import execute_netbox_finder, execute_netbox_search_cidr_by_ipaddress
from app.engine.sources.elastic import execute_elasctic_query_via_client, execute_elasctic_aggs_via_client, execute_function_linux_pid_hierarchy_elastic, execute_function_linux_pid_siblings_elastic
from app.engine.sources.elastic_requests import execute_elastic_query as execute_elasctic_query_via_requests, execute_elastic_aggs as execute_elasctic_aggs_via_requests, execute_function_linux_pid_hierarchy_elastic_requests, execute_function_linux_pid_siblings_elastic_requests
from app.engine.sources.opensearch import execute_opensearch_query, execute_opensearch_aggs
from app.engine.sources.postgresql import execute_postgresql 
from app.engine.sources.sqlite3 import execute_sqlite3
from app.engine.sources.mssql import execute_mssql
from app.engine.sources.ollama import execute_ollama_chat_query
from app.engine.sources.llama import execute_llama_chat_query
from app.engine.sources.pandas import execute_pandas_dynamic_aggregation, execute_pandas_aggregation, execute_pandas_aggregation_with_time_grouper, execute_pandas_shift, execute_pandas_union
from app.engine.sources.grafana import execute_grafana_export_table_requests
from app.engine.sources.youtrack import execute_youtrack_project_finder, execute_youtrack_all_project_issue_finder, execute_youtrack_all_articles_finder
from app.engine.sources.gitlab import execute_gitlab_namespace_owner_request, execute_gitlab_search_request
from app.engine.sources.iris import execute_function_iris_get_alerts
from app.engine.sources.teleport import execute_function_get_hosts_teleport
from app.engine.sources.dns import execute_dns_resolve
from app.engine.sources.mysql import execute_mysql
from app.engine.sources.manticoresearch import execute_manticoresearch_sql
from app.engine.sources.duckdb import execute_duckdb
from app.engine.sources.universal_harvester import execute_local_scenario, execute_get_static_data

ENGINE_SOURCES_AND_FUNCTIONS_MAP = {
    "elastic":{
        "functions":{
            "generic_query":{
                "required":{
                    "index":"example: events-*",
                    "query":"",
                    "fields":"",
                    "sort":"",
                    "size":"",
                    "search_after_shift":-10
                },
                "functions":{
                    "query": execute_elasctic_query_via_client,
                    #"converter":lambda: None
                }
            },
            "aggs_query":{
                "required":{
                    "index":"example: events-*",
                    "query":"",
                    "aggs":"",
                    # "sort":"",
                    # "size":"",
                    # "search_after_shift":-10
                },
                "functions":{
                    "query": execute_elasctic_aggs_via_client,
                    #"converter":lambda: None
                }
            },
            "pid_hierarchy":{
                "required":{
                    "index":"example: events-*",
                    "query":"",
                    "fields":"",
                    "sort":"",
                    "size":"",
                    "search_after_shift":-10
                },
                "functions":{
                    "query": execute_function_linux_pid_hierarchy_elastic,
                    #"converter":lambda: None
                }
            },
            "pid_siblings":{
                "required":{
                    "index":"example: events-*",
                    "query":"",
                    "fields":"",
                    "sort":"",
                    "size":"",
                    "search_after_shift":-10
                },
                "functions":{
                    "query": execute_function_linux_pid_siblings_elastic,
                    #"converter":lambda: None
                }
            }
        },
        "required":{
            "host":"https://elastic.example.ru",
            "port":9201,
            "auth_type":"api_key",# or http_auth
            "max_threads":10
        },
        "unrequired":{
            "verify_certs":False,
            "request_timeout":300,
            "max_retries":2,
            "retry_on_timeout":True,
            "ssl_show_warn":False
        }
    },
    "elastic_requests":{
        "functions":{
            "generic_query":{
                "required":{
                    "url":"https://elastic.ru/api/console/proxy?path=/%(index)s/_search?batched_reduce_size=64&method=POST",
                    "query":"",
                    "fields":"",
                    "sort":"",
                    "size":"",
                    "search_after_shift":-10
                },
                "functions":{
                    "query": execute_elasctic_query_via_requests,
                    #"converter":lambda: None
                }
            },
            "aggs_query":{
                "required":{
                    "url":"https://elastic.ru/api/console/proxy?path=/%(index)s/_search?batched_reduce_size=64&method=POST",
                    "query":"",
                    "aggs":"",
                },
                "functions":{
                    "query": execute_elasctic_aggs_via_requests,
                    #"converter":lambda: None
                }
            },
            "pid_hierarchy":{
                "required":{
                    "url":"https://elastic.ru/api/console/proxy?path=/%(index)s/_search?batched_reduce_size=64&method=POST",
                    "query":"",
                    "fields":"",
                    "sort":"",
                    "size":"",
                    "search_after_shift":-10
                },
                "functions":{
                    "query": execute_function_linux_pid_hierarchy_elastic_requests,
                    #"converter":lambda: None
                }
            },
            "pid_siblings":{
                "required":{
                    "url":"https://elastic.ru/api/console/proxy?path=/%(index)s/_search?batched_reduce_size=64&method=POST",
                    "query":"",
                    "fields":"",
                    "sort":"",
                    "size":"",
                    "search_after_shift":-10
                },
                "functions":{
                    "query": execute_function_linux_pid_siblings_elastic_requests,
                    #"converter":lambda: None
                }
            }
        },
        "required":{
            "max_threads":10
        },
        "unrequired":{
            "verify_certs":False,
            "request_timeout":300
        }
    },
    "opensearch":{
        "functions":{
            "generic_query":{
                "required":{
                    "index":"example: events-*",
                    "query":"",
                    "fields":"",
                    "sort":"",
                    "size":"",
                    "search_after_shift":-10
                },
                "functions":{
                    "query": execute_opensearch_query,
                    #"converter":lambda: None
                }
            },
            "aggs_query":{
                "required":{
                    "index":"example: events-*",
                    "query":"",
                    "aggs":"",
                },
                "functions":{
                    "query": execute_opensearch_aggs,
                    #"converter":lambda: None
                }
            },
        },
        "required":{
            "host":"opensearch.example.ru",
            "port":9200,
            "auth_type":"http_auth",
            "max_threads":10
        },
        "unrequired":{
            "http_compress":True,
            "use_ssl":True,
            "verify_certs":False,
            "ssl_assert_hostname":False,
            "ssl_show_warn":False,
            "timeout":300, 
            "max_retries":2 
        }
    },
    "netbox":{
        "functions":{
            "finder":{
                "required":{
                },
                "functions":{
                    "query": execute_netbox_finder,
                    #"converter": lambda: None
                }
            },
            "search_cidr_by_ip":{
                "required":{
                },
                "functions":{
                    "query": execute_netbox_search_cidr_by_ipaddress,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "url":"https://netbox.example.ru",
            "host":"netbox.example.ru",
            "port":443,
            #"auth_type":"api_key",
            "timeout": 60,
            "max_threads":10
        }, 
        "unrequired":{
            "use_ssl":True
        }
    },
    "manticoresearch":{
        "functions":{
            "sql_query":{
                "required":{
                    "query":"SHOW TABLES"
                },
                "functions":{
                    "query": execute_manticoresearch_sql,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "url":"https://manticoresearch.example.ru:9308/sql?mode=raw",
            "timeout": 60,
            "max_threads":10
        }, 
        "unrequired":{
            "verify":False
        }
    },
    "sqlite3_in_memory":{
        "functions":{
            "query":{
                "required":{
                    "preparatory_queries":["SQL query 1","SQL query 2"],
                    "final_query":"SELECT * FROM anytable;"
                },
                "functions":{
                    "query": execute_sqlite3,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{}, 
        "unrequired":{}
        },
    "duckdb":{
        "functions":{
            "query":{
                "required":{
                    "preparatory_queries":["SQL query 1","SQL query 2"],
                    "final_query":"SELECT * FROM anytable;",
                    "type":"table"# or view
                },
                "functions":{
                    "query": execute_duckdb,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{}, 
        "unrequired":{}
        },
    "postgresql":{
        "functions":{
            "query":{
                "required":{
                    "preparatory_queries":["SQL query 1","SQL query 2"],
                    "final_query":"SELECT * FROM anytable;",
                    "timeout":180
                },
                "functions":{
                    "query": execute_postgresql,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "host":"postgresql.example.ru",
            "port":5432,
            "database":"db",
            "auth_type":"login/pass",
            "max_threads":10
        }, 
        "unrequired":{}
    },
    "mysql":{
        "functions":{
            "query":{
                "required":{
                    "preparatory_queries":["SQL query 1","SQL query 2"],
                    "final_query":"SELECT * FROM anytable;",
                    "timeout":180
                },
                "functions":{
                    "query": execute_mysql,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "host":"mysql.example.ru",
            "port":3306,
            "database":"db",
            "auth_type":"login/pass",
            "max_threads":10
        }, 
        "unrequired":{
            # убедитесь, что эти файлы лежат в storage, обычно storage_path='/srv/storage' 
            "ca.pem":"/mysql/ssl/ca.pem",
            "client-cert.pem":"/mysql/ssl/client-cert.pem",
            "client-key.pem":"/mysql/ssl/client-key.pem"
        }
    },
    "mssql":{
        "functions":{
            "query":{
                "required":{
                    "preparatory_queries":["SQL query 1","SQL query 2"],
                    "final_query":"SELECT * FROM anytable;",
                    "timeout":180,
                    "encoding":"latin-1"
                },
                "functions":{
                    "query": execute_mssql,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "host":"mssql.example.ru",
            "port":5000,
            "database":"db",
            "auth_type":"login/pass",
            "max_threads":10
        }, 
        "unrequired":{}
    },
    "dns":{
        "functions":{
            "query":{
                "required":{},
                "functions":{
                    "query": execute_dns_resolve,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "host":"dns.example.ru",
            "max_threads":10
        }, 
        "unrequired":{}
    },
    "gitlab":{
        "functions":{
            "get_namespace_owner":{
                "required":{},
                "functions":{
                    "query": execute_gitlab_namespace_owner_request,
                    #"converter": lambda: None
                }
            },
            "search":{
                "required":{},
                "functions":{
                    "query": execute_gitlab_search_request
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "url":"https://gitlab.example.ru",
            "timeout": 60,
            #"key":{"system":"foo", "account":"bar"},
            "max_threads":10
        }, 
        "unrequired":{}
    },
    "irp_iris":{
        "functions":{
            "get_all_alerts":{
                "required":{
                    "per_page":10000
                },
                "functions":{
                    "query": execute_function_iris_get_alerts,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "url":"https://iris.example.ru",
            "timeout": 60,
            #"key":{"system":"foo", "account":"bar"},
            "max_threads":10
        }, 
        "unrequired":{}
    },
    "teleport":{       
        "functions":{
            "get_hosts":{
                "required":{
                    "ttl":600
                },
                "functions":{
                    "query": execute_function_get_hosts_teleport,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "host":"teleport.example.ru",
            #"key":[{"system":"teleport", "account":"foo.bar"},{"system":"teleport", "account":"foo.bar_TOTP"}],
            "max_threads":10
        }, 
        "unrequired":{}
    },
    "youtrack":{
        "functions":{
            "search_in_project":{
                "required":{
                    "fields":[{"customFields":["name", {"value":"name"}]}, "summary"]
                },
                "functions":{
                    "query": execute_youtrack_project_finder,
                    #"converter": lambda: None
                }
            },
            "search_in_all_projects":{
                "required":{
                    "fields":[{"customFields":["name", {"value":"name"}]}, "summary"]
                },
                "functions":{
                    "query": execute_youtrack_all_project_issue_finder,
                    #"converter": lambda: None
                }
            },
            "search_in_all_articles":{
                "required":{
                    "fields":["idReadable", "summary"],
                    "fields_with_content":["idReadable", "summary", "content"]
                },
                "functions":{
                    "query": execute_youtrack_all_articles_finder,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "url":"https://youtrack.example.ru",
            "timeout": 60,
            #"key":{"system":"foo", "account":"bar"},
            "max_threads":10
        }, 
        "unrequired":{}
    },
    "grafana":{
        "functions":{
            "get_table":{
                "required":{
                    "data_source_uid":{"9Md-vGvIo": "75"},
                    "api_path": "/api/ds/query/",
                    "datasource_type": "prometheus",
                    "expr":'probe_success{job=\\"vm\\"}',
                    #https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
                    "server_timezone":"Europe/Moscow",
                    "ttl":600
                },
                "functions":{
                    "query": execute_grafana_export_table_requests,
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{
            "url":"https://grafana.example.ru",
            #"key":{"system":"foo", "account":"bar"},
            "max_threads":10
        }, 
        "unrequired":{}
    },
    "python_requests":{
        "functions":{
            "nane":{
                "required":{
                    "url":""
                }
            }
        }, 
        "required":{}, 
        "unrequired":{}
    },
    "pandas":{
        "functions":{
            "dynamic_aggr":{
                "required":{
                    "target_data":"vpn_data",
                    "list_to_str_dict":{'kibana.alert.rule.indices':'indices'},
                    "groupby_list":[
                        "host.hostname", #*
                        "decorations.computer_name",
                        "kibana.alert.rule.name", #*
                        "signal.rule.description",
                        "indices",
                        "process.command_line" #*
                    ],
                    "agg_dict":{
                        '@timestamp': ['min',"max","count"],
                        'signal.original_time': ['min',"max","count"],
                        'process.pid': ['min',"max","count"]
                    },
                    "dynamic_groupby_list":["host.hostname","kibana.alert.rule.name","process.command_line"],
                    "dynamica_agg_dict" :{
                        "@timestamp_min":"min",
                        "@timestamp_max":"max",
                        "@timestamp_count":"sum"
                    }
                },
                "functions":{
                    "query": execute_pandas_dynamic_aggregation,
                    #"converter": lambda: None
                }
            },
            "aggr":{
                "required":{
                    "target_data":"vpn_data",
                    "list_to_str_dict":{'kibana.alert.rule.indices':'indices'},
                    "groupby_list":[
                        "host.hostname", #*
                        "decorations.computer_name",
                        "kibana.alert.rule.name", #*
                        "signal.rule.description",
                        "indices",
                        "process.command_line" #*
                    ],
                    "agg_dict":{
                        '@timestamp': ['min',"max","count"],
                        'signal.original_time': ['min',"max","count"],
                        'process.pid': ['min',"max","count"]
                    }
                },
                "functions":{
                    "query": execute_pandas_aggregation,
                    #"converter": lambda: None
                }
            },
            "time_grouper_aggr":{
                "required":{
                    "target_data":"vpn_data",
                    "list_to_str_dict":{'kibana.alert.rule.indices':'indices'},
                    "groupby_list":[
                        "host.hostname", #*
                        "decorations.computer_name",
                        "kibana.alert.rule.name", #*
                        "signal.rule.description",
                        "indices",
                        "process.command_line" #*
                    ],
                    "agg_dict":{
                        '@timestamp': ['min',"max","count"],
                        'signal.original_time': ['min',"max","count"],
                        'process.pid': ['min',"max","count"]
                    }
                },
                "functions":{
                    "query": execute_pandas_aggregation_with_time_grouper,
                    #"converter": lambda: None
                }
            },
            "shift":{
                "required":{
                    "target_data":"vpn_data",
                    "list_to_str_dict":{'kibana.alert.rule.indices':'indices'},
                    "groupby_list":[ # может быть пустым
                        "host.hostname", #*
                        "decorations.computer_name",
                        "kibana.alert.rule.name", #*
                        "signal.rule.description",
                        "indices",
                        "process.command_line" #*
                    ],
                    "target_column":"column",
                    "result_column":"shifted_column",
                    "shift":1,
                    "fill_value":""
                },
                "functions":{
                    "query": execute_pandas_shift,
                    #"converter": lambda: None
                }
            },
            "union":{
                "required":{
                    "target_data":["data_1", "data_2"]
                },
                "functions":{
                    "query": execute_pandas_union
                    #"converter": lambda: None
                }
            }
        }, 
        "required":{}, 
        "unrequired":{}
    },
    "ollama":{
        "functions":{
            "chat":{
                "required":{
                    "url":"https://localhost:11434/api/chat",
                    "model":"llama3.2",
                    "format":"",
                    "main_prompt":"",
                    "data_for_analysis":["data1", "data2"]
                },
                "functions":{
                    "query": execute_ollama_chat_query,
                    #"converter":lambda: None
                }
            }
        },
        "required":{
            #"key":{"system":"foo", "account":"bar"},
            "max_threads":10
        },
        "unrequired":{
            "verify_certs":False,
            "request_timeout":300
        }
    },
    "llama":{
        "functions":{
            "chat":{
                "required":{
                    "model_path":"/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf",
                    "context_length":16000,
                    "cpu_threads":32,
                    "gpu_layers":0,
                    "max_tokens":32000,
                    "stop":["</s>"],
                    "data_for_analysis":["data1", "data2"]
                },
                "functions":{
                    "query": execute_llama_chat_query,
                    #"converter":lambda: None
                }
            }
        },
        "required":{
            "max_threads":2
        },
        "unrequired":{
            "verify_certs":False,
            "request_timeout":300
        }
    },
    "universal_harvester":{
        "functions":{
            "local_scenario":{
                "required":{
                    "scenario_name":"[BB] Local scenario",
                    "result_data_name":"data_name",
                    "parameters":{"data1", "data2"}
                },
                "functions":{
                    "query": execute_local_scenario,
                    #"converter":lambda: None
                }
            },
            "get_static_data":{
                "required":{
                    "static_data_name":"dict",
                    "limit":1000000
                },
                "functions":{
                    "query": execute_get_static_data,
                    #"converter":lambda: None
                }
            }
        },
        "required":{
            "max_threads":999
        },
        "unrequired":{}
    }
    #"kaspersky_kata":{"functions":{}, "required":{}, "unrequired":{}},
}

def engine_hasshin(data, current_state):
    ####################################
    # пишем в базу новую таску
    ####################################
    db_upsert_task_result = db_upsert_task(
        data, 
        current_state)
    if db_upsert_task_result[0] == False: # если не удалось записать
        error_message = f"New task writing error: {db_upsert_task_result[1]}", f"{db_upsert_task_result[2]}->{currentFuncName()}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, None
    
    ####################################
    # создаём shared memory block
    ####################################
    create_shared_memory_block_result = create_shared_memory_block(data["id"], current_state)
    if create_shared_memory_block_result[0] == False:
        error_message = f"Shared memory creating error: {create_shared_memory_block_result[1]}", f"{create_shared_memory_block_result[2]}->{currentFuncName()}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, None
    
    ####################################
    # запускаем экземпляр движка и передаём ему shared memory block в качестве параметра
    ####################################
    
    try:
        engine_pid = os.spawnl(os.P_NOWAIT, sys.executable, sys.executable, f'{current_state["engine_path"]}',f'--shared_memory_name={create_shared_memory_block_result[3]}')
        #engine_pid = os.spawnl(os.P_NOWAIT, f'{current_state["engine_path"]}', f'{current_state["engine_path"]}', f'-s',f'{create_shared_memory_block_result[3]}')
    except BaseException as e:
        error_message = f"Start engine for task {data['id']} error: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        # неуданый запуск, мы должны обновить таску в БД и поставить статус ошибки
        # обновляем таску, ставим статус -1:"Движок не был запущен, задача остановлена",# текст ошибки
        data["status_code"] = -1
        data["status"] = error_message
        data["timestamp_stop"] = currentTimestamp()

        db_upsert_task_result = db_upsert_task(
            data, 
            current_state)
        if db_upsert_task_result[0] == False:
            return False, f"Crashed task upserting error: {db_upsert_task_result[1]}", f"{db_upsert_task_result[2]}->{currentFuncName()}", None
            
        return False, error_message, currentFuncName(), None
    # обновляем pid в новой таске 1:"По таске запущен движок, ожидает выполнения", #ок   
    data["status_code"] = 0
    data["pid"] = engine_pid

    db_upsert_task_result = db_upsert_task(
        data, 
        current_state)
    if db_upsert_task_result[0] == False:
        return False, db_upsert_task_result[1], db_upsert_task_result[2], None

    return True, f"id:{data['id']} pid:{engine_pid}", currentFuncName(), None

def get_key(key_node: Dict, current_state: Dict):
    if isinstance(key_node, Dict):
        if "system" in key_node and "account" in key_node:
            # пробуем забрать ключ из хранилища
            db_get_key_result = db_get_key(
                {"system":key_node["system"], "account":key_node["account"]},current_state)
            if db_get_key_result[0] == False:
                return False, f'db error for key {key_node["system"]}/{key_node["account"]}:{db_get_key_result[2]}/{db_get_key_result[1]}', currentFuncName(), None
            key_node["value"] = db_get_key_result[3][2]

            # снимаем шифрование
            decrypt_result = decrypt(key_node["value"], current_state)
            if decrypt_result[0] == False:
                logger_log(syslog.LOG_ERR, get_log_message(decrypt_result[1], currentFuncName(), current_state))
                return False, f'cryptography error for key {key_node["system"]}/{key_node["account"]}: {decrypt_result[1]}', currentFuncName(), None

            key_node["value"] = decrypt_result[3]

            return True, f'OK', currentFuncName(), key_node["value"]
    return False, f'key_node is not valid', currentFuncName(), None

def engine_source_parameters_validator(sources_map, from_db_source, current_state):
    try:
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
        # Проверяем, что это валидный json
        if check_json_correct(from_db_source) == False:
            return False, "from_db_source is not a valid json", currentFuncName(), None
            
        source_json = json.loads(from_db_source)
        # Проверяем, что это dict
        if not isinstance(source_json, dict):
            return False, "source_json is not a dict", currentFuncName(), None
        # Проверяем наличие ключа type
        if "type" not in source_json:
            return False, "there is not type in source_json", currentFuncName(), None
        # Проверяем, что такой type есть в карте
        if source_json["type"] not in sources_map:
            return False, "there is not source_json type in map", currentFuncName(), None
        # Пробегаемся по обязательным параметрам и проверяем их наличие
        for required in sources_map[source_json["type"]]["required"].keys():
            if required not in source_json:
                return False, f"there is not required parameter {required} in source_json", currentFuncName(), None
        # пробегаемся по необязательным параметрам, и если они не определены -- добавляем их как default
        for unrequired in sources_map[source_json["type"]]["unrequired"].keys():
            if unrequired not in source_json:
                source_json[unrequired] = sources_map[source_json["type"]]["unrequired"][unrequired]

        # проверяем наличие блока ключей
        # в целом он необязателен
        if "key" in source_json:
            if isinstance(source_json["key"], list) == True:
                for key_node in source_json["key"]:
                    get_key_result = get_key(key_node, current_state)
                    if get_key_result[0] == False:
                        return False, f'key proc error: {get_key_result[1]}', currentFuncName(), None
                    key_node["value"] = get_key_result[3]
            elif isinstance(source_json["key"], dict) == True:
                get_key_result = get_key(source_json["key"], current_state)
                if get_key_result[0] == False:
                    return False, f'key proc error: {get_key_result[1]}', currentFuncName(), None
                source_json["key"]["value"] = get_key_result[3]
            else:
                return False, f'wrong key node type', currentFuncName(), None

        # вы великолепны
        # тут имеем корректный source_json c добавленными необязательными параметрами и ключами
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), source_json
    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), None



def process_injections(node, parameters, current_state):
    """Функция, которая позволяет подставить параметры в блок query шага. Изначально она работала на %()s встроенной
    функции python, но это работает не совсем корректно. Таким образом сложно вставить integer в валидный json. Поэтому
    эта функция была переписана с возможностью вставлять string (s), integer (i), float (f), boolean (b), list (l), dict (d)."""

    try:
        logger_log(syslog.LOG_DEBUG, get_log_message("start", currentFuncName(), current_state))
        # node_string = json.dumps(node)
        # node_string = node_string % parameters
        # injected_node = json.loads(node_string)

        node_string = json.dumps(node)

        for parameter in parameters.keys():
            value = parameters[parameter]
            regular_expression = fr'%\({parameter}\)[sifbldx]'
            parameter_positions = [m.start() for m in re.finditer(regular_expression, node_string)]
            #print(parameter_positions, len(parameter), parameter)

            next_change_shift = 0
            for position in parameter_positions:
                injection_position = position + next_change_shift
                injection_type_position = injection_position + 2 + len(parameter) + 1
                injection_type = node_string[injection_type_position]
                injection_end_position = injection_type_position + 1

                quotation_mark_shift = 0

                if node_string[injection_position-1] == '"' and node_string[injection_end_position] == '"':
                    quotation_mark_shift = 1

                #print(injection_type, next_change_shift, node_string[injection_position:injection_end_position])
                #print(node_string)
                if injection_type == "s": #string вставляется как есть без впопросов и проблем
                    node_string = node_string[:injection_position] + str(value) + node_string[injection_end_position:]
                    current_next_shift = len(value) - (injection_end_position - injection_position)
                    next_change_shift = next_change_shift + current_next_shift
                elif injection_type == "x": #x вставляет строку без кавычек, то есть это прямая инъекция, что может быть не совсем безопасно
                    node_string = node_string[:injection_position-quotation_mark_shift] + str(value) + node_string[injection_end_position+quotation_mark_shift:]
                    current_next_shift = len(value) - (injection_end_position - injection_position)
                    next_change_shift = next_change_shift + current_next_shift
                elif injection_type == "i":
                    input_value = f"{value}"
                    node_string = node_string[:injection_position-quotation_mark_shift] + input_value + node_string[injection_end_position+quotation_mark_shift:]
                    current_next_shift = len(input_value) - (injection_end_position - injection_position)
                    next_change_shift = next_change_shift + current_next_shift
                elif injection_type == "f":
                    input_value = "{0:0.9f}".format(value)
                    node_string = node_string[:injection_position-quotation_mark_shift] + input_value + node_string[injection_end_position+quotation_mark_shift:]
                    current_next_shift = len(input_value) - (injection_end_position - injection_position)
                    next_change_shift = next_change_shift + current_next_shift
                elif injection_type == "b":
                    if value:
                        node_string = node_string[:injection_position-quotation_mark_shift] + "true" + node_string[injection_end_position+quotation_mark_shift:]
                        current_next_shift = 4 - (injection_end_position - injection_position)
                    else:
                        node_string = node_string[:injection_position-quotation_mark_shift] + "false" + node_string[injection_end_position+quotation_mark_shift:]
                        current_next_shift = 5 - (injection_end_position - injection_position)
                    
                    next_change_shift = next_change_shift + current_next_shift
                elif injection_type == "l" or injection_type == "d":
                    injection_string = json.dumps(value)
                    node_string = node_string[:injection_position-quotation_mark_shift] + str(injection_string) + node_string[injection_end_position+quotation_mark_shift:]
                    current_next_shift = len(injection_string) - (injection_end_position - injection_position)
                    next_change_shift = next_change_shift + current_next_shift
                else:
                    error_message = f"undefined injection_type: {str(injection_type)}"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), {}

        if check_json_correct(node_string) == False:
            error_message = f"incorrect json injected_node after injections"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
        
        injected_node = json.loads(node_string)
        logger_log(syslog.LOG_DEBUG, get_log_message("done", currentFuncName(), current_state))
        return True, "OK", currentFuncName(), injected_node

    except BaseException as e:
        error_message = f"process_injections fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {}

def search_parameter_in_apply(apply_node: dict, parameter_name, current_state):
    if "target_parameters" not in apply_node:
        error_message = f"target_parameters not in apply_node"
        logger_log(syslog.LOG_WARNING, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {}
    if isinstance(apply_node["target_parameters"], list) == False:
        error_message = f"target_parameters in apply_node is not a list"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), {}
    for target_parameter in apply_node["target_parameters"]:
        if "as" not in target_parameter:
            error_message = f"there is not as node in target_parameter"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), {}
        if target_parameter["as"] == parameter_name:
            return True, "OK", currentFuncName(), target_parameter
    return True, "not found", currentFuncName(), {}

def process_parameters_generation(apply_node: dict, generator_node, parameters, step_input_parameters, current_state):
    try:
        new_parameters = parameters

        for generated_parameter_key in generator_node.keys():
            generated_parameter = generator_node[generated_parameter_key]
            if "type" not in generated_parameter:
                error_message = f"there is not type in {generated_parameter_key} generator node"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), {}
            
            type = generated_parameter["type"]
            if type == "copy":
                if "copy_source" not in generated_parameter:
                    error_message = f"there is not required_key copy_source in {generated_parameter_key} generator node"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), {}
                copy_source = generated_parameter["copy_source"]

                search_parameter_in_apply_result = search_parameter_in_apply(apply_node, copy_source, current_state)
                apply_copy_source = search_parameter_in_apply_result[3]

                if copy_source not in parameters:
                    # параметра-источника нет в параметрах. Это исключение, но может он в апплай?
                    if "as" not in apply_copy_source:
                        # это не апплай
                        error_message = f"there is not copy_source {copy_source} in parameters"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), {}
                    else:
                        if apply_copy_source["as"] == copy_source:
                            error_message = f"there is copy_source {copy_source} in apply node, but there is not in parameters"
                            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                            return False, error_message, currentFuncName(), {}
                        else:
                            error_message = f"there is not copy_source {copy_source} in apply node? (why?)"
                            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                            return False, error_message, currentFuncName(), {}
                
                new_parameters[generated_parameter_key] = parameters[copy_source]
                
            elif type == "-timedelta":
                #на всякий случай поищем apply ноду
                search_parameter_in_apply_result = search_parameter_in_apply(apply_node, generated_parameter["timestamp_field"], current_state)
                apply_timestamp_field = search_parameter_in_apply_result[3]
                # search_parameter_in_apply_result = search_parameter_in_apply(apply_node, generated_parameter["delta_field"], current_state)
                # apply_delta_field = search_parameter_in_apply_result[3]

                # вычитаем из времени дельту и возвращаем текстом по формату datetime
                # проверяем наличие полей
                for required_key in ["timestamp_field", "delta_field", "output_format"]:
                    if required_key not in generated_parameter:
                        error_message = f"there is not required_key {required_key} in {generated_parameter} generator node"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), {}
                    
                # проверяем, что дельта существует в параметрах и это integer
                if generated_parameter["delta_field"] not in parameters:
                    # дельта может быть динамической из apply
                    error_message = f"there is not delta_field in parameters for generated_parameter {generated_parameter_key}"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), {}
                
                time_delta = parameters[generated_parameter["delta_field"]]

                if not isinstance(time_delta, int):
                    error_message = f"delta_field is not an integer for generated_parameter {generated_parameter_key}"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), {}
                
                # проверяем наличие основного поля времени в блоке параметров или apply
                if generated_parameter["timestamp_field"] not in parameters:
                    error_message = f"there is not timestamp_field {generated_parameter['timestamp_field']} in parameters"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), {}
                else:
                    parameter_timestamp = parameters[generated_parameter["timestamp_field"]]

                # проверяем наличие формата в блоке параметров или apply
                if generated_parameter["timestamp_field"] in step_input_parameters:
                    # не апплай
                    if "format" in step_input_parameters[generated_parameter["timestamp_field"]]:
                        input_format = step_input_parameters[generated_parameter["timestamp_field"]]["format"]
                    else:
                        error_message = f"there is not format node in step_input_parameters"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), {}
                else:
                    # апплай
                    if "as" in apply_timestamp_field:
                        if "format" in apply_timestamp_field:
                            input_format = apply_timestamp_field["format"]
                        else:
                            error_message = f"there is not format node in apply_timestamp_field"
                            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                            return False, error_message, currentFuncName(), {}
                    else:
                        error_message = f"cannot get format - there is not as node in apply_timestamp_field"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), {}

                # создаём новый параметр
                original_timestamp = datetime.strptime(
                    parameter_timestamp, 
                    input_format)
                
                new_timestamp = original_timestamp - timedelta(seconds=time_delta)
                new_parameters[generated_parameter_key] = new_timestamp.strftime(generated_parameter["output_format"])
            elif type == "+timedelta":
                #на всякий случай поищем apply ноду
                search_parameter_in_apply_result = search_parameter_in_apply(apply_node, generated_parameter["timestamp_field"], current_state)
                apply_timestamp_field = search_parameter_in_apply_result[3]
                # search_parameter_in_apply_result = search_parameter_in_apply(apply_node, generated_parameter["delta_field"], current_state)
                # apply_delta_field = search_parameter_in_apply_result[3]

                # вычитаем из времени дельту и возвращаем текстом по формату datetime
                # проверяем наличие полей
                for required_key in ["timestamp_field", "delta_field", "output_format"]:
                    if required_key not in generated_parameter:
                        error_message = f"there is not required_key {required_key} in {generated_parameter} generator node"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), {}
                    
                # проверяем, что дельта существует в параметрах и это integer
                if generated_parameter["delta_field"] not in parameters:
                    # дельта может быть динамической из apply
                    error_message = f"there is not delta_field in parameters for generated_parameter {generated_parameter_key}"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), {}
                
                time_delta = parameters[generated_parameter["delta_field"]]

                if not isinstance(time_delta, int):
                    error_message = f"delta_field is not an integer for generated_parameter {generated_parameter_key}"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), {}
                
                # проверяем наличие основного поля времени в блоке параметров или apply
                if generated_parameter["timestamp_field"] not in parameters:
                    error_message = f"there is not timestamp_field {generated_parameter['timestamp_field']} in parameters"
                    logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                    return False, error_message, currentFuncName(), {}
                else:
                    parameter_timestamp = parameters[generated_parameter["timestamp_field"]]

                # проверяем наличие формата в блоке параметров или apply
                if generated_parameter["timestamp_field"] in step_input_parameters:
                    # не апплай
                    if "format" in step_input_parameters[generated_parameter["timestamp_field"]]:
                        input_format = step_input_parameters[generated_parameter["timestamp_field"]]["format"]
                    else:
                        error_message = f"there is not format node in step_input_parameters"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), {}
                else:
                    # апплай
                    if "as" in apply_timestamp_field:
                        if "format" in apply_timestamp_field:
                            input_format = apply_timestamp_field["format"]
                        else:
                            error_message = f"there is not format node in apply_timestamp_field"
                            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                            return False, error_message, currentFuncName(), {}
                    else:
                        error_message = f"cannot get format - there is not as node in apply_timestamp_field"
                        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                        return False, error_message, currentFuncName(), {}

                # создаём новый параметр
                original_timestamp = datetime.strptime(
                    parameter_timestamp, 
                    input_format)
                
                new_timestamp = original_timestamp + timedelta(seconds=time_delta)
                new_parameters[generated_parameter_key] = new_timestamp.strftime(generated_parameter["output_format"])
            # сюда можно добавить новые генераторы
            # генератор now()
            else:
                error_message = f"wrong generated_parameter type {type} for generated_parameter {generated_parameter_key}"
                logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
                return False, error_message, currentFuncName(), {}


        return True, "OK", currentFuncName(), new_parameters
                    



    except BaseException as e:
        error_message = f"process parameter generator fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), new_parameters

def get_step_dependency(step, source, current_query, current_state):
    try:
        #print("\nget_step_dependency\n", step, source)
        dependency = []
        if "apply" in step:
            dependency.append(step["apply"]["target_data"])

        if "data_for_analysis" in current_query:
            if isinstance(current_query["data_for_analysis"], list):
                for data_for_analysis in current_query["data_for_analysis"]:
                    dependency.append(data_for_analysis["data_name"])
        
        if "target_data" in current_query and source["type"] == "pandas": 
            if isinstance(current_query["target_data"], str):
                dependency.append(current_query["target_data"])
            elif isinstance(current_query["target_data"], list):
                dependency = dependency + current_query["target_data"]

        if source["type"] in ["sqlite3", "sqlite3_in_memory", "duckdb"]:
            # представляем весь блок query кка одну строку и ищем в ней зависимости
            # тут будут в кучу preparatory и final
            sql_dependency = []
            sql_with_statement = []
            query_string = json.dumps(current_query)
            for sql_depend in re.findall(r"(FROM|JOIN)\s+([^\s;)]+)",query_string):
                sql_dependency.append(sql_depend[1])
            for sql_with in re.findall(r"(WITH|\),)\s+([^\s;]+)\s+AS\s+\(",query_string):
                sql_with_statement.append(sql_with[1])
            for sql_dependency_candidate in sql_dependency:
                if sql_dependency_candidate not in sql_with_statement:
                    dependency.append(sql_dependency_candidate)
  
        return True, "OK", currentFuncName(), list(set(dependency))
    
    except BaseException as e:
        error_message = f"get_step_dependency fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), dependency


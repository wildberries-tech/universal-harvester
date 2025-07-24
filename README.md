# Universal Harvester

## Description
Подключай, собирай, преобразовывай. Долго запрягаем, зато быстро едем.

Universal Harvester представляет собой платформу для создания автоматизаций получения и обработки данных, единое окно входа где пользователь или иная система может получить осмысленные и обогащённые данные, необходимые для решения конкретной задачи. Данный инструмент был создан в SOC для решения задач SOC, но при этом является независимым от данных и области деятельности. Главное чтобы был ландшафт данных и осмысленные задачи. Вы можете получать любые данные из широкого спектра возможных источников данных, предобрабатывать, объединять (JOIN) и соединять (UNION [ALL]), что позволяет решить широкий спектр практических задач. 

Для работы с Universal Harvester вам понадобится: развернуть приложение, добавить в него пользователей, источники данных и учётные данные к ним, написать шаги получения или обработки данных, объединить шаги в сценарий, назначить пользователям, шагам и сценариям соответствующие роли. Это потребует глубоких знаний в системах хранения данных, в самих данных и в языке SQL. Сохранив всё это в виде сценария вы сможете тиражировать компетенции в виде доступа к готовым сценариям в вашей конкретной инфраструктуре.

## Abitities
Куда Universal Harvester может подключиться и что сделать:
| Source type                    | Function               | Comment                                                                                  |
|--------------------------------|------------------------|------------------------------------------------------------------------------------------|
| elastic                        | generic query          | Обычный запрос на получение данных с помощью API (как в discover > inspect > request)    |
|                                | aggs query             | Запрос агрегации данных с помощью API (как в visualize > data table > inspect > request) |
| elastic proxypass (via kibana) | generic query          | Обычный запрос на получение данных с помощью API (как в discover > inspect > request)    |
|                                | aggs query             | Запрос агрегации данных с помощью API (как в visualize > data table > inspect > request) |
| opensearch                     | generic query          | Обычный запрос на получение данных с помощью API (как в discover > inspect > request)    |
|                                | aggs query             | Запрос агрегации данных с помощью API (как в visualize > data table > inspect > request) |
| netbox                         | netbox finder          | Запрос записи по IP-адресу                                                               |
|                                | cidr search            | Поиск по IP-адресу наименьшей по маске записи                                            |
| sqlite3_in_memory              | query                  | Запрос обработки данных в рамках исполнения сценария в виртуальной БД sqlite3            |
| duckdb                         | query                  | Запрос обработки данных в рамках исполнения сценария в виртуальной БД duckdb             |
| postgresql                     | query                  | Запрос к СУБД PostgreSQL                                                                 |
| mssql                          | query                  | Запрос к СУБД MSSQL                                                                      |
| mysql                          | query                  | Запрос к СУБД MySQL                                                                      |
| dns                            | query                  | Выполение DNS-запроса (разыменование доменного имени)                                    |
| gitlab                         | get namespace owner    | Получение владельца namespace                                                            |
|                                | search                 | Стандартный поиск по gitlab API                                                          |
| iris irp                       | get all alerts         | Получение всех алертов по хосту                                                          |
| teleport                       | get hosts              | Получение списка всех хостов                                                             |
| youtrack                       | search in project      | Поиск документов по проекту                                                              |
|                                | search in all projects | Поиск документов по всем проеткам                                                        |
|                                | search in all articles | Поиск статей по базе знаний                                                              |
| grafana                        | get table              | Получение таблицы из grafana                                                             |
| pandas_in_memory               | aggr                   | Обычная агрегация данных с помощью pandas                                                |
|                                | time grouper aggr      | Обычная агрегация данных с помощью pandas + группировка по времени                       |
|                                | dynamic aggr           | Динамическая агрегация (максимальная компановка данных)                                  |
| ollama                         | chat                   | Обработка данных с помощью LLM (ollama api)                                              |
| manticore                      | requests query         | Получение данных из Manticore                                                            |
| universal harvester            | run local_scenario     | Получение данных из Universal harvester (itself)                                         |

Дополнительные кастомные действия:
| Source type                    | Function      | Comment                                                                 |
|--------------------------------|---------------|-------------------------------------------------------------------------|
| elastic                        | pid hierarchy | Сбор иерархии процессов по выбранному (в данных osquery process events) |
| elastic proxypass (via kibana) | pid hierarchy | Сбор иерархии процессов по выбранному (в данных osquery process events) |
| elastic                        | pid siblings  | Сбор сиблингов процесса по выбранному (в данных osquery process events) |
| elastic proxypass (via kibana) | pid siblings  | Сбор сиблингов процесса по выбранному (в данных osquery process events) |

## Visuals

## How to use
### System requirements
Системные требования, предъявляемые к виртуальной или железной машине, зависят от объёма данных, которые предполагается обрабатывать с помощью приложения. Основные узкие места в порядке приоритета: ОЗУ, ЦПУ, ПЗУ, пропускная способность сети. При работе приложения все данные одновременно выполняемых сценариев не должны превышать ОЗУ (с учётом работы ОС и docker). ЦПУ станет узким местом при выполнении большого количества небольших по объёму данных сценариев, но с большим количеством шагов. ПЗУ (storage) сохраняет данные по всем выполняемым сценариям, будьте уверены, что хранилище не переполнится. Также скорость работы Universal Harvester зависит от скорости работы ПЗУ (задержки доступа, чтение и запись) (Модуль Health TBD). Пропускная способность сети может стать узким местом, если вы попытаетесь получить большое количество данных через узкий канал связи. Убедитесь, что имеется надёжная сетевая связность между хостом Universal Harvester и источниками данных.

#### Minimal
Raspberry Pi 5

#### Optimal
8+ core CPU, 64Gb+ RAM, Linux, 1G Network

#### Ideal
64+ core CPU, 640Gb RAM, Linux, 10G Network

### Deploy
Развёртывание приложения прощего осуществить с помощью Docker-контейнера, но также возможно и прямое развертывание на хосте

#### Local
1. Клонируйте репозиторий на хост.
2. Обеспечте окружение python (pip install -r requirements.txt).
3. Определите используемую БД (с помощью ноутбука base64_json_object_creator.ipynb).
4. Сгенерируйте ключ nicegui storage (с помощью ноутбука base64_json_object_creator.ipynb).
5. Сгенерируйте master_key (с помощью ноутбука base64_json_object_creator.ipynb).
6. Сформируйте строку запуска.
7. Запустите front.py со всеми необходимыми параметрами.
8. Интерактивно введите master_key.

#### Docker
1. Клонируйте репозиторий.
2. Соберите под нужную архитектуру и доставьте docker контейнер на хост.
3. Определите используемую БД (с помощью ноутбука base64_json_object_creator.ipynb).
4. Сгенерируйте ключ nicegui storage (с помощью ноутбука base64_json_object_creator.ipynb).
5. Сгенерируйте master_key (с помощью ноутбука base64_json_object_creator.ipynb).
6. Сформируйте строку запуска.
7. Запустите контейнер -> front.py со всеми необходимыми параметрами.
8. Интерактивно введите master_key.

Пример:
```bash
docker run --log-driver syslog --network=host --log-opt syslog-address=udp://127.0.0.1:514 --mount type=bind,source=/mnt/storage/universal_harvester/storage,target=/srv/storage -it universal_harvester_docker_amd64 front.py --host='0.0.0.0' --port=443 --ssl_keyfile='path' --ssl_certfile='path' --itself_link='https://universalharvester.local:443/' --storage_path='/srv/storage' --health_module_path='health.py' --scheduler_module_path='scheduler.py' --engine_module_path='engine.py' --nicegui_storage_key_object='[сформировано с помощью ноутбука base64_json_object_creator.ipynb]' --db_conf_object='[сформировано с помощью ноутбука base64_json_object_creator.ipynb]'
```
Блок 
```bash 
... --log-driver syslog --network=host --log-opt syslog-address=udp://127.0.0.1:514
```
отвечает за механизмы логирования и доступа к Universal Harvester по сети.

Блок 
```bash 
... --mount type=bind,source=/mnt/storage/universal_harvester/storage,target=/srv/storage
```
отвечает за доступ к хранилищу из контейнера. Убедитесь, что существование хранилища не зависит от существования контейнера.

#### Keycloak
Universal Harvester имеет функционал интеграции с Keycloak. Для интеграции необходимо добавить в ключи (таблица keys) секрет клиента Keycloak, после этого указать в строке запуска параметры keycloak. Параметр keycloak_key указывается в виде system_name:account_name таблицы keys. 
```bash
... --keycloak_url='https://keycloak.example.ru' --keycloak_client_id='harvester.example.ru' --keycloak_realm_id='example_realm' --keycloak_key='keycloak.example.ru:harvester.example.ru'
```

#### Credentials
Стандартная УЗ при инициализации БД default_admin:universal_harvester , при первом входе рекомендуется создать новую админскую УЗ, а default_admin отключить.

#### Access networks
Стандартная сеть доступа: 127.0.0.0/8, при необходимости добавьте другие (пока что прямыми запросами в БД)
```sql
INSERT INTO access_networks (ip_network, allow, comment) VALUES('0.0.0.0/0', true, 'all');
```

# Usage
## Users
Управление УЗ производится через интерфейс приложения в меню USERS. Заполните роли для каждого пользователя. Роль суперадмина определена как fullmaster.
### Ролевая модель
| Роль                      | USERS                                            | KEYS                                       | SOURCES                                       | STEPS                                                         | TASKS                                             | SCENARIOS                                                                           | SCENARIOS EDITOR                                        | SCHEDULER |
|---------------------------|--------------------------------------------------|--------------------------------------------|-----------------------------------------------|---------------------------------------------------------------|---------------------------------------------------|-------------------------------------------------------------------------------------|---------------------------------------------------------|-----------|
| fullmaster                | Полное редактирование всех УЗ, создание новых УЗ | Просмотр,создание, редактирование секретов | Просмотр, создание, редактирование источников | Просмотр, изменение, создание, копирование, запуск всех шагов | Просмотр, перезапуск, остановка всех задач        | Доступны все сценарии, вся история запусков                                         | Просмотр, редактирование, копирование всех сценариев    | TBD       |
| users_admin               | Полное редактирование всех УЗ, создание новых УЗ | Недоступно                                 | Недоступно                                    | Просмотр, запуск шагов в соответствии с собственными ролями   | Просмотр, перезапуск, остановка собственных задач | Доступны сценарии в соответствии с собственными ролями, собственная история запуска | Просмотр сценариев в соответствии с собственными ролями | TBD       |
| keys_admin                | Просмотр своей УЗ, изменение своего пароля       | Просмотр,создание, редактирование секретов | Недоступно                                    | Просмотр, запуск шагов в соответствии с собственными ролями   | Просмотр, перезапуск, остановка собственных задач | Доступны сценарии в соответствии с собственными ролями, собственная история запуска | Просмотр сценариев в соответствии с собственными ролями | TBD       |
| sources_admin             | Просмотр своей УЗ, изменение своего пароля       | Недоступно                                 | Просмотр, создание, редактирование источников | Просмотр, запуск шагов в соответствии с собственными ролями   | Просмотр, перезапуск, остановка собственных задач | Доступны сценарии в соответствии с собственными ролями, собственная история запуска | Просмотр сценариев в соответствии с собственными ролями | TBD       |
| steps_admin               | Просмотр своей УЗ, изменение своего пароля       | Недоступно                                 | Недоступно                                    | Просмотр, изменение, создание, копирование, запуск всех шагов | Просмотр, перезапуск, остановка собственных задач | Доступны сценарии в соответствии с собственными ролями, собственная история запуска | Просмотр сценариев в соответствии с собственными ролями | TBD       |
| tasks_admin               | Просмотр своей УЗ, изменение своего пароля       | Недоступно                                 | Недоступно                                    | Просмотр, запуск шагов в соответствии с собственными ролями   | Просмотр, перезапуск, остановка всех задач        | Доступны сценарии в соответствии с собственными ролями, собственная история запуска | Просмотр сценариев в соответствии с собственными ролями | TBD       |
| scenarios_admin           | Просмотр своей УЗ, изменение своего пароля       | Недоступно                                 | Недоступно                                    | Просмотр, запуск шагов в соответствии с собственными ролями   | Просмотр, перезапуск, остановка собственных задач | Доступны все сценарии, вся история запусков                                         | Просмотр сценариев в соответствии с собственными ролями | TBD       |
| scenario_editor_admin     | Просмотр своей УЗ, изменение своего пароля       | Недоступно                                 | Недоступно                                    | Просмотр, запуск шагов в соответствии с собственными ролями   | Просмотр, перезапуск, остановка собственных задач | Доступны сценарии в соответствии с собственными ролями, собственная история запуска | Просмотр, редактирование, копирование всех сценариев    | TBD       |
| custom (собственные роли) | Просмотр своей УЗ, изменение своего пароля       | Недоступно                                 | Недоступно                                    | Просмотр, запуск шагов в соответствии с собственными ролями   | Просмотр, перезапуск, остановка собственных задач | Доступны сценарии в соответствии с собственными ролями, собственная история запуска | Просмотр сценариев в соответствии с собственными ролями | TBD       |

У пользователя может быть несколько ролей.

### User json and notifications
Дополнительные данные пользователя могу включать в себя любые дополнительные поля кроме блока notify. Блок notify определяет тип оповещения для пользователя.
```json
{
  "any_fields": "",
  "notify": {
    "mattermost": {
      "enabled": true,
      "server": "mattermost.example.ru",
      "username": "username of user in mattermost",
      "key": {
        "system": "system in keys (creds link for mattermost.example.ru)",
        "account": "account in keys (creds link for mattermost.example.ru)"
      }
    },
    "telegram": {
      "enabled": true,
      "chat_id": 12345,
      "key": {
        "system": "system in keys (creds link for telegram token)",
        "account": "account in keys (creds link for telegram token)"
      }
    }
  }
}
```
#### Mattermost
Для оповещений в Mattermost необходимо создать бота с правами на создание чатов с пользователями и добавить API-ключ бота в разделе Keys.

#### Telegram
Для оповещения в телеграме необходимо сначала создать Телеграм-бота с помощью [@BotFather](https://t.me/BotFather), затем добавить API-ключ бота в разделе Keys. Чтобы получить уникальный chat_id пользователя, необходимо, чтобы пользователь написал боту, после этого можно получить chat_id, например, следующим способом:
```python
import requests
bot_token = ""
url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
print(requests.get(url).json())
```
# Keys
Учётные данные и API-ключи к другим системам для получения данных и оповещений хранятся в БД Universal Harvester в зашифровнанном на master_key виде. Хранение происходит по типу keyring, доступ к ключу всегда осуществляется по двум идентификаторам: система и аккаунт. Доступ к расшифрованным ключам осуществляется в следующих случаях:
1. Когда модуль engine валидирует и подготавливает source к работе.
2. Когда модуль engine осуществляет нотификацию.
3. Когда происходит вход через Keycloak.

# Sources
Для работы Universal Harvester требуется определить внешние источники данных, помимо стандартных sqlite3_in_memory и pandas_in_memory. Чтобы определить новый источник данных, нужно создать его через интерфейс Universal Harveter или добавить его напрямую в БД. Список необходимых полей для каждого источника описаны в файле app/engine/engine.py -> ENGINE_SOURCES_AND_FUNCTIONS_MAP.

Sourcename -- уникальное имя источника данных в экземпляре Universal Harvester.
## Elastic
Type -- elastic.

JSON
```python
{
  "description":"", # <- описание источника данных (необязательный параметр)
  "type":"elastic", # <- дублирование тип данных
  "host":"https://elastic.ru", # <- адрес источника
	"auth_type":"api_key", # <- тип аутентификации, это может быть http_auth или api_key
	"port":9200, # <- порт подключения к elastic
	"request_timeout":300, # <- таймаут запроса к эластику
	"max_retries":10, # <- количество переподключений
	"verify_certs":False, # <- необходимость валидации SSL сертификата
	"retry_on_timeout":True, # <- необходимость переподключения по таймауту
	"ssl_show_warn":False, # <- отображение ошибок валидации SSL сертификата
	"max_threads": 10, # <- максимальное количество параллельно выполняемых с данным источником задач
  "key":{ # <- ссылка на учётные данные в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## Elastic proxypass (kibana)
Type -- elastic_requests.

JSON
```python
{
  "type":"elastic_requests",
  "max_threads":10,
  "verify_certs":false,
  "request_timeout":300,
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```
Адрес подключения указывается в конкретном шаге в разделе Steps.

## Opensearch
Type -- opensearch.

JSON
```python
{
  "type":"opensearch", # <- дублирование тип данных
  "host":"opensearch.example.ru", # <- адрес хоста opensearch
  "port":9200, # <- порт подключения
  "auth_type":"http_auth", # <- доступен только http_auth
  "max_threads":10 # <- максимальное количество параллельно выполняемых с данным источником задач
  "http_compress":True,
  "use_ssl":True,
  "verify_certs":False,
  "ssl_assert_hostname":False,
  "ssl_show_warn":False,
  "timeout":300, 
  "max_retries":2 
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## Netbox
Type -- netbox.

JSON
```python
{
  "type":"netbox", # <- дублирование тип данных
  "url":"https://netbox.example.ru/", # <- netbox
  "host":"netbox.example.ru", # <- netbox
  "port":443, # <- порт подключения
  "max_threads":10, # <- максимальное количество параллельно выполняемых с данным источником задач
  "use_ssl":True,
  "timeout":120
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## SQLite3 in memory
Стандартный встроенный источник данных, на нём выполняются все основные задачи по подготовке, обработке и обогащению данных. С помощью значения max_threads можно регулировать потребление ОЗУ на хосте Universal Harvester.

Type -- sqlite3_in_memory.

JSON
```python
{
    "type":"sqlite3_in_memory",
    "max_threads":999
}
```

## duckdb
Стандартный встроенный источник данных, на нём выполняются все основные задачи по подготовке, обработке и обогащению данных. С помощью значения max_threads можно регулировать потребление ОЗУ на хосте Universal Harvester.

Type -- duckdb.

JSON
```python
{
    "type":"duckdb",
    "max_threads":999
}
```

## PostgreSQL
Type -- postgresql.

JSON
```python
{
  "type":"postgresql",
  "host":"postgresql.example.ru",
  "port":5432,
  "database":"db",
  "auth_type":"login/pass", # <- login/pass единственный доступный вариант
  "max_threads":10,
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## MSSQL
Type -- mssql.

JSON
```python
{
  "type":"mssql",
  "host":"mssql.example.ru",
  "port":1433,
  "database":"db",
  "auth_type":"login/pass", # <- login/pass единственный доступный вариант
  "max_threads":10,
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## DNS
Type -- dns.

JSON
```python
{
  "type":"dns",
  #"host":"dns.example.ru",
  "max_threads":10
}
```

## GitLab
Type -- gitlab.

JSON
```python
{
  "type":"gitlab",
  "url":"https://gitlab.example.ru",
  "timeout": 60,
  "max_threads":10,
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## Iris IRP
Type -- irp_iris.

JSON
```python
{
  "type":"irp_iris",
  "url":"https://iris.example.ru",
  "timeout": 60,
  "max_threads":10,
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## Teleport
Для корректной работы Teleport необходимо на этапе сборки контейнера добавить дистрибутив нужной версии для установки клиента в контейнер. Реализован вход с помощью дополнительно фактора TOTP.

Type -- teleport.

JSON
```python
{
  "type":"teleport",
  "host":"teleport.example.ru",
  "max_threads":1,
  "key":[{"system":"teleport", "account":"foo.bar"},{"system":"teleport", "account":"foo.bar_TOTP"}]
}
```

## YouTrack
Type -- youtrack.

JSON
```python
{
  "type":"youtrack",
  "url":"https://youtrack.example.ru",
  "timeout": 60,
  "max_threads":1,
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## Grafana
Type -- grafana.

JSON
```python
{
  "type":"grafana",
  "url":"https://grafana.example.ru",
  "max_threads":1,
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## Pandas in memory
Стандартный встроенный источник данных, на нём выполнется сложное агрегирование данных. С помощью значения max_threads можно регулировать потребление ОЗУ на хосте Universal Harvester.

Type -- pandas.

JSON
```python
{
    "type":"pandas",
    "max_threads":999
}
```

## Ollama
Type -- ollama.

JSON
```python
{
  "type":"ollama",
  "max_threads":1,
  "verify_certs":False,
  "request_timeout":300
  "key":{ # <- ссылка на креды в разделе keys
        "system":"system in keys table",
        "account":"account in keys table"
    }
}
```

## Manticoresearch
Type -- manticoresearch.

JSON
```python
{
  "type":"manticoresearch",
  "url":"https://manticore.example.ru/sql?mode=raw",
  "timeout":60,
  "verify":False,
  "max_threads":2
}
```

Адрес подключения указывается в конкретном шаге в разделе Steps.

# Steps
Шаги являются основным контентом Universal Harvester, который требует точного соотвествия информационному ландшафту, а значит и рефакторинга при его изменении. Шаги отвечаю за получение или обработку данных на функции выбранного источника (source) по заранее определённым или генерируемым параметрам. Результатом каждого шага является [] (list), который при наличии данных содержит "строки" данных (dict). Очевидно, что редактирование шага повлечёт за собой изменения во всех сценариях, где этот шаг используется.

Для написания шага нам потребуется:
1. Корректный источник данных (с ключами при необходимости).
2. Определить исполняемую функцию источника (определены в app/engine/engine.py ENGINE_SOURCES_AND_FUNCTIONS_MAP).
3. Определить параметры, включая генерацию параметров или применение в качестве параметров других данных (apply).
4. Определить блок query (основной блок данных запроса).
5. Определить тестовые значения параметров для валидации написанного шага.

## step fields
```python
{
    "description": "", # описание шага
    "example": "", # пример получения данных, например, сохранённый запрос в elastic
    "llm": # блок, описывающий данные для LLM (если предполагается обработка данных с помощью LLM)
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "generic_query", # идентификатор функции источника
    "input_parameters": # входные параметры, определённые шага
    {
        "...":"..."
    },
    "query": # данные, которыми оперирует функция-исполнитель шага, сюда возможно инъектирование параметров
    {
        "...": "..."
    },
    "apply": # опциональный блок применение уже полученных данных
    {
        "...":{}
    },
    "generate_parameters": # опциональный блок генерации параметров
    {
        "...":{}
    }
}
```

## Parameters (step)
Входные параметры шага определяются в ноде input_parameters шага. Возможные типы данных параметров, обязательные поля и варианты автозаполнения определены в app/engine/steps.py TYPE_MAP.
type -- тип данных параметра
description -- описание параметра
required -- флаг обязательности параметра (если false, то при его отсутствии он будет сгенерирован автоматически по полю default)
default -- значение параметра по умолчанию (или функция автозаполнения)
max_length -- только для string, максимальная длина строки
format -- только для datetime, формат принимаемого параметра времени



Примеры входных параметров
```json
"input_parameters": {
        "string_parameter": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "default_string",
            "description":""
        },
        "datetime_parameter": {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": true,
            "default": "now",
            "description":""
        },
        "integer_parameter": {
            "type": "integer",
            "required": true,
            "default": 0,
            "description":""
        },
        "ip_address_parameter": {
            "type": "ip_address",
            "required": false,
            "default": "127.0.0.1",
            "description":""
        },
        "float_parameter": {
            "type": "float",
            "required": false,
            "default": 0.0,
            "description":""
        },
        "boolean_parameter": {
            "type": "boolean",
            "required": false,
            "default": true,
            "description":""
        }
    }
```

Генерация параметров применяется для создания новых параметров из имеющихся. Определены 3 функции генерации: -timedelta, +timedelta, copy.
Имя ноды определяет имя сгенерированного параметра.
type -- тип генерации нового параметра
timestamp_field -- имя параметра времени для типов -timedelta и +timedelta, от которого будет определяться смещение
delta_field -- имя параметра (integer) для смещения в секундах
output_format -- формат времени сгенерированного параметра
copy_source -- существующий параметр для копирования, тип данных наследуется

Примеры генерации параметров:
```json
"generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "copied":
        {
            "type":"copy",
            "copy_source":"other_parameter"
        }
    }
```

Применение данных в качестве параметров (apply)
Universal Harvester имеет возможность применять данные, полученные в одних запрос, для подготовки других запросов. Для этого применятся нода шага apply. Имеется возможность использования результатов только одного уже выполненного шага. Применение apply определяет зависимость выполняемого шага от другого и влияет на очерёдность выполнения шагов в рамках сценария.

target_data -- уникальный идентификатор данных в рамках сценария или опредеяемый в специальном параметре __outervision__
target_parameters -- список генерируемых параметров по столбцам данных target_data
output_unique_fields -- (опционально) удаление дубликатов по указанным полям

Для каждого параметра необходимо указать:
column_name -- имя колонки в применяемых данных
as -- имя нового параметра в шаге

Опционально:
format -- формат вывода, если это datetime
pattern -- применение дополнительного паттерна инъектирования параметра

```json
"apply":{
    	"target_data":"target_data_name",
    	"target_parameters":[
    		{
    			"column_name":"column_in_target_data_1",
    			"as":"parameter_name_1"
    		},
        {
    			"column_name":"column_in_target_data_2_datetime",
    			"as":"parameter_name_2",
          "format":"%Y-%m-%dT%H:%M:%S.%f%z"
    		},
        {
    			"column_name":"timestamp_stop",
    			"as":"timestamp_stop",
          "pattern":"='%(__pattern_value__)s'"
    		}
    	],
        "output_unique_fields":["field_1", "field_2"]
    }
```

Инъектирование параметров производится для блоков шага query и apply. Это значит, что указав в тексте блок %(parameter)[sifbldx], параметр parameter будет инъектирован в шаг по правилам типа инъекции [sifbldx].

s -- вместо блока %(parameter)s подставляется str(value) ("data":"text %(parameter)s text" -> "data":"text value text" при value = "value")

i -- вместо блока %(parameter)i подставляется int(value), если инъекция обрамляется ", то они будут опущены ("data":"%(parameter)i" -> "data":0 при value = 0)

f -- вместо блока %(parameter)f подставляется float(value), если инъекция обрамляется ", то они будут опущены ("data":"%(parameter)f" -> "data":0.0 при value = 0.0)

b -- вместо блока %(parameter)b подставляется bool(value), если инъекция обрамляется ", то они будут опущены ("data":"%(parameter)b" -> "data":true при value = true)

l -- вместо блока %(parameter)l подставляется json.dumps(value), если инъекция обрамляется ", то они будут опущены ("data":"%(parameter)l" -> "data":[] при value = [])

d -- вместо блока %(parameter)d подставляется json.dumps(value), если инъекция обрамляется ", то они будут опущены ("data":"%(parameter)d" -> "data":{} при value = {})

x -- вместо блока %(parameter)x подставляется str(value), если инъекция обрамляется ", то они будут опущены ("data":"%(parameter)x" -> "data":value_ при value = "value_")

Обязательно убедитесь в том, что после инъектирования у вас получится корректный JSON.

| Injection string | Type         | Test value    | Original string                   | Result                                | Comment                                          |
|------------------|--------------|---------------|-----------------------------------|---------------------------------------|--------------------------------------------------|
| %(parameter)s    | string       | test          | "data":"query data %(parameter)s" | "data":"query data test"              |                                                  |
| %(parameter)i    | integer      | 12            | "data":"query data %(parameter)i" | "data":"query data 12"                |                                                  |
|                  |              |               | "data":"%(parameter)i"            | "data":12                             |                                                  |
| %(parameter)f    | float        | 12.34         | "data":"query data %(parameter)f" | "data":"query data 12.340000000"      | "{0:0.9f}".format(value)                         |
|                  |              |               | "data":"%(parameter)f"            | "data":12.340000000                   |                                                  |
| %(parameter)b    | boolean      | true          | "data":"query data %(parameter)b" | "data":"query data true"              |                                                  |
|                  |              |               | "data":"%(parameter)b"            | "data":true                           |                                                  |
| %(parameter)l    | list         | ["test"]      | "data":"query data %(parameter)l" | "data":"query data [\"test\"]"        |                                                  |
|                  |              |               | "data":"%(parameter)l"            | "data":["test"]                       |                                                  |
| %(parameter)d    | dict         | {"foo":"bar"} | "data":"query data %(parameter)d" | "data":"query data {\"foo\":\"bar\"}" |                                                  |
|                  |              |               | "data":"%(parameter)d"            | "data":{"foo":"bar"}                  |                                                  |
| %(parameter)x    | e__x__tended | "[\"test\"]"  | "data":"query data %(parameter)x" | "data":"query data [\"test\"]"        |                                                  |
|                  |              |               | "data":"%(parameter)x"            | "data":["test"]                       | Прямое инъектирование, JSON должен быть валидным |

## Elastic step functions
### generic_query
Получение данных из elastic, ровно тех, которые вы можете получить с помощью интерфейса Discover в Kibana. Получение не ограничено по объёму данных и количеству записей.

```json
{
    "description": "Поиск по логу DNS",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "generic_query",
    "input_parameters":
    {
        "timestamp_start":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": true,
            "default": "now",
            "description": "Опорное время поиска (start)."
        },
        "timestamp_stop":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": true,
            "default": "now",
            "description": "Опорное время поиска (stop)."
        },
        "search_value":
        {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description": "То, что мы ищем, мультипоиск по всем полям, возможен wildcard."
        }
    },
    "query":
    {
        "index": "index-*",
        "size": 1000,
        "search_after_shift": -10,
        "sort":
        [
            {
                "@timestamp":
                {
                    "order": "desc",
                    "unmapped_type": "boolean"
                }
            }
        ],
        "fields":
        [
            {
                "field": "srcip",
                "include_unmapped": "true"
            },
            {
                "field": "srcport",
                "include_unmapped": "true"
            },
            {
                "field": "domain_name",
                "include_unmapped": "true"
            },
            {
                "field": "@timestamp",
                "format": "strict_date_optional_time"
            }
        ],
        "query":
        {
            "bool":
            {
                "must":
                [],
                "filter":
                [
                    {
                        "bool":
                        {
                            "should":
                            [
                                {
                                    "match_phrase":
                                    {
                                        "domain_name": "%(search_value)s"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    {
                        "range":
                        {
                            "@timestamp":
                            {
                                "format": "strict_date_optional_time",
                                "gte": "%(timestamp_start)s",
                                "lte": "%(timestamp_stop)s"
                            }
                        }
                    }
                ],
                "should":
                [],
                "must_not":
                []
            }
        }
    },
    "generate_parameters":
    {
        "lte":
        {
            "type": "copy",
            "copy_source": "timestamp_stop"
        }
    }
}
```
### aggs_query
Получение данных из elastic, как в интерфейсе aggregation table.

```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "aggs_query",
    "input_parameters":
    {
        "timestamp_field":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "@timestamp",
            "description": "Наиболее релевантное поле времени"
        },
        "timestamp":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": false,
            "default": "now",
            "description": "Опорное время поиска, от него берутся дельты в секундах."
        },
        "time_delta":
        {
            "type": "integer",
            "required": false,
            "default": 172800,
            "description": "Дельта времени в секундах."
        },
        "target_search_field":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "value",
            "description": "Поле в применяемых данных с целью поиска"
        },
        "target_data":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "unique_values",
            "description": "Имя применяемых данных"
        }
    },
    "query":
    {
        "index": "foobar-events",
        "size": 0,
        "aggs":
        {
            "2":
            {
                "terms":
                {
                    "field": "address",
                    "order":
                    {
                        "_count": "desc"
                    },
                    "missing": "__missing__",
                    "size": 500
                },
                "aggs":
                {
                    "3":
                    {
                        "terms":
                        {
                            "field": "hid",
                            "order":
                            {
                                "_count": "desc"
                            },
                            "missing": "__missing__",
                            "size": 50000
                        },
                        "aggs":
                        {
                            "4":
                            {
                                "terms":
                                {
                                    "field": "hostname",
                                    "order":
                                    {
                                        "_count": "desc"
                                    },
                                    "missing": "__missing__",
                                    "size": 50000
                                },
                                "aggs":
                                {
                                    "5":
                                    {
                                        "min":
                                        {
                                            "field": "%(timestamp_field)s"
                                        }
                                    },
                                    "6":
                                    {
                                        "max":
                                        {
                                            "field": "%(timestamp_field)s"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "query":
        {
            "bool":
            {
                "must":
                [],
                "filter":
                [
                    {
                        "multi_match":
                        {
                            "type": "phrase",
                            "query": "%(search_value)s",
                            "lenient": true
                        }
                    },
                    {
                        "match_phrase":
                        {
                            "logger": "foobar"
                        }
                    },
                    {
                        "range":
                        {
                            "%(timestamp_field)s":
                            {
                                "format": "strict_date_optional_time",
                                "gte": "%(gte)s",
                                "lte": "%(lte)s"
                            }
                        }
                    }
                ],
                "should":
                [],
                "must_not":
                []
            }
        }
    },
    "apply":
    {
        "target_data": "%(target_data)s",
        "target_parameters":
        [
            {
                "column_name": "%(target_search_field)s",
                "as": "search_value"
            }
        ]
    },
    "generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "time_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "time_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        }
    }
}
```
### pid_hierarchy
Последовательность запросов по восстановлению иерархии pid->parent_pid.

```json
{
    "description": "Построение дерева процессов по указанному процессу",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function":"pid_hierarchy",
    "input_parameters": {
        "timestamp_field": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "process.start",
            "description":"Актуальное поле времени запуска процесса"
        },
        "timestamp": {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S%z",
            "required": true,
            "default": "now",
            "description":"Время запуска целевого процесса"
        },
        "host_search_field": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "hid",
            "description":"По какому полю идентифицируем хост"
        },
        "host_search_field_value": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "Please fill a hid",
            "description":"Идентификатор хоста"
        },
        "process_pid": {
            "type": "integer",
            "required": true,
            "default": 0,
            "description":"Process ID, по которому хотим узнать иерархию"
        },
        "parent_deep": {
            "type": "integer",
            "required": false,
            "default": 16,
            "description":"Глубина поиска родителей"
        },
        "parent_delta": {
            "type": "integer",
            "required": false,
            "default": 86000,
            "description":"Глубина поиска родителей в секундах"
        },
        "child_deep": {
            "type": "integer",
            "required": false,
            "default": 8,
            "description":"Глубина поиска детей"
        },
        "child_delta": {
            "type": "integer",
            "required": false,
            "default": 2600,
            "description":"Глубина поиска детей в секундах"
        },
        "index": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "audit-*",
            "description":"В каком индексе ищем."
        }
    },
    "query":
    {
        "index": "%(index)s",
        "size": 1000,
        "search_after_shift": -10,
        "sort": [{"%(timestamp_field)s": {"order": "desc","unmapped_type": "boolean"}}],
        "fields": [{"field": "*","include_unmapped": "true"}],
        "query":{"bool":{"must":[],"filter":[{"range":{"%(timestamp_field)s":{"format":"strict_date_optional_time","gte":"%(timestamp)s","lte":"%(timestamp)s"}}},{"match_phrase":{"%(host_search_field)s":"%(host_search_field_value)s"}},{"match_phrase":{"pid":"%(process_pid)i"}}],"should":[],"must_not":[]}}
    },
    "generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "parent_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "child_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        }
    }
}
```

### pid_siblings
Получение сиблингов процесса (список процессов того же родителя, что и у целевого процесса).

```json
{
    "description": "Поиск сиблингов (процессов с аналогичным parent pid)",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function":"pid_siblings",
    "input_parameters": {
        "timestamp_field": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "process.start",
            "description":"Актуальное поле времени запуска процесса"
        },
        "timestamp": {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S%z",
            "required": true,
            "default": "now",
            "description":"Время запуска целевого процесса"
        },
        "host_search_field": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "hid",
            "description":"По какому полю идентифицируем хост"
        },
        "host_search_field_value": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "Please fill a hid",
            "description":"Идентификатор хоста"
        },
        "process_pid": {
            "type": "integer",
            "required": true,
            "default": 0,
            "description":"Process ID, по которому хотим узнать"
        },
        "parent_delta": {
            "type": "integer",
            "required": false,
            "default": 86000,
            "description":"Глубина поиска родителей в секундах"
        },
        "child_delta": {
            "type": "integer",
            "required": false,
            "default": 2600,
            "description":"Глубина поиска детей в секундах"
        },
        "index": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "audit-*",
            "description":"В каком индексе elastic ищем"
        }
    },
    "query":
    {
        "index": "%(index)s",
        "size": 1000,
        "search_after_shift": -10,
        "sort": [{"%(timestamp_field)s": {"order": "desc","unmapped_type": "boolean"}}],
        "fields": [{"field": "*","include_unmapped": "true"}],
        "query":{"bool":{"must":[],"filter":[{"range":{"%(timestamp_field)s":{"format":"strict_date_optional_time","gte":"%(timestamp)s","lte":"%(timestamp)s"}}},{"match_phrase":{"%(host_search_field)s":"%(host_search_field_value)s"}},{"match_phrase":{"pid":"%(process_pid)i"}}],"should":[],"must_not":[]}}
    },
    "generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "parent_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "child_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        }
    }
}
```


## Elastic proxypass (kibana) step functions
### generic_query
Получение данных из elastic, ровно тех, которые вы можете получить с помощью интерфейса Discover в Kibana. Получение не ограничено по объёму данных и количеству записей.

```json
{
    "description": "Поиск по логу DNS",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "generic_query",
    "input_parameters":
    {
        "timestamp_start":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": true,
            "default": "now",
            "description": "Опорное время поиска (start)."
        },
        "timestamp_stop":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": true,
            "default": "now",
            "description": "Опорное время поиска (stop)."
        },
        "search_value":
        {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description": "То, что мы ищем, мультипоиск по всем полям, возможен wildcard."
        },
        "index": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "%(index)s",
            "description":"В каком индексе ищем."
        }
    },
    "query":
    {
        "url": "https://kibana.example.ru/api/console/proxy?path=/%(index)s/_search?batched_reduce_size=64&method=POST",
        "size": 1000,
        "search_after_shift": -10,
        "sort":
        [
            {
                "@timestamp":
                {
                    "order": "desc",
                    "unmapped_type": "boolean"
                }
            }
        ],
        "fields":
        [
            {
                "field": "srcip",
                "include_unmapped": "true"
            },
            {
                "field": "srcport",
                "include_unmapped": "true"
            },
            {
                "field": "domain_name",
                "include_unmapped": "true"
            },
            {
                "field": "@timestamp",
                "format": "strict_date_optional_time"
            }
        ],
        "query":
        {
            "bool":
            {
                "must":
                [],
                "filter":
                [
                    {
                        "bool":
                        {
                            "should":
                            [
                                {
                                    "match_phrase":
                                    {
                                        "domain_name": "%(search_value)s"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    {
                        "range":
                        {
                            "@timestamp":
                            {
                                "format": "strict_date_optional_time",
                                "gte": "%(timestamp_start)s",
                                "lte": "%(timestamp_stop)s"
                            }
                        }
                    }
                ],
                "should":
                [],
                "must_not":
                []
            }
        }
    },
    "generate_parameters":
    {
        "lte":
        {
            "type": "copy",
            "copy_source": "timestamp_stop"
        }
    }
}
```

### aggs_query
Получение данных из elastic, как в интерфейсе aggregation table.

```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "aggs_query",
    "input_parameters":
    {
        "timestamp_field":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "@timestamp",
            "description": "Наиболее релевантное поле времени"
        },
        "timestamp":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": false,
            "default": "now",
            "description": "Опорное время поиска, от него берутся дельты в секундах."
        },
        "time_delta":
        {
            "type": "integer",
            "required": false,
            "default": 172800,
            "description": "Дельта времени в секундах."
        },
        "target_search_field":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "value",
            "description": "Поле в применяемых данных с целью поиска"
        },
        "target_data":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "unique_values",
            "description": "Имя применяемых данных"
        },
        "index": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "%(index)s",
            "description":"В каком индексе ищем."
        }
    },
    "query":
    {
        "url": "https://kibana.example.ru/api/console/proxy?path=/%(index)s/_search?batched_reduce_size=64&method=POST",
        "size": 0,
        "aggs":
        {
            "2":
            {
                "terms":
                {
                    "field": "address",
                    "order":
                    {
                        "_count": "desc"
                    },
                    "missing": "__missing__",
                    "size": 500
                },
                "aggs":
                {
                    "3":
                    {
                        "terms":
                        {
                            "field": "hid",
                            "order":
                            {
                                "_count": "desc"
                            },
                            "missing": "__missing__",
                            "size": 50000
                        },
                        "aggs":
                        {
                            "4":
                            {
                                "terms":
                                {
                                    "field": "hostname",
                                    "order":
                                    {
                                        "_count": "desc"
                                    },
                                    "missing": "__missing__",
                                    "size": 50000
                                },
                                "aggs":
                                {
                                    "5":
                                    {
                                        "min":
                                        {
                                            "field": "%(timestamp_field)s"
                                        }
                                    },
                                    "6":
                                    {
                                        "max":
                                        {
                                            "field": "%(timestamp_field)s"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "query":
        {
            "bool":
            {
                "must":
                [],
                "filter":
                [
                    {
                        "multi_match":
                        {
                            "type": "phrase",
                            "query": "%(search_value)s",
                            "lenient": true
                        }
                    },
                    {
                        "match_phrase":
                        {
                            "logger": "foobar"
                        }
                    },
                    {
                        "range":
                        {
                            "%(timestamp_field)s":
                            {
                                "format": "strict_date_optional_time",
                                "gte": "%(gte)s",
                                "lte": "%(lte)s"
                            }
                        }
                    }
                ],
                "should":
                [],
                "must_not":
                []
            }
        }
    },
    "apply":
    {
        "target_data": "%(target_data)s",
        "target_parameters":
        [
            {
                "column_name": "%(target_search_field)s",
                "as": "search_value"
            }
        ]
    },
    "generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "time_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "time_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        }
    }
}
```

### pid_hierarchy
Последовательность запросов по восстановлению иерархии pid->parent_pid.

```json
{
    "description": "Построение дерева процессов по указанному процессу",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function":"pid_hierarchy",
    "input_parameters": {
        "timestamp_field": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "process.start",
            "description":"Актуальное поле времени запуска процесса"
        },
        "timestamp": {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S%z",
            "required": true,
            "default": "now",
            "description":"Время запуска целевого процесса"
        },
        "host_search_field": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "hid",
            "description":"По какому полю идентифицируем хост"
        },
        "host_search_field_value": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "Please fill a hid",
            "description":"Идентификатор хоста"
        },
        "process_pid": {
            "type": "integer",
            "required": true,
            "default": 0,
            "description":"Process ID, по которому хотим узнать иерархию"
        },
        "parent_deep": {
            "type": "integer",
            "required": false,
            "default": 16,
            "description":"Глубина поиска родителей"
        },
        "parent_delta": {
            "type": "integer",
            "required": false,
            "default": 86000,
            "description":"Глубина поиска родителей в секундах"
        },
        "child_deep": {
            "type": "integer",
            "required": false,
            "default": 8,
            "description":"Глубина поиска детей"
        },
        "child_delta": {
            "type": "integer",
            "required": false,
            "default": 2600,
            "description":"Глубина поиска детей в секундах"
        },
        "index": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "audit-*",
            "description":"В каком индексе ищем."
        }
    },
    "query":
    {
        "index": "%(index)s",
        "url": "https://kibana.example.ru/api/console/proxy?path=/%(index)s/_search?batched_reduce_size=64&method=POST",
        "size": 1000,
        "search_after_shift": -10,
        "sort": [{"%(timestamp_field)s": {"order": "desc","unmapped_type": "boolean"}}],
        "fields": [{"field": "*","include_unmapped": "true"}],
        "query":{"bool":{"must":[],"filter":[{"range":{"%(timestamp_field)s":{"format":"strict_date_optional_time","gte":"%(timestamp)s","lte":"%(timestamp)s"}}},{"match_phrase":{"%(host_search_field)s":"%(host_search_field_value)s"}},{"match_phrase":{"pid":"%(process_pid)i"}}],"should":[],"must_not":[]}}
    },
    "generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "parent_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "child_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        }
    }
}
```
### pid_siblings
Получение сиблингов процесса (список процессов того же родителя, что и у целевого процесса).

```json
{
    "description": "Поиск сиблингов (процессов с аналогичным parent pid)",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function":"pid_siblings",
    "input_parameters": {
        "timestamp_field": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "process.start",
            "description":"Актуальное поле времени запуска процесса"
        },
        "timestamp": {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S%z",
            "required": true,
            "default": "now",
            "description":"Время запуска целевого процесса"
        },
        "host_search_field": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "hid",
            "description":"По какому полю идентифицируем хост"
        },
        "host_search_field_value": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "Please fill a hid",
            "description":"Идентификатор хоста"
        },
        "process_pid": {
            "type": "integer",
            "required": true,
            "default": 0,
            "description":"Process ID, по которому хотим узнать"
        },
        "parent_delta": {
            "type": "integer",
            "required": false,
            "default": 86000,
            "description":"Глубина поиска родителей в секундах"
        },
        "child_delta": {
            "type": "integer",
            "required": false,
            "default": 2600,
            "description":"Глубина поиска детей в секундах"
        },
        "index": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "audit-*",
            "description":"В каком индексе elastic ищем"
        }
    },
    "query":
    {
        "index": "%(index)s",
        "url": "https://kibana.example.ru/api/console/proxy?path=/%(index)s/_search?batched_reduce_size=64&method=POST",
        "size": 1000,
        "search_after_shift": -10,
        "sort": [{"%(timestamp_field)s": {"order": "desc","unmapped_type": "boolean"}}],
        "fields": [{"field": "*","include_unmapped": "true"}],
        "query":{"bool":{"must":[],"filter":[{"range":{"%(timestamp_field)s":{"format":"strict_date_optional_time","gte":"%(timestamp)s","lte":"%(timestamp)s"}}},{"match_phrase":{"%(host_search_field)s":"%(host_search_field_value)s"}},{"match_phrase":{"pid":"%(process_pid)i"}}],"should":[],"must_not":[]}}
    },
    "generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "parent_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "child_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        }
    }
}
```

## Opensearch step functions
### generic_query
Получение данных из opensearch, ровно тех, которые вы можете получить с помощью интерфейса Discover в Kibana. Получение не ограничено по объёму данных и количеству записей.

```json
{
    "description": "Поиск по логу DNS",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "generic_query",
    "input_parameters":
    {
        "timestamp_start":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": true,
            "default": "now",
            "description": "Опорное время поиска (start)."
        },
        "timestamp_stop":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": true,
            "default": "now",
            "description": "Опорное время поиска (stop)."
        },
        "search_value":
        {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description": "То, что мы ищем, мультипоиск по всем полям, возможен wildcard."
        }
    },
    "query":
    {
        "index": "index-*",
        "size": 1000,
        "search_after_shift": -10,
        "sort":
        [
            {
                "@timestamp":
                {
                    "order": "desc",
                    "unmapped_type": "boolean"
                }
            }
        ],
        "fields":
        [
            {
                "field": "srcip",
                "include_unmapped": "true"
            },
            {
                "field": "srcport",
                "include_unmapped": "true"
            },
            {
                "field": "domain_name",
                "include_unmapped": "true"
            },
            {
                "field": "@timestamp",
                "format": "strict_date_optional_time"
            }
        ],
        "query":
        {
            "bool":
            {
                "must":
                [],
                "filter":
                [
                    {
                        "bool":
                        {
                            "should":
                            [
                                {
                                    "match_phrase":
                                    {
                                        "domain_name": "%(search_value)s"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    {
                        "range":
                        {
                            "@timestamp":
                            {
                                "format": "strict_date_optional_time",
                                "gte": "%(timestamp_start)s",
                                "lte": "%(timestamp_stop)s"
                            }
                        }
                    }
                ],
                "should":
                [],
                "must_not":
                []
            }
        }
    },
    "generate_parameters":
    {
        "lte":
        {
            "type": "copy",
            "copy_source": "timestamp_stop"
        }
    }
}
```
### aggs_query
Получение данных из opensearch, как в интерфейсе aggregation table.

```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "aggs_query",
    "input_parameters":
    {
        "timestamp_field":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "@timestamp",
            "description": "Наиболее релевантное поле времени"
        },
        "timestamp":
        {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": false,
            "default": "now",
            "description": "Опорное время поиска, от него берутся дельты в секундах."
        },
        "time_delta":
        {
            "type": "integer",
            "required": false,
            "default": 172800,
            "description": "Дельта времени в секундах."
        },
        "target_search_field":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "value",
            "description": "Поле в применяемых данных с целью поиска"
        },
        "target_data":
        {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "unique_values",
            "description": "Имя применяемых данных"
        }
    },
    "query":
    {
        "index": "foobar-events",
        "size": 0,
        "aggs":
        {
            "2":
            {
                "terms":
                {
                    "field": "address",
                    "order":
                    {
                        "_count": "desc"
                    },
                    "missing": "__missing__",
                    "size": 500
                },
                "aggs":
                {
                    "3":
                    {
                        "terms":
                        {
                            "field": "hid",
                            "order":
                            {
                                "_count": "desc"
                            },
                            "missing": "__missing__",
                            "size": 50000
                        },
                        "aggs":
                        {
                            "4":
                            {
                                "terms":
                                {
                                    "field": "hostname",
                                    "order":
                                    {
                                        "_count": "desc"
                                    },
                                    "missing": "__missing__",
                                    "size": 50000
                                },
                                "aggs":
                                {
                                    "5":
                                    {
                                        "min":
                                        {
                                            "field": "%(timestamp_field)s"
                                        }
                                    },
                                    "6":
                                    {
                                        "max":
                                        {
                                            "field": "%(timestamp_field)s"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "query":
        {
            "bool":
            {
                "must":
                [],
                "filter":
                [
                    {
                        "multi_match":
                        {
                            "type": "phrase",
                            "query": "%(search_value)s",
                            "lenient": true
                        }
                    },
                    {
                        "match_phrase":
                        {
                            "logger": "foobar"
                        }
                    },
                    {
                        "range":
                        {
                            "%(timestamp_field)s":
                            {
                                "format": "strict_date_optional_time",
                                "gte": "%(gte)s",
                                "lte": "%(lte)s"
                            }
                        }
                    }
                ],
                "should":
                [],
                "must_not":
                []
            }
        }
    },
    "apply":
    {
        "target_data": "%(target_data)s",
        "target_parameters":
        [
            {
                "column_name": "%(target_search_field)s",
                "as": "search_value"
            }
        ]
    },
    "generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "time_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "time_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        }
    }
}
```

## Netbox step functions
### finder
Поиск данных по конкретному IP-адресу.

```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "finder",
    "input_parameters":
    {
    	"target": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description":"Что ищем в netbox, попадает в api параметр /api/ipam/ip-addresses/?q="
        },
        "fast_flag": {
            "type": "boolean",
            "required": false,
            "default": true,
            "description":"Флаг пропуска дополнительных поисков в /api/ipam/prefixes/?q= и /api/tenancy/contact-assignments/?object_id="
        }
    },
    "query":{},
    "generate_parameters":
    {}
}
```
### search_cidr_by_ip
Поиск ближайшего к запрашиваемому адресу cidr.

```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "search_cidr_by_ip",
    "input_parameters":
    {
    	"target": {
            "type": "ip_address",
            "required": true,
            "description":"По какому адресу ищем узел или ближайшую сеть"
        }
    },
    "query":{
        "search_parameter":"target"
    },
    "generate_parameters":
    {}
}
```

## SQLite3 in memory step functions
### query
Основная функция преобразования и объединения данных (фильтрация, перестановка столбцов, переименование, JOIN, UNION, DISTINCT, GROUP BY и т.д., доступны все возможности sqlite3 + дополнительные функции). Таблицы соответствуют data_name в сценарии или __outervision__ в отладочном запуске шага. Важно: обращение к data_name ведёт к ожиданию выполнения шага с этим data_name, от этого зависит последовательность выполнения шагов.

```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "query",
    "input_parameters":{
	    "subject":{
            "type": "string",
            "max_length": 100,
            "required": false,
            "default":"subject",
            "description": ""
        }
    },
    "query":
    {
        "preparatory_queries":
        [
            "CREATE TABLE IF NOT EXISTS events (`foobar_1` TEXT, `foobar_2` TEXT, `foobar_3` TEXT, `foobar_histogram` TEXT);"
        ],
        "final_query": "SELECT '%(subject)s' as subject, unixtime_to_iso_timestamp(`foobar_histogram`/1000) as timestamp, `foobar_1` as foobar_1_name, `foobar_2` as foobar_2_name, `foobar_3` as foobar_3_name FROM events ORDER BY `foobar_histogram`;"
    },
    "generate_parameters":
    {}
}
```

#### additional sqlite3 functions
Для удобства обработки данных в sqlite3 были добавлены кастомные функции:
* regexp(pattern, string) -- найдено ли паттерн в строке;
* regexp_substr(pattern, string) -- все вхождения паттерна в строку, текстовая репрезентация листа;
* ip_is_private(ip_address) -- если ip-адрес относится к приватной сети, то возвращает 1, иначе 0;
* unixtime_to_iso_timestamp(unix_timestamp) -- преобразует unix_timestamp (миллисекунды) в iso формат;
* bytes_to_string(int_bytes) -- преобразует количество байт в pretty вид;
* ip_port2ip(ip_port) -- выделяет из конкатенации ip:port только ip;
* validate_ip_address(ip_address) -- проверяет ip-адрес на валидность;
* datetime_to_timestamp(string, format) -- преобразует текстовое время в unix_timestamp.

## duckdb in memory step functions
### query
Основная функция преобразования и объединения данных (фильтрация, перестановка столбцов, переименование, JOIN, UNION, DISTINCT, GROUP BY и т.д., доступны все возможности duckdb + дополнительные функции). Таблицы соответствуют data_name в сценарии или __outervision__ в отладочном запуске шага. Важно: обращение к data_name ведёт к ожиданию выполнения шага с этим data_name, от этого зависит последовательность выполнения шагов.
Для duckdb присутствует параметр type, который отвечает за представление данных: table или view. View работает быстрее на больших данных, но имеет определённые ограничения на модификации данных.
```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "query",
    "input_parameters":{
	    "subject":{
            "type": "string",
            "max_length": 100,
            "required": false,
            "default":"subject",
            "description": ""
        }
    },
    "query":
    {
        "preparatory_queries":
        [
            "CREATE TABLE IF NOT EXISTS events (\"foobar_1\" TEXT, \"foobar_2\" TEXT, \"foobar_3\" TEXT, \"foobar_histogram\" TEXT);"
        ],
        "final_query": "SELECT '%(subject)s' as subject, unixtime_to_iso_timestamp(\"foobar_histogram\"/1000) as timestamp, \"foobar_1\" as foobar_1_name, \"foobar_2\" as foobar_2_name, \"foobar_3\" as foobar_3_name FROM events ORDER BY \"foobar_histogram\";",
        "type":"table"
    },
    "generate_parameters":
    {}
}
```

#### additional duckdb functions
Для удобства обработки данных в sqlite3 были добавлены кастомные функции:
* regexp(pattern, string) -- найдено ли паттерн в строке;
* regexp_substr(pattern, string) -- все вхождения паттерна в строку, текстовая репрезентация листа;
* ip_is_private(ip_address) -- если ip-адрес относится к приватной сети, то возвращает 1, иначе 0;
* unixtime_to_iso_timestamp(unix_timestamp) -- преобразует unix_timestamp (миллисекунды) в iso формат;
* bytes_to_string(int_bytes) -- преобразует количество байт в pretty вид;
* ip_port2ip(ip_port) -- выделяет из конкатенации ip:port только ip;
* validate_ip_address(ip_address) -- проверяет ip-адрес на валидность;
* datetime_to_timestamp(string, format) -- преобразует текстовое время в unix_timestamp.

## PostgreSQL step functions
### query
```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "query",
    "input_parameters":{
	    "subject":{
            "type": "string",
            "max_length": 100,
            "required": false,
            "default":"subject",
            "description": ""
        }
    },
    "query":
    {
        "preparatory_queries":[],
        "final_query": "SELECT foobar_1, foobar_2, foobar_3, foobar_4 FROM foobar_table WHERE foobar_1='%(subject)s' ORDER BY foobar_2 DESC LIMIT 10;"
    },
    "generate_parameters":
    {}
}
```

## MSSQL step functions
### query
```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "query",
    "input_parameters":{
	    "subject":{
            "type": "string",
            "max_length": 100,
            "required": false,
            "default":"subject",
            "description": ""
        }
    },
    "query":
    {
        "preparatory_queries":[],
        "final_query": "SELECT foobar_1, foobar_2, foobar_3, foobar_4 FROM foobar_table WHERE foobar_1='%(subject)s' ORDER BY foobar_2 DESC LIMIT 10;"
    },
    "generate_parameters":
    {}
}
```

## MySQL step functions
### query
```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "query",
    "input_parameters":{
	    "subject":{
            "type": "string",
            "max_length": 100,
            "required": false,
            "default":"subject",
            "description": ""
        }
    },
    "query":
    {
        "preparatory_queries":[],
        "final_query": "SELECT foobar_1, foobar_2, foobar_3, foobar_4 FROM foobar_table WHERE foobar_1='%(subject)s' ORDER BY foobar_2 DESC LIMIT 10;"
    },
    "generate_parameters":
    {}
}
```

## DNS step functions
### query
```json
{
    "description": "Разыменовывание dns имени",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "query",
    "input_parameters":{
        "domain_name": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description":""
        }
    },
    "query":{},
    "generate_parameters":{}
}
```

## GitLab step functions
### get_namespace_owner
Получение owner по неймспейсу gitlab.
```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "query",
    "input_parameters":{
        "namespace": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description":""
        },
        "project_id": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "12345",
            "description":""
        }
    },
    "query":{},
    "generate_parameters":{}
}
```
### search
Стандартный поиск по gitlab.
```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "query",
    "input_parameters":{
        "target": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description":""
        },
        "scope": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "blobs",
            "description":""
        }
    },
    "query":{},
    "generate_parameters":{}
}
```

## Iris IRP step functions
### get_all_alerts
```json
{
    "description": "",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "get_all_alerts",
    "input_parameters":{
        "search_value": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description":""
        },
        "start_date": {
            "type": "datetime",
            "format": "%Y-%m-%d",
            "required": true,
            "description":""
        },
        "end_date": {
            "type": "datetime",
            "format": "%Y-%m-%d",
            "required": true,
            "description":""
        }
    },
    "query":{
      "per_page":10000,
      "search_field":"alert_assets"
    },
    "generate_parameters":{}
}
```

## Teleport step functions
### get_hosts
```json
{
    "description": "Получение информации о хостах",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "get_hosts",
    "input_parameters":{},
    "query":{
        "ttl":600
    },
    "generate_parameters":{}
}
```

## YouTrack step functions
### search_in_project
Поиск в выбранном проетке.

```json
{
    "description": "Получение данных из youtrack по карточкам (issue) в проекте",
    "example": "",
    "llm":
    {
        "preprompt": "Данные из youtrack (issue)",
        "postprompt": ""
    },
    "source_function": "search_in_project",
    "input_parameters":{
        "target": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description":"Что ищем"
        },
        "project_id": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "description":"12345"
        }
    },
    "query":{
        "fields": ["idReadable", "description", "summary", "created", "updated", "resolved"]
    },
    "generate_parameters":{}
}
```
### search_in_all_projects
Поиск по всем проектам.

```json
{
    "description": "Получение данных из youtrack по карточкам (issue)",
    "example": "",
    "llm":
    {
        "preprompt": "Данные из youtrack (issue)",
        "postprompt": ""
    },
    "source_function": "search_in_all_projects",
    "input_parameters":{
        "target": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description":"Что ищем"
        }
    },
    "query":{
        "fields": ["idReadable", "description", "summary", "created", "updated", "resolved"]
    },
    "generate_parameters":{}
}
```
### search_in_all_articles
Поиск по базе знаний.

```json
{
    "description": "Получение данных из youtrack (база знаний)",
    "example": "",
    "llm":
    {
        "preprompt": "Данные из youtrack (база знаний)",
        "postprompt": ""
    },
    "source_function": "search_in_all_articles",
    "input_parameters":{
        "target": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "description":"Что ищем"
        },
        "top": {
            "type": "integer",
            "required": false,
            "default": 100,
            "description":"Количество забираемых записей из youtrack"
        },
        "with_content_flag": {
            "type": "boolean",
            "required": false,
            "default": false,
            "description":"Флаг загрузки контента статей"
        }
    },
    "query":{
        "fields": ["idReadable", "summary", "created", "updated"],
        "fields_with_content": ["idReadable", "summary", "created", "updated", "content"]
    },
    "generate_parameters":{}
}
```

## Grafana step functions
### get_table
Позволяет получить таблицу с данными из grafana.
```json
{
    "description": "Получение данных из grafana",
    "example": "",
    "llm":
    {
        "preprompt": "Инвентаризационные данные из grafana",
        "postprompt": ""
    },
    "source_function": "get_table",
    "input_parameters":{
        "timestamp": {
            "type": "datetime",
            "format": "%Y-%m-%dT%H:%M:%S.%f%z",
            "required": false,
            "default": "now",
            "description":"Опорное время поиска, от него берутся дельты в секундах."
        },
        "time_delta": {
            "type": "integer",
            "required": false,
            "default": 1800,
            "description":"Дельта времени в секундах"
        }
    },
    "query":{
        "api_path": "/api/ds/query/",
        "datasource_type": "prometheus",
        "expr":"probe_success{foo=\"bar\"}",
        "server_timezone":"Europe/Moscow",
        "ttl":600,
        "data_source_uid": {"foo": "bar"}
    },
    "generate_parameters":
    {
        "gte":
        {
            "type": "-timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "time_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        },
        "lte":
        {
            "type": "+timedelta",
            "timestamp_field": "timestamp",
            "delta_field": "time_delta",
            "output_format": "%Y-%m-%dT%H:%M:%S.%f%z"
        }
    }
}
```

## Pandas step functions
### dynamic_aggr
Кастомная функция pandas, динамическая агрегация предполагает максимальное сжатие данных по выбранным полям (значения объединяются в list).

```json
"TBD":"TBD"
```
### aggr
Стандартное агрегирование данных с помощью pandas.

```json
{
    "description": "Агрегация данных",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "aggr",
    "input_parameters":{
        "target_data": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "target_data",
            "description":"Данные для агрегирования"
        },
        "list_to_str_dict": {
            "type": "dict",
            "required": false,
            "default": {},
            "description":"Правило преобразования поля pandas list->str"
        },
        "groupby_list": {
            "type": "list",
            "required": true,
            "default": [],
            "description":"Поля агрегирования помимо поля времени key"
        },
        "agg_dict": {
            "type": "dict",
            "required": true,
            "default": {},
            "description":"Описание агрегации pandas"
        }
    },
    "query":
    {
        "target_data":"%(target_data)s",
        "list_to_str_dict":"%(list_to_str_dict)d",
        "groupby_list":"%(groupby_list)l",
        "agg_dict":"%(agg_dict)d"
    },
    "generate_parameters":
    {}
}
```
### time_grouper_aggr
Стандартное агрегирование данных с помощью pandas + добавление группировки по времени.

```json
{
    "description": "Агрегация данных по периодам времени",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "time_grouper_aggr",
    "input_parameters":{
        "frequency": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "600s",
            "description":"Период агрегирования"
        },
        "key": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "timestamp",
            "description":"Поле времени"
        },
        "format": {
            "type": "string",
            "max_length": 100,
            "required": false,
            "default": "%Y-%m-%dT%H:%M:%S.%f%z",
            "description":"Формат времени"
        },
        "target_data": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "target_data",
            "description":"Данные для агрегирования"
        },
        "list_to_str_dict": {
            "type": "dict",
            "required": false,
            "default": {},
            "description":"Правило преобразования поля pandas list->str"
        },
        "groupby_list": {
            "type": "list",
            "required": true,
            "default": [],
            "description":"Поля агрегирования помимо поля времени key"
        },
        "agg_dict": {
            "type": "dict",
            "required": true,
            "default": {},
            "description":"Описание агрегации pandas"
        }
    },
    "query":
    {
        "target_data":"%(target_data)s",
        "list_to_str_dict":"%(list_to_str_dict)d",
        "groupby_list":"%(groupby_list)l",
        "agg_dict":"%(agg_dict)d"
    },
    "generate_parameters":
    {}
}
```
### shift
Сдвиг столбца на указанное количество строк.

```json
{
    "description": "Сдвиг столбца данных",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "shift",
    "input_parameters":{
        "target_data": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "target_data",
            "description":"Данные для сдвига"
        },
        "list_to_str_dict": {
            "type": "dict",
            "required": false,
            "default": {},
            "description":"Правило преобразования поля pandas list->str"
        },
        "groupby_list": {
            "type": "list",
            "required": true,
            "default": [],
            "description":"Поля группировки данных для сдвига в группе"
        },
        "target_column": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "target_column",
            "description":"Столбец для сдвига"
        },
        "result_column": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "result_column",
            "description":"Итоговый столбец"
        },
        "shift": {
            "type": "integer",
            "required": true,
            "default": 1,
            "description":"Размер сдвига"
        },
        "fill_value": {
            "type": "string",
            "max_length": 100,
            "required": true,
            "default": "fill_value",
            "description":"Заполнение пустого значения сдвига"
        }
    },
    "query":
    {
        "target_data":"%(target_data)s",
        "list_to_str_dict":"%(list_to_str_dict)d",
        "groupby_list":"%(groupby_list)l",
        "target_column":"%(target_column)s",
        "result_column":"%(result_column)s",
        "shift":"%(shift)i",
        "fill_value":"%(fill_value)s"
    },
    "generate_parameters":
    {}
}
```

### union
Объединение блоков данных в один с добавлением столбца __data_name__

```json
{
    "description": "Объединение блоков данных",
    "example": "",
    "llm":
    {
        "preprompt": "",
        "postprompt": ""
    },
    "source_function": "shift",
    "input_parameters":{
        "target_data": {
            "type": "list",
            "max_length": 100,
            "required": true,
            "default": ["target_data_1", "target_data_2"],
            "description":"Данные для объединения"
        }
    },
    "query":
    {
        "target_data":"%(target_data)l"
    },
    "generate_parameters":
    {}
}
```
## Ollama step functions
### chat
Взаимодействие с LLM через API ollama.

```json
"TBD":"TBD"
```

## Local llama step functions
### chat
Взаимодействие с локальной LLM (TBD).

```json
"TBD":"TBD"
```

## Step creating
Написание и поддержка шагов является основной задачей администратора Universal Harvester. Опытным путём было определено, что наиболее оптимальной стратегией будет создание generic-шагов с расширенным управлением через параметры выполнения. Это повышает возможности по переиспользованию уже существующих шагов. Использование правил именования шагов также помогает в работе. Universal Harvester не требует специальных имён для шагов, но наиболее удобно пользоваться следующим правилом именования: [Группа шага, например, PREPARATORY для подготовительных запросов, TEST для тестирования и т.д.] cуть выполняемого шага [Модификатор, например APPLY]. Например, [PREPARATORY] Generic field filter [APPLY].

Шаги можно копировать из существующего в новый.

## Step testing
Для тестирования шаги с желаемыми параметрами можно запускать из раздела Steps. Для шагов с зависимостями (pandas/sqlite3_in_memory/duckdb или apply) можно принудительно прикрепить данные шагов, которые были выполнены ранее. Шаг-кандидат на прикрепление проще всего искать в разделе Tasks. Как только выбраны необходимые для прикрепления шаги, можно их указать в параметрах следующим образом:
```json
{
  "parameter_1":"foo",
  "parameter_2":"bar",
  "__outervision__":{
    "data_name_1":"target_task_uuid_1",
    "data_name_2":"target_task_uuid_2"
  }
}
```

# Scenarios
Сценарием является последовательность шагов, которая будет выполнена по запросу с переданными параметрами.
Блок steps содержит список выполняемых шагов, в каждом шаге должны быть определены следующие параметры:
* step_name -- идентификатор выполняемого шага;
* data_name -- имя данных в рамках выполнения сценария, по этому имени данных другие шаги смогут получить доступ к данным этого шага, должно быть уникально для сценария;
* description -- описание шага, нужно для рисования красивой демонстрационной схемы сценария;
* show -- необходимость учёта данны в результат, данные с True попадают в результат выполнения pretty, json, xlsx, csv.

Необязательные параметры:
default_parameters_replacement -- переопределение параметров по умолчанию для шага в рамках текущего сценария.
apply_replacement -- переопределение блока apply для шага в рамках текущего сценария.

Блок (необязательный) conjoined_parameters позволяет задать правило объединения параметров разных шагов. Т.е. передача объединённого параметра автоматически определит все зависимые параметры.
description -- описание сценария, для сего он нужен, какую задачу выполняет.
Блок LLM сценария доступен для шагов ollama/llama, позволяет передать контекст выполняемой задачи.

```json
{
  "steps": [
    {
      "step_name": "[STATISTIC] Important step 1",
      "data_name": "foo",
      "description": "Получение списка foo",
      "show": false
    },
    {
      "step_name": "[PREPARATORY] Generic field filter",
      "data_name": "foo_filtred",
      "description": "Фильтрация списка foo",
      "show": false,
      "default_parameters_replacement": {
        "data_name": "foo",
        "filtred_field": "foo_terms",
        "filter_value": "LIKE '%' LIMIT 5"
      }
    },
    {
      "step_name": "[STATISTIC] Important step 2",
      "data_name": "bar",
      "description": "Получение bar",
      "show": false,
      "default_parameters_replacement": {
        "apply_target_data": "foo_filtred",
        "apply_target_field": "foo_terms",
        "host_ident_field": "foo_id"
      },
      "apply_replacement": {
        "target_data": "unioned_tags",
        "target_parameters": [
          {
            "column_name": "tag",
            "as": "tag"
          }
        ],
        "output_unique_fields": [
          "x1",
          "x2"
        ]
      }
    },
    {
      "step_name": "[PREPARATORY] Generic field filter",
      "data_name": "bar_filtred",
      "description": "Сортировка событий osquery audit",
      "show": false,
      "default_parameters_replacement": {
        "data_name": "bar",
        "filtred_field": "bar.id",
        "filter_value": "LIKE '%' ORDER BY `bar.id`"
      }
    },
    {
      "step_name": "[PREPARATORY] Generic pandas shift",
      "data_name": "bar_filtred_shifted",
      "description": "Сдвиг идентификаторов bar на 1",
      "show": false,
      "default_parameters_replacement": {
        "target_data": "bar_filtred",
        "list_to_str_dict": {},
        "groupby_list": [
          "barname",
          "applied_target"
        ],
        "target_column": "bar.id",
        "result_column": "bar.id_shift",
        "shift": -1,
        "fill_value": "empty"
      }
    },
    {
      "step_name": "[STATISTIC] Postprocessing aggs result",
      "data_name": "result",
      "description": "Результат",
      "show": true,
      "default_parameters_replacement": {
        "target_data": "bar_filtred_shifted"
      }
    }
  ],
  "conjoined_parameters": {
    "timestamp_start": [
      "0:timestamp_start",
      "2:timestamp_start"
    ],
    "timestamp_stop": [
      "0:timestamp_stop",
      "2:timestamp_stop"
    ]
  },
  "description": "Сценарий предназначен для анализа foobar",
  "llm": {
    "preprompt": "",
    "postprompt": ""
  }
}
```

## Scenario creating
Написание и поддержка сценариев является второй основной задачей администратора Universal Harvester. Следует также помнить, что изменение шага влечёт за собой изменение всех подчинённых сценариев, ревью сценариев следует проводить в том числе и после изменения шагов, входящих в сценарии. Использование правил именования сценариев помогает в работе, в первую очередб пользователям Universal Harvester. Приложение не требует специальных имён для шагов, но наиболее удобно пользоваться следующим правилом именования: [Группа сценария, например, SOC -- для применения в SOC] cуть выполняемого шага [дополнительный модификатор, например, FAST, HEAVY, EXPERIMENTAL]. Например, [SOC] DNS hunt [HEAVY].

Сценарии можно копировать из существующего в новый.

Как написать сценарий?
1. Уясняем задачу, под которую пишем сценарий, придумываем название и описание.
2. Наполняем блок steps шагами, при необходимости пишем шаги под сценарий. После добавления каждого шага можно запустить сценарий и посмотреть результат выполнения шагов в разделе Tasks.
3. При необходимости переопределяем параметры по умолчанию у шагов.
4. При необходимости определяем правила объединения параметров.
5. После итогового тестирования (при необходимости) пишем описание данных для LLM.

Писать сценарии очень сложно и трудозатратно. Вы по-настоящему прочувствуете все ваши данные, их качество и применимость для желаемых автоматизаций. "Perfer obdura, labor hic tibi proderit olim". 

# Tasks
Раздел Tasks позволяет просматривать выполняемые и уже выполненные шаги. Используется чаще всего при отладке сценариев, так как обеспечивает доступ к данным каждого выполненного шага. Не открывайте таски шагов с большим количеством строк результата (250к+), у браузера может не хватить ОЗУ для отрисовки такой таблицы.
## Tasks management
TBD

# Support
TBD

# Roadmap
TBD

# Contributing
TBD

# Authors and acknowledgment
Denis Strochenko/RWB SOC

# License
TBD

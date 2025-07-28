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

Подробная документация описана в [Wiki](https://github.com/wildberries-tech/universal-harvester/wiki) проекта.

# Authors and acknowledgment
Denis Strochenko/RWB SOC

import requests
import pandas, json
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName

def execute_ollama_chat_query(data_map, source, query, step, parameters, current_state):
    """Функция-интеграция с api ollama для взаимодействия с LLM в рамках сценария"""

    ##############################################
    # Подготовка prompt, отсюда будет понятна необходимая область видимости
    ##############################################

    try:
        request_prompt = ""
        zero_key = list(data_map.keys())[0]
        if "preprompt" in data_map[zero_key]["scenario_llm"]:
            request_prompt = request_prompt + data_map[zero_key]["scenario_llm"]["preprompt"] + "\n\n"

        for outer_data in query["data_for_analysis"]:
            data_name = outer_data["data_name"]
            data_representation_type = outer_data["representation_type"]

            if "preprompt" in data_map[data_name]["step_llm"]:
                request_prompt = request_prompt + data_map[data_name]["step_llm"]["preprompt"] + "\n\n"

            if data_representation_type == "markdown":
                current_data = pandas.DataFrame(data_map[data_name]["data"]).to_markdown(index=False)

            if data_representation_type == "json":
                current_data = json.dumps(data_map[data_name]["data"], indent=2)

            request_prompt = request_prompt + current_data + "\n\n"

            if "postprompt" in data_map[data_name]["step_llm"]:
                request_prompt = request_prompt + data_map[data_name]["step_llm"]["postprompt"] + "\n\n"


        if "postprompt" in data_map[zero_key]["scenario_llm"]:
            request_prompt = request_prompt + data_map[zero_key]["scenario_llm"]["postprompt"] + "\n\n"
    
        request_prompt = request_prompt + query["main_prompt"]

        ##############################################
        # Делаем запрос. Это актуально для ручки  http://foobarhost/api/chat
        ##############################################
        #print(request_prompt) 
        response = requests.post(
                query["url"], # индекс туда должен вставляться на этапе инъектирования параметров
                json={
                    "model":query["model"],
                    "messages":[{"role":"user", "content":request_prompt}],
                    "stream":False,
                    "format":query["format"]
                },
                headers={
                    'user-agent': f'{current_state["app_name"]}/{current_state["app_version"]}', 
                    'content-type': 'application/json', 
                    "Authorization": f"Bearer {source["key"]["value"]}"
                },
                verify=source["verify_certs"], timeout=source["request_timeout"]
            )
        response_code = response.status_code

        if response_code not in [200, 201]:
            error_message = f"fail response code {response_code}: {response.text}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        print(response.json())
        df = pandas.json_normalize([response.json()])
        try:
            df["message.content"] = df["message.content"].apply(eval)
            output_data = pandas.json_normalize(df.to_dict('records'))
        except BaseException as e:
            output_data = df.to_dict('records')
        output_data

        return True, "OK", currentFuncName(), output_data

    except BaseException as e:
        error_message = f"query fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
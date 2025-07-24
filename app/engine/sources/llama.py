from llama_cpp import Llama
import pandas, json
import syslog
from app.logging import get_log_message, logger_log, currentFuncName

def execute_llama_chat_query(data_map, source, query, step, parameters, current_state):
    """Функция-интеграция с llama для взаимодействия с локальной LLM в файле .gguf"""

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
        # Делаем запрос.
        ##############################################
        llm = Llama(
            model_path=current_state["storage_path"] + query["model_path"],
            n_ctx=query["context_length"],#32000,  # Context length to use
            n_threads=query["cpu_threads"],#32,            # Number of CPU threads to use
            n_gpu_layers=query["gpu_layers"]#0        # Number of model layers to offload to GPU
        )
        ## Generation kwargs
        generation_kwargs = {
            "max_tokens":query["max_tokens"],#20000
            "stop":query["stop"],#["</s>"],
            "echo":False, # Echo the prompt in the output
            "top_k":1 # This is essentially greedy decoding, since the model will always return the highest-probability token. Set this value > 1 for sampling decoding
        }

        ## Run inference
        res = llm(request_prompt, **generation_kwargs) # Res is a dictionary

        output_data = [{"message":res["choices"][0]["text"]}]

        return True, "OK", currentFuncName(), output_data

    except BaseException as e:
        error_message = f"query fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
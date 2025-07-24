import pandas
import numpy
import copy
import json
import syslog
from app.logging import currentTimestamp, get_log_message, logger_log, currentFuncName

def rename(col):
    if isinstance(col, tuple):
        col = '_'.join(str(c) for c in col)
        if col[-1] == '_':
            col = col[:-1]
    return col

def get_aggr_node(df, list_aggregate_fields, agg_params):
    # нам нужно найти самое максимальное сочетание данных по агрегируемым полям
    # для этого мы делаем агрегацию с помощью пандаса, так быстрее по производительности, но расточительнее по памяти
    # плюс это добавит простоты к коду
    # выделяя каждый раз максимальное, мы разберём весь скоп данных по принципу максимального покрытия
    df_filtred = df.loc[df["aggregated"] == False]
    debug = True
    # выделяем варианты агрегирования
    variants = []
    for field in list_aggregate_fields:
        buf_list = copy.deepcopy(list_aggregate_fields)
        buf_list.remove(field)
        variants.append(buf_list)
    if debug:
        print("Варианты агрегации:",variants)


    variants_weight = []
    for variant in variants:
        df_search = df_filtred
        filter = {}
        for field in variant:
            filter[field] = df_filtred.iloc[0][field]
        df_search = df_filtred.loc[(df_filtred[list(filter)] == pandas.Series(filter)).all(axis=1)]
        
        #df_search_aggr = df_search.groupby(variant,dropna=False).agg(count=(count_field,"count")).reset_index()
        #вытаскиваем дикт с найденными значениями агрегационных полей
        #max_value_aggr_fields_dict = df_search_aggr.loc[df_search_aggr["count"] == df_search_aggr["count"].max()].to_dict('records')[0]
        variants_weight.append(df_search.shape[0]) 
    
    if debug:
        print("Веса агрегации:",variants_weight)

    #ищем вариант с максимальным весом
    variant_max = numpy.argmax(variants_weight)
    if debug:
        print("Вариант с наибольшим весом:",variant_max)

    df_search = df_filtred
    filter = {}
    for field in variants[variant_max]:
        filter[field] = df_filtred.iloc[0][field]
    df_search = df_filtred.loc[(df_filtred[list(filter)] == pandas.Series(filter)).all(axis=1)]
    # выделяем данные согласно варианту
    agg_params_current = agg_params
    agg_params_current[[x for x in list_aggregate_fields if x not in variants[variant_max]][0]] = lambda x: ','.join(sorted(pandas.Series.unique(x)))
    df_output = df_search.groupby(variants[variant_max],dropna=False).agg(agg_params_current).reset_index(allow_duplicates=True)

    df_filtred_new = df
    df_filtred_new.loc[(df_filtred_new[list(filter)] == pandas.Series(filter)).all(axis=1), "aggregated"] = True

    return df_output#, df_filtred_new

def execute_pandas_aggregation(data_map, source, query, step, parameters, current_state):
    try:
        #################################################
        # формируем блок необходимых переменных
        #################################################
        target_data = query["target_data"]
        list_to_str_dict = query["list_to_str_dict"]
        groupby_list = query["groupby_list"]
        agg_dict = query["agg_dict"]
        #################################################
        # Получаем исходыне данные из data_map
        #################################################
        try:
            df = pandas.DataFrame(data_map[target_data]["data"])
        except BaseException as e:
            error_message = f"list to str normalization fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        #################################################
        # Нормализуем данные, мы не можем работать с листом (может и с другими не можем)
        #################################################
        try:
            for list_field in list_to_str_dict.keys():
                new_string_field = list_to_str_dict[list_field]
                df[new_string_field] = df[list_field].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else x)

        except BaseException as e:
            error_message = f"list to str normalization fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        #################################################
        # Первичная агрегация пандасом
        #################################################
        try:
            df_pandas_aggregated = df.groupby(groupby_list,dropna=False).agg(agg_dict).reset_index()

            prepared_df = df_pandas_aggregated.fillna("-")
            prepared_df.columns = map(rename, prepared_df.columns)
        except BaseException as e:
            error_message = f"pandas aggregation fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        result_data = prepared_df.to_json(orient="records", date_format="iso")
        return True, "OK", currentFuncName(), json.loads(result_data)

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []

def execute_pandas_aggregation_with_time_grouper(data_map, source, query, step, parameters, current_state):
    try:
        #################################################
        # формируем блок необходимых переменных
        #################################################
        target_data = query["target_data"]
        list_to_str_dict = query["list_to_str_dict"]
        groupby_list = query["groupby_list"]
        agg_dict = query["agg_dict"]
        freq = parameters["frequency"]
        key = parameters["key"]
        format = parameters["format"]
        #################################################
        # Получаем исходыне данные из data_map
        #################################################
        try:
            df = pandas.DataFrame(data_map[target_data]["data"])
        except BaseException as e:
            error_message = f"list to str normalization fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        #################################################
        # Нормализуем данные, мы не можем работать с листом (может и с другими не можем)
        #################################################
        try:
            for list_field in list_to_str_dict.keys():
                new_string_field = list_to_str_dict[list_field]
                df[new_string_field] = df[list_field].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else x)

        except BaseException as e:
            error_message = f"list to str normalization fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        #################################################
        # Преобразуем столбец со временем в pandas datetime
        #################################################
        try:
            df[key] = pandas.to_datetime(df[key], format=format)
        except BaseException as e:
            error_message = f"pandas.to_datetime fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        #################################################
        # Первичная агрегация пандасом
        #################################################
        try:
            groupby_list.append(pandas.Grouper(freq=freq, key=key))
            df_pandas_aggregated = df.groupby(groupby_list,dropna=False).agg(agg_dict).reset_index()

            prepared_df = df_pandas_aggregated.fillna("-")
            prepared_df.columns = map(rename, prepared_df.columns)
        except BaseException as e:
            error_message = f"pandas aggregation fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        

        result_data = prepared_df.to_json(orient="records", date_format="iso")
        return True, "OK", currentFuncName(), json.loads(result_data)

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    
def execute_pandas_dynamic_aggregation(data_map, source, query, step, parameters, current_state):
    # groupby_list
    # [
    #     "host.hostname", #*
    #     "decorations.computer_name",
    #     "kibana.alert.rule.name", #*
    #     "signal.rule.description",
    #     "indices",
    #     "process.command_line" #*
    # ]
    # agg_dict
    # {
    #     '@timestamp': ['min',"max","count"],
    #     'signal.original_time': ['min',"max","count"],
    #     'process.pid': ['min',"max","count"]
    # }
    #dynamic_groupby_list ["host.hostname","kibana.alert.rule.name","process.command_line"]
    # dynamica_agg_dict = {
    #     "@timestamp_min":"min",
    #     "@timestamp_max":"max",
    #     "@timestamp_count":"sum"
    # }
    #################################################
    # формируем блок необходимых переменных
    #################################################
    target_data = query["target_data"]
    list_to_str_dict = query["list_to_str_dict"]
    groupby_list = query["groupby_list"]
    agg_dict = query["agg_dict"]
    dynamic_groupby_list = query["dynamic_groupby_list"]
    dynamica_agg_dict = query["dynamica_agg_dict"]
    #################################################
    # Получаем исходыне данные из data_map
    #################################################
    try:
        df = pandas.DataFrame(data_map[target_data]["data"])
    except BaseException as e:
        error_message = f"list to str normalization fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    #################################################
    # Нормализуем данные, мы не можем работать с листом (может и с другими не можем)
    #################################################
    try:
        for list_field in list_to_str_dict.keys():
            new_string_field = list_to_str_dict[list_field]
            df[new_string_field] = df[list_field].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else x)

    except BaseException as e:
        error_message = f"list to str normalization fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    #################################################
    # Первичная агрегация пандасом
    #################################################
    try:
        df_pandas_aggregated = df.groupby(groupby_list,dropna=False).agg(agg_dict).reset_index()

        prepared_df = df_pandas_aggregated.fillna("-")
        prepared_df.columns = map(rename, prepared_df.columns)
    except BaseException as e:
        error_message = f"pandas aggregation fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    #################################################
    # Динамическая агрегация
    #################################################
    try:
        prepared_df["aggregated"] = False
        df_input = prepared_df
        y = 1
        while True:
            #print("Слой агрегации", y)
            df_input["aggregated"] = False
            output_df_list = []
            i = 0
            while df_input.loc[df_input["aggregated"] == True].shape[0] < df_input.shape[0]:
                output_df_list = output_df_list + get_aggr_node(df_input, dynamic_groupby_list, dynamica_agg_dict).to_dict('records')  
                i += 1
            else:
                pass
                #print('Цикл окончен, итераций было сделано', i)
            df_output = pandas.DataFrame(output_df_list)

            if df_input.shape[0] > df_output.shape[0]:
                #print("Исходное количество записей", df_input.shape[0])
                #print("Итоговое количество записей", df_output.shape[0])
                y = y + 1
                #df_input = df_output
                df_input = df_output.copy(deep=True)
            else:
                #print("Агрегирование завершено за ", y, "итераций")
                break
        result_data = df_input.to_json(orient="records", date_format="iso")
        return True, "OK", currentFuncName(), json.loads(result_data)#.to_dict('records')
        #return True, "OK", currentFuncName(), df_input.to_dict('records')
    
    except BaseException as e:
        error_message = f"dynamic aggregation fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
    
def execute_pandas_shift(data_map, source, query, step, parameters, current_state):
    try:
        #################################################
        # формируем блок необходимых переменных
        #################################################
        target_data = query["target_data"]
        list_to_str_dict = query["list_to_str_dict"]
        groupby_list = query["groupby_list"] # отдельный вариант, если он пустой
        target_column = query["target_column"]
        result_column = query["result_column"]
        shift = query["shift"]
        fill_value = query["fill_value"]
        #################################################
        # Получаем исходыне данные из data_map
        #################################################
        try:
            df = pandas.DataFrame(data_map[target_data]["data"])
        except BaseException as e:
            error_message = f"list to str normalization fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        #################################################
        # Нормализуем данные, мы не можем работать с листом (может и с другими не можем)
        #################################################
        try:
            for list_field in list_to_str_dict.keys():
                new_string_field = list_to_str_dict[list_field]
                df[new_string_field] = df[list_field].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else x)

        except BaseException as e:
            error_message = f"list to str normalization fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        #################################################
        # Делаем shift
        #################################################
        try:
            if len(groupby_list) == 0:
                df[result_column] = df[target_column].shift(shift, fill_value=fill_value)
            else:
                df[result_column] = df.groupby(groupby_list)[target_column].shift(shift, fill_value=fill_value)

            prepared_df = df.fillna("-")
            prepared_df.columns = map(rename, prepared_df.columns)
        except BaseException as e:
            error_message = f"pandas aggregation fail: {str(e)}"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        result_data = prepared_df.to_json(orient="records", date_format="iso")
        return True, "OK", currentFuncName(), json.loads(result_data)

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []

def execute_pandas_union(data_map, source, query, step, parameters, current_state):
    try:
        #################################################
        # формируем блок необходимых переменных
        #################################################
        target_data_list = query["target_data"]

        #################################################
        # Получаем исходыне данные из data_map
        #################################################
        unioned_data = []

        if isinstance(query["target_data"], list) == False:
            error_message = f"target_data is not a list"
            logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
            return False, error_message, currentFuncName(), []
        
        for target_data in target_data_list:
            df_target_data = pandas.DataFrame(data_map[target_data]["data"])
            df_target_data["_data_name_"] = target_data

            unioned_data = unioned_data + df_target_data.to_dict('records')

        return True, "OK", currentFuncName(), unioned_data

    except BaseException as e:
        error_message = f"fail: {str(e)}"
        logger_log(syslog.LOG_ERR, get_log_message(f"{error_message}", currentFuncName(), current_state))
        return False, error_message, currentFuncName(), []
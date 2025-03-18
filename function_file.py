from datetime import datetime, timedelta
import hashlib
import pandas as pd
import numpy as np
import gspread
import streamlit as st

mapping_dow = {'Monday': 0,'Tuesday': 1,'Wednesday': 2,'Thursday': 3,'Friday': 4,'Saturday': 5,'Sunday': 6}

def read_gg_sheets(wb_url, ws_name, cred_location):
    gc = gspread.service_account(filename=cred_location)
    wb = gc.open_by_url(wb_url)
    ws = wb.worksheet(ws_name)
    data = pd.DataFrame(ws.get_all_records())
    return data


def next_weekday_in_interval_lst(start_date_input, end_date_input, target_weekdays=np.arange(0,7)):
    lst_weekday = []
    if isinstance(start_date_input, str) and isinstance(end_date_input, str):
        start_date = datetime.strptime(start_date_input, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_input, '%Y-%m-%d')
    else:
        start_date, end_date = start_date_input, end_date_input
    # Iterate through each day in the interval
    current_date = start_date
    while current_date <= end_date:
        # Check if the current date's weekday is in the target weekdays list
        if current_date.weekday() in target_weekdays:
            lst_weekday.append(current_date.strftime("%Y-%m-%d"))
        # Move to the next day
        current_date += timedelta(days=1)
    return lst_weekday

def next_weekday_in_interval(start_date_input, end_date_input, target_weekday_input):
    start_date = datetime.strptime(start_date_input, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_input, '%Y-%m-%d')
    target_weekday = int(target_weekday_input)
    
    days_until_target = (target_weekday - start_date.weekday()) % 7
    next_date = start_date + timedelta(days=days_until_target)

    matching_dates = []
    while next_date <= end_date:
        matching_dates.append(next_date.strftime('%Y-%m-%d'))
        next_date += timedelta(days=7)

    return matching_dates

def generate_hexacode(row):
    combined_string = ''.join(map(str, row))
    hash_object = hashlib.sha256(combined_string.encode('utf-8'))
    hex_dig = hash_object.hexdigest()
    hexacode = 'ord_' + hex_dig[:6]
    return hexacode

def generate_hour_block(start_time, end_time):
    time_range = pd.date_range(start=f'{int(start_time)}:00', end=f'{int(end_time)}:00', freq='H')
    return [f'{start.hour:02d}-{end.hour:02d}' for start, end in zip(time_range[:-1], time_range[1:])]

def color_value(val):
    if val == 3:
        bg_color = "red"
        txt_color = "white"
    elif val == 0:
        bg_color = "#00C000"
        txt_color = "white"
    else:
        bg_color = "white"
        txt_color = ""
    return f'color:{txt_color}; background-color: {bg_color};'



def preprocessing_data_calendar(data_frame, start_date_calendar, end_date_calendar, data_type = 'Filter Data'):
    data = pd.DataFrame(data_frame, dtype=str)
    if data.shape[0] >0:
        data[['StartTime', 'EndTime']] = data[['StartTime', 'EndTime']].apply(pd.to_numeric)
        data['OrderID'] = data.drop(['CustomerType'], axis = 1).apply(generate_hexacode, axis = 1)
        data['DayOfWeek_Split'] = data['DayOfWeek'].str.split('_')
        data = data.explode('DayOfWeek_Split')
        data['DayOfWeek_Split'].replace(mapping_dow, inplace = True)
        data['DeliverDate'] = data.apply(lambda row: next_weekday_in_interval(row['StartDate'], row['EndDate'], row['DayOfWeek_Split']), axis = 1)
        data = data.explode('DeliverDate')
        data['DayName'] = pd.to_datetime(data['DeliverDate']).dt.day_name()
        data['HourBlock'] = data.apply(lambda row: generate_hour_block(row['StartTime'], row['EndTime']), axis=1)
        data = data.explode('HourBlock').sort_values(by = ['OrderID', 'DeliverDate', 'HourBlock']).drop(['DayOfWeek_Split'], axis = 1).reset_index(drop=True)

        if data_type == 'All Data':
            data_calendar_hour_block = pd.DataFrame({'DeliverDate':pd.date_range(start_date_calendar, end_date_calendar)}, dtype=str)\
                                    .merge(pd.DataFrame({'HourBlock': generate_hour_block(6,23)}, dtype = str), how = 'cross')
            data_calendar_hour_block['DayName'] = pd.to_datetime(data_calendar_hour_block['DeliverDate']).dt.day_name()
            data = data_calendar_hour_block.merge(data, how = 'left', left_on = ['DeliverDate', 'HourBlock', 'DayName'], right_on = ['DeliverDate', 'HourBlock', 'DayName'])
        
        column_deliver_date, column_hour_block = ['DeliverDate', 'HourBlock']
        ###----------------------------------------------------------------###
        data_pivot_customer = pd.pivot_table(data, index = [column_deliver_date], columns = column_hour_block, values = 'CustomerID', \
                                    aggfunc = lambda x: ' || '.join( sorted(x.fillna(''))) ).reset_index()
        data_pivot_court = pd.pivot_table(data, index = [column_deliver_date], columns = column_hour_block, values = 'CourtNumber', \
                                    aggfunc = lambda x: ' || '.join( sorted(x.fillna(''))) ).reset_index()
       
        data_pivot_count = pd.pivot_table(data, index = column_deliver_date, columns = column_hour_block, values = 'CustomerID', aggfunc = 'count')
        data_pivot_count.fillna(0,inplace = True)
        data_pivot_count_styled = data_pivot_count.style.map(color_value).format('{:.0f}')
        ###----------------------------------------------------------------###
    else:
        raise Exception("Cannot read the Dataframe")
    
    return data, data_pivot_customer, data_pivot_court


def switch_chart_streamlit(chart1, chart2, button_name):
    if 'show_table_1' not in st.session_state:
        st.session_state.show_table_1 = True
    if st.button(button_name):
        st.session_state.show_table_1 = not st.session_state.show_table_1
        
    if st.session_state.show_table_1:
        st.dataframe(chart1)
    else:
        st.dataframe(chart2)



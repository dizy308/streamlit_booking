import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
import os
import time
import calendar

import gspread

import warnings
warnings.filterwarnings('ignore')
from function_file import *

st.set_page_config(page_icon=":car:", page_title="Booking App", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
data_template = conn.read()

lst_cols_template = ['OrderTime', 'CustomerID', 'CustomerType', 'StartTime', 'EndTime', 'StartDate', 'EndDate', 'DayOfWeek', 'CourtNumber', 'Note']
lst_courts_template = ['C_1', 'C_2', 'C_3']
lst_dow_template = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

if data_template.shape[1] == len(lst_cols_template):
    st.session_state.bookings = conn.read()
else:
    st.session_state.bookings = pd.DataFrame(columns=lst_cols_template)


current_datetime = datetime.now().date()
page = st.sidebar.selectbox("Choose a page", ["Calendar", "Booking"])

if page == 'Booking':
    st.markdown(
    """
    <style>
    .main .block-container {
        max-width: 60%;}
    </style>
    """,
    unsafe_allow_html=True)


    st.markdown("<h1 style='text-align: center; color: red;'>THÔNG TIN ĐẶT SÂN</h1>", unsafe_allow_html=True)
    with st.form("booking_form"):
        col1, col2 = st.columns(2)
        with col1:
            order_date = st.date_input("Order Date", value = current_datetime, format = "YYYY-MM-DD")
            customer_id = st.text_input("Customer ID")
            customer_type = st.selectbox("Customer Type", ["Cố Định", "Vãng Lai"], index=None)
            court_num = st.selectbox("Court Number", lst_courts_template, index = None)
            note_box = st.text_input("Note", value = " ")  

        with col2:
            day_of_week = st.multiselect("Day of Week", lst_dow_template, key="test_group_1")
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            start_time = st.selectbox("Start Time (Hour)", options=range(6, 23), index=0) 
            end_time = st.selectbox("End Time (Hour)", options=range(7, 24), index=0) 

        submitted = st.form_submit_button("Update Data")

    if submitted:
        with st.spinner("Processing your booking..."):
            time.sleep(1)
            st.session_state.bookings = conn.read(ttl=5)
        invalid_days = [day for day in day_of_week if not any((start_date + timedelta(days=i)).strftime("%A") == day for i in range((end_date - start_date).days + 1))]
        if invalid_days:
            st.error(f"The selected {invalid_days} do not exist within the date range {start_date} to {end_date}.", icon="🚨")
        elif not all([customer_id, customer_type, start_time, end_time, start_date, end_date, day_of_week, court_num]):
            st.error("Please fill out all fields.")
        elif end_date < start_date or end_time <= start_time:
            st.error("End Time must be later than Start Time.")
        elif not day_of_week:
            st.error("Please select at least one day.")

        # Check if the selected days of the week exist within the date range
        else:
            day_of_week_str = "_".join(day_of_week)
            # Check if the time slot is occupied for any of the selected days
            if st.session_state.bookings.empty:
                is_occupied = False
            else:
                is_occupied = False
                for day in day_of_week:
                    occupied = st.session_state.bookings[
                        (st.session_state.bookings['DayOfWeek'].str.contains(day)) & 
                        (
                            ((st.session_state.bookings['StartDate'] <= datetime.strftime(start_date, "%Y-%m-%d")) & (st.session_state.bookings['EndDate'] >= datetime.strftime(start_date, "%Y-%m-%d"))) |
                            ((st.session_state.bookings['StartDate'] <= datetime.strftime(end_date, "%Y-%m-%d")) & (st.session_state.bookings['EndDate'] >= datetime.strftime(end_date, "%Y-%m-%d"))) |
                            ((st.session_state.bookings['StartDate'] >= datetime.strftime(start_date, "%Y-%m-%d")) & (st.session_state.bookings['EndDate'] <= datetime.strftime(end_date, "%Y-%m-%d")))
                        ) & 
                        (
                            (st.session_state.bookings['StartTime'] < end_time) & 
                            (st.session_state.bookings['EndTime'] > start_time) &
                            (st.session_state.bookings['CourtNumber'] == court_num) 
                        )
                    ].any().any()
                    if occupied:
                        is_occupied = True
                        break

            if is_occupied:
                st.error("This time slot is already occupied for one or more selected days. Please choose another time.")
            else:
                # Add the booking to the DataFrame
                new_booking = pd.DataFrame({
                    'OrderTime': [order_date],
                    'CustomerID': [customer_id],
                    'CustomerType': [customer_type],
                    'StartTime': [start_time],
                    'EndTime': [end_time],
                    'StartDate': [start_date],
                    'EndDate': [end_date],
                    'DayOfWeek': [day_of_week_str],
                    'CourtNumber' : [court_num],
                    'Note' : [note_box],
                })
                st.session_state.bookings = pd.concat([st.session_state.bookings, new_booking], ignore_index=True)
                conn.update(worksheet="InputData", data=st.session_state.bookings)
                
                success_message = st.success("Court booked successfully!")
                time.sleep(3)
                success_message.empty()
    else:
        st.session_state.bookings = conn.read()
            
elif page == 'Calendar':
    st.markdown(
        """
        <style>
        .main .block-container {max-width: 80%;}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<h1 style='text-align: center; color: green;'>DỮ LIỆU ĐẶT SÂN 📅</h1>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        calendar_type = st.selectbox("Filter Data Type", ["Filter Data", "All Data"], index = 1)
    
    data_booking = st.session_state.bookings
    tab2_1, tab2_2, tab2_3 = st.tabs(["Calendar", "Kiểm tra Lịch", "Tải dữ liệu"])

    start_date_input = (current_datetime .replace(day = 1)).strftime('%Y-%m-%d')
    end_date_input = (current_datetime.replace(day = 1)  + relativedelta(day = 31)).strftime('%Y-%m-%d')


    df_raw, df_pivot_customer, df_pivot_court = preprocessing_data_calendar(data_booking, data_type = calendar_type, 
                                                                         start_date_calendar=start_date_input,end_date_calendar=end_date_input)
    with tab2_1:
        col1, col2, col3 = st.columns(3)
        ###----------------Set Up Filter----------------###
        with col1:
            lst_date_range = st.date_input("Select Date Range", (current_datetime, current_datetime))
            
        with col2:
            lst_hour_block = st.multiselect("Select Hour Block", generate_hour_block(6,22))
        with col3:
            dow_filter = st.multiselect("Day of Week", lst_dow_template)

        if isinstance(lst_date_range, (list, tuple)) and len(lst_date_range) == 2:
            start_date_filter, end_date_filter = lst_date_range
            lst_date_filter = next_weekday_in_interval_lst(start_date_filter, end_date_filter)
        else:
            st.stop()

        st.markdown("<br>", unsafe_allow_html=True)
        ###---------------------------------------------###
        if dow_filter != []:
            lst_date_filter = next_weekday_in_interval_lst(start_date_filter, end_date_filter,  [mapping_dow[t] for t in dow_filter if t != "All"])

        cond_filter =  (df_raw.DeliverDate.isin(lst_date_filter))
        if lst_hour_block != []:
            cond_filter = (df_raw.DeliverDate.isin(lst_date_filter)) & (df_raw.HourBlock.isin(lst_hour_block))

        data_calendar_check = pd.pivot_table(df_raw.loc[cond_filter], index = ['DeliverDate', 'DayName'], columns = 'HourBlock', \
                                        values = 'CourtNumber', aggfunc = 'count').reset_index().fillna(0)
        data_calendar_check_styled = data_calendar_check.style.map(color_value) \
                                                            .format('{:.0f}', subset=data_calendar_check.select_dtypes(include=['number']).columns)
        
        data_calendar_note = pd.pivot_table(df_raw.loc[cond_filter], index = ['DeliverDate', 'DayName'], columns = 'HourBlock', \
                                        values = 'Note', aggfunc = lambda x: ' || '.join( sorted(x.fillna(''))) ).reset_index()

        switch_chart_streamlit(data_calendar_check_styled, data_calendar_note, "Change View")
        
    with tab2_2:
        switch_chart_streamlit(df_pivot_court, df_pivot_customer, "Switch Data")

    with tab2_3:
        st.title('InputData')
        st.dataframe(data_booking)
        st.title('RawData')
        st.dataframe(df_raw)
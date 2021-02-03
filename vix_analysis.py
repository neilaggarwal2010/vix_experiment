import requests
import time
import datetime
import numpy as np
import json
from decimal import Decimal
import re
import time
from time import sleep
import traceback
import urllib.parse
from xlrd import open_workbook
import xlrd
import xlsxwriter
from dateutil.relativedelta import relativedelta
from scipy import stats


#######################
#
# GENERAL
#
#######################

def excel_date(date1):
    temp = datetime.datetime(1899, 12, 30)    
    delta = date1 - temp
    return float(delta.days) + (float(delta.seconds) / 86400)

def calc_annualized_appreciation(years, total_return):
    return None


def limit_stock_list_to_window_of_time(stock, date_start, date_end):
    timestamp_start = time.mktime(datetime.datetime.strptime(date_start, "%Y-%m-%d").timetuple())
    timestamp_end = time.mktime(datetime.datetime.strptime(date_end, "%Y-%m-%d").timetuple())
    temp_stock = {}
    for e in stock:
        if e > timestamp_end:
            break
        if e >= timestamp_start:
            temp_stock[e] = stock[e]
    return temp_stock


def calculate_return_of_stock_during_holding_periods(stock_holding, leverage_multiple):
    last_month = 0
    last_year = 0

    #there is a open value and a close value - open value allows for ROI calc starting from that date.  
    daily_returns = {}
    daily_returns_3x = {}
    
    returns_by_month = []
    returns_by_month_3x = []
    
    running_tally = 1
    running_tally_3x = 1
    
    last_price = -1
    for e in stock_holding:

        if last_price > -1 or stock_holding[e]['buy'] == "buy":

            daily_returns[e] = {'timestamp': e, 'month': stock_holding[e]['month'], 'day': stock_holding[e]['day'], 'year': stock_holding[e]['year']}
            daily_returns_3x[e] = {'timestamp': e, 'month': stock_holding[e]['month'], 'day': stock_holding[e]['day'], 'year': stock_holding[e]['year']}
            
            daily_returns[e]['open'] = running_tally
            daily_returns_3x[e]['open'] = running_tally_3x
            
            if stock_holding[e]['buy'] == "buy" or stock_holding[e]['buy'] == "buy and sell":
                last_price = stock_holding[e]['open'] # - assume buy at open, should get intraday data and create a buffer 
                
            if stock_holding[e]['buy'] == "sell":
                #assumes we sell as soon after open as possible - assuming immediate sell - should get intraday data and create a time buffer
                running_tally = running_tally * (1 + ((stock_holding[e]['open'] - last_price)/last_price))
                running_tally_3x = running_tally_3x * (1 + (((stock_holding[e]['open'] - last_price)/last_price)*leverage_multiple))
                
            elif stock_holding[e]['buy'] == "buy and sell" or stock_holding[e]['buy'] == "sell at close":
                #assumes we sell shortly before close - assuming immediate sell - should get intraday data and create a time buffer
                running_tally = running_tally * (1 + ((stock_holding[e]['close'] - last_price)/last_price))
                running_tally_3x = running_tally_3x * (1 + (((stock_holding[e]['close'] - last_price)/last_price)*leverage_multiple))
                
            else:
                running_tally = running_tally * (1 + ((stock_holding[e]['close'] - last_price)/last_price))
                running_tally_3x = running_tally_3x * (1 + (((stock_holding[e]['close'] - last_price)/last_price)*leverage_multiple))
                last_price = stock_holding[e]['close']

            daily_returns[e]['close'] = running_tally
            daily_returns_3x[e]['close'] = running_tally_3x
                
            if last_month == 0:
                last_month = stock_holding[e]['month']
            if last_month != stock_holding[e]['month']:
                returns_by_month.append([str(stock_holding[e]['month']) + "-" + str(stock_holding[e]['year']), running_tally, running_tally_3x])
                last_month = stock_holding[e]['month']
        

    return running_tally, running_tally_3x, returns_by_month, returns_by_month_3x, daily_returns, daily_returns_3x

#######################
#
# GET STOCK PRICE DATA
#
#######################

def get_stock_data_from_excel(ticker, location_of_excel_folders):
    prices_by_time = []
    book = open_workbook(location_of_excel_folders + ticker + ".xls")
    sheet = book.sheet_by_index(0)

    # read first row for keys  
    keys = sheet.row_values(0)

    # read the rest rows for values
    counter = 0
    for e in sheet:
        if counter > 0:
            if e[1].value != "n/a":
                try:
                    #extract date from excel is special process
                    book_datemode = book.datemode
                    year, month, day, hour, minute, second = xlrd.xldate_as_tuple(e[0].value, book.datemode)
                    timestamp = time.mktime(datetime.datetime.strptime(str(year) + "-" + str(month) + "-" +  str(day), "%Y-%m-%d").timetuple())
                    
                    prices_by_time.append({'timestamp': timestamp,
                                           'actual_day': str(year) + "-" + str(month) + "-" +  str(day),
                                           'open': e[1].value,
                                           'high': None,
                                           'low': None,
                                           'close': e[2].value,
                                           'adjusted_close': None,
                                           'split_coefficient': None,
                                           'dividend': None,
                                           'month': month,
                                           'year': year,
                                           'day': day})
                except:
                    print(traceback.format_exc())
        counter += 1

    prices_by_time = sorted(prices_by_time, key= lambda x: x['timestamp'])   

    dictionary = {}
    for e in prices_by_time:
        dictionary[e['timestamp']] = e
    return dictionary





def get_vix_data(location_of_excel_folders):
    prices_by_time = []
    book = open_workbook(location_of_excel_folders + "vix.xls")
    sheet = book.sheet_by_index(0)
        single_day_data = {'year': year,
                           'day': day,
                           'timestamp': timestamp,
                           'human_readable_date': human_readable_date,
                           'open': stock_open,
                           'close': stock_close
                           }
        return single_day_data
    return None

def extract_one_row_of_stock_data(book, row):
    stock_open = row[1].value
    stock_close = row[2].value
    excel_date = row[0].value
    year, month, day, hour, minute, second, human_readable_date, timestamp = convert_excel_date_to_component_parts(book, excel_date)
    return build_dictionary_of_single_day_data(year, month, day, timestamp, human_readable_date, stock_open, stock_close)

def load_stock_data(Assumptions):
    stock = {}
    book, sheet = get_sheet_from_excel(Assumptions, Assumptions.stock + ".xls")
    counter = 0
    for row in sheet:
        if counter > 0:
            single_day_data = extract_one_row_of_stock_data(book, row)
            if single_day_data != None:
                stock[single_day_data['human_readable_date']] = single_day_data
        counter += 1
    return stock
        
#######################
#
# METRICS BY DAY
#
#######################

def calc_moving_avg_by_day(stock, days_for_moving_average):
    moving_average_by_day = {}
    stock_values = []
    days = 0
    for date in stock:
        sum_of_stock_values = 0
        if days >= days_for_moving_average:
            for close_price in stock_values[-1*days_for_moving_average:]:
                sum_of_stock_values += close_price
            moving_average_by_day[date] = sum_of_stock_values/days_for_moving_average
        else:
            moving_average_by_day[date] = None
        stock_values.append(stock[date]['close'])
        days += 1
    return moving_average_by_day

def extract_one_row_of_vix_data(book, row):
    vix_open = row[1].value
    vix_close = row[4].value
    excel_date = row[0].value
    year, month, day, hour, minute, second, human_readable_date, timestamp = convert_excel_date_to_component_parts(book, excel_date)
    return build_dictionary_of_single_day_data(year, month, day, timestamp, human_readable_date, vix_open, vix_close)

def load_vix_data(Assumptions):
    vix = {}
    book, sheet = get_sheet_from_excel(Assumptions, "vix.xls")
    counter = 0
    for row in sheet:
        if counter > 0:
            single_day_data = extract_one_row_of_vix_data(book, row)
            if single_day_data != None:
                vix[single_day_data['human_readable_date']] = single_day_data
        counter += 1
    return vix

class Metrics:

    def __init__(self, Assumptions, stock):
        self.vix = load_vix_data(Assumptions)
        self.moving_average_by_day_long = calc_moving_avg_by_day(stock, Assumptions.days_for_moving_average_long)
        self.moving_average_by_day_short = calc_moving_avg_by_day(stock, Assumptions.days_for_moving_average_short)


#######################
#
# TRIGGERS BY DAY
#
#######################

def check_whether_vix_is_below_threshold_by_day(Assumptions, Metrics):
    vix_position_below_treshold = {}
    for date in Metrics.vix:
        vix_position_below_treshold[date] = {}
        if Metrics.vix[date]['open'] <= Assumptions.vix_threshold:
            vix_position_below_treshold[date]['open'] = True
        else:
            vix_position_below_treshold[date]['open'] = False

            
        if Metrics.vix[date]['close'] <= Assumptions.vix_threshold:
            vix_position_below_treshold[date]['close'] = True
        else:
            vix_position_below_treshold[date]['close'] = False
            
    return vix_position_below_treshold
        



class Triggers:

    def __init__(self, Assumptions, stock, Metrics):
        self.vix_position_below_treshold = check_whether_vix_is_below_threshold_by_day(Assumptions, Metrics)



#######################
#
# RETURNS FOR EACH STRATEGY
#
#######################

def create_buy_sell_orders(triggers_by_date):
    last_day_we_have_data_for_stock = list(triggers_by_date.keys())[-1]
    buy_and_sell_orders_by_day = {}

    currently_holding_stock = False
    
    for date in triggers_by_date:
        
        if triggers_by_date[date]['open'] == True: 
            if currently_holding_stock == False:
                buy_and_sell_orders_by_day[date] = "buy"
                currently_holding_stock = True
            else:
                buy_and_sell_orders_by_day[date] = "hold"

            try:
                if triggers_by_date[date]['close'] == False:
                    currently_holding_stock = False
                    if buy_and_sell_orders_by_day[date] == "buy":
                        buy_and_sell_orders_by_day[date] = "buy and sell same day"
                    else:
                        buy_and_sell_orders_by_day[date] = "sell at close"
            except:
                pass

        else:
            if currently_holding_stock == True:
                buy_and_sell_orders_by_day[date] = "sell"
            currently_holding_stock = False

        if date == last_day_we_have_data_for_stock and currently_holding_stock == True: 
            try:
                if buy_and_sell_orders_by_day[date] == "buy":
                    buy_and_sell_orders_by_day[date] = "buy and sell same day"
                else:
                    buy_and_sell_orders_by_day[date] = "sell at close"
            except:
                buy_and_sell_orders_by_day[date] = "sell at close"
            
            currently_holding_stock = False
            
    return buy_and_sell_orders_by_day

def add_running_tally_by_day_open_data(running_tally_by_day, running_tally_by_day_3x, date, running_tally, running_tally_3x, stock):
    date_dictionary = {'month': stock[date]['month'],
                        'day': stock[date]['day'],
                        'year': stock[date]['year']}


    running_tally_by_day[date] = date_dictionary
    running_tally_by_day_3x[date] = date_dictionary
    
    running_tally_by_day[date]['open_running_tally'] = running_tally  
    running_tally_by_day_3x[date]['open_running_tally'] = running_tally_3x
    
    return running_tally_by_day, running_tally_by_day_3x

def add_running_tally_by_day_close_data(running_tally_by_day, running_tally_by_day_3x, date, running_tally, running_tally_3x, buy_and_sell_orders_by_day):
    running_tally_by_day[date]['close_running_tally'] = running_tally
    running_tally_by_day[date]['order'] = buy_and_sell_orders_by_day[date]
    
    running_tally_by_day_3x[date]['close_running_tally'] = running_tally_3x
    running_tally_by_day_3x[date]['order'] = buy_and_sell_orders_by_day[date]
    return running_tally_by_day, running_tally_by_day_3x


def calculate_current_return(current_price, last_price, leverage_multiple, running_tally, running_tally_3x):
    running_tally = running_tally * (1+ ((current_price - last_price)/last_price))
    running_tally_3x = running_tally_3x * (1+ (((current_price - last_price)/last_price) * leverage_multiple))
    return running_tally, running_tally_3x

def calculate_return_of_stock(buy_and_sell_orders_by_day, stock, leverage_multiple):
    running_tally = 1
    running_tally_3x = 1

    running_tally_by_day = {}
    running_tally_by_day_3x = {}

    last_price = False #switches to stock price after first buy order is fulfilled
    for date in buy_and_sell_orders_by_day:
        if date in stock:
            if last_price is not False or buy_and_sell_orders_by_day[date] == "buy" or buy_and_sell_orders_by_day[date] == "buy and sell same day":
                running_tally_by_day, running_tally_by_day_3x = add_running_tally_by_day_open_data(running_tally_by_day, running_tally_by_day_3x, date, running_tally, running_tally_3x, stock)

                if buy_and_sell_orders_by_day[date] == "buy" or buy_and_sell_orders_by_day[date] == "buy and sell same day":
                    last_price = stock[date]['open']

                if buy_and_sell_orders_by_day[date] == "sell":
                    running_tally, running_tally_3x = calculate_current_return(stock[date]['open'], last_price, leverage_multiple, running_tally, running_tally_3x)

                elif buy_and_sell_orders_by_day[date] == "buy and sell same day" or buy_and_sell_orders_by_day[date] == "sell at close":
                    running_tally, running_tally_3x = calculate_current_return(stock[date]['close'], last_price, leverage_multiple, running_tally, running_tally_3x)

                else:
                    running_tally, running_tally_3x = calculate_current_return(stock[date]['close'], last_price, leverage_multiple, running_tally, running_tally_3x)
                    last_price = stock[date]['close']

                running_tally_by_day, running_tally_by_day_3x = add_running_tally_by_day_close_data(running_tally_by_day, running_tally_by_day_3x, date, running_tally, running_tally_3x, buy_and_sell_orders_by_day)

    return running_tally_by_day, running_tally_by_day_3x


class Single_Strategy_Returns:

    def __init__(self, stock, buy_and_sell_orders, Assumptions):
        running_tally_by_day, running_tally_by_day_3x = calculate_return_of_stock(buy_and_sell_orders, stock, Assumptions.leverage_multiple)
        self.running_tally_by_day = running_tally_by_day
        self.running_tally_by_day_3x = running_tally_by_day_3x
        

class Returns:

    def __init__(self, stock, Triggers, Assumptions):
        self.vix_position_strategy = Single_Strategy_Returns(stock, create_buy_sell_orders(Triggers.vix_position_below_treshold), Assumptions)


#######################
#
# EXECUTE
#
#######################

Assumptions = Assumptions()
stock = load_stock_data(Assumptions)
Metrics = Metrics(Assumptions, stock)
Triggers = Triggers(Assumptions, stock, Metrics)
Returns = Returns(stock, Triggers, Assumptions)

    

        

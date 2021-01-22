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



#######################
#
# GENERAL
#
#######################

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
                                           'high': e[2].value,
                                           'low': e[3].value,
                                           'close': e[4].value,
                                           'adjusted_close': None,
                                           'split_coefficient': None,
                                           'dividend': None})
                except:
                    print(traceback.format_exc())
        counter += 1

    prices_by_time = sorted(prices_by_time, key= lambda x: x['timestamp'])   

    dictionary = {}
    for e in prices_by_time:
        dictionary[e['timestamp']] = e

    return dictionary



#######################
#
# MAKE DATA SETS THE SAME DATES (COMPARISONS SHOULD BE OF TWO DATA SETS WITH SAME DATES AND, THUS, SAME SIZE)
#
#######################

def make_data_sets_the_same_dates(data1, data2):
    new_data1 = {}
    new_data2 = {}

    for e in data2:
        if e in data1:
            new_data1[e] = data1[e]

    for e in new_data1:
        if e in data2:
            new_data2[e] = data2[e]

    return new_data1, new_data2
            

#######################
#
# VIX VELOCITY STRATEGIES
#
#######################


def calc_distribution_of_vix_velocity(vix_velocity):
    return None

def calc_vix_velocity(vix):
    vix_velocity = {}
    vix_distribution = {}

    
    vix_values = []
    counter = 0
    for e in vix:
        intra_day = vix[e]['open'] - vix[e]['close']
        two_day = None
        ten_day = None
        thirty_day = None
        
        if counter >= 1:
            two_day = vix[e]['open'] - vix_values[-1]
            
        if counter >= 10:
            ten_day = vix[e]['open'] - vix_values[-10]

        if counter >= 30:
            ten_day = vix[e]['open'] - vix_values[-30]

        vix_velocity[e] = {'intra_day': intra_day,
                           'two_day': two_day,
                           'ten_day': ten_day,
                           'thirty_day': thirty_day}
        
        vix_values.append(vix['open'])
        counter += 1

    return vix_velocity, vix_distribution

#######################
#
# 200 MOVING AVG AND VIX COMBO
#
#######################
def create_dictionary_of_periods_when_holding_stock_combo_strategy(vix, two_hundred_day_avg, vix_threshold, comparison):
    list_of_comparison_keys = list(comparison.keys())
    number_of_buys = 0
    stock_holding = {}
    buy = False
    for e in comparison:
        if e in two_hundred_day_avg and two_hundred_day_avg[e] != None and e in vix:
            dictionary = comparison[e]
            if comparison[e]['open'] >= two_hundred_day_avg[e] or vix[e]['open'] <= vix_threshold:

                if buy == False:
                    dictionary['buy'] = "buy"
                    buy = True
                    number_of_buys += 1
                else:
                    dictionary['buy'] = "hold"
                stock_holding[e] = dictionary

                if comparison[e]['close'] < two_hundred_day_avg[e] and vix[e]['close'] > vix_threshold:
                    buy = False
                    if stock_holding[e]['buy'] == "buy":
                        stock_holding[e]['buy'] = "buy and sell"
                    else:
                        stock_holding[e]['buy'] = "sell at close"
                
            else:
                if buy == True:
                    dictionary['buy'] = "sell"
                    stock_holding[e] = dictionary
                buy = False

            if list_of_comparison_keys[-1] == e:
                if buy == True:
                    dictionary['buy'] = "sell at close"
                    stock_holding[e] = dictionary
                buy = False                
                
    return stock_holding, number_of_buys

#######################
#
# 200 MOVING AVG STRATEGIES
#
#######################
def create_dictionary_of_periods_when_holding_stock_200_day_strategy(two_hundred_day_avg, comparison):
    list_of_comparison_keys = list(comparison.keys())
    number_of_buys = 0
    stock_holding = {}
    buy = False
    for e in comparison:
        if e in two_hundred_day_avg and two_hundred_day_avg[e] != None:
            dictionary = comparison[e]
            if comparison[e]['open'] >= two_hundred_day_avg[e]:

                if buy == False:
                    dictionary['buy'] = "buy"
                    buy = True
                    number_of_buys += 1
                else:
                    dictionary['buy'] = "hold"
                stock_holding[e] = dictionary
                
                if comparison[e]['close'] < two_hundred_day_avg[e]:
                    buy = False
                    if stock_holding[e]['buy'] == "buy":
                        stock_holding[e]['buy'] = "buy and sell"
                    else:
                        stock_holding[e]['buy'] = "sell at close"

                
            else:
                if buy == True:
                    dictionary['buy'] = "sell"
                    stock_holding[e] = dictionary
                buy = False

            if list_of_comparison_keys[-1] == e:
                if buy == True:
                    dictionary['buy'] = "sell at close"
                    stock_holding[e] = dictionary
                buy = False
                
    return stock_holding, number_of_buys

def calc_200_day_moving_average(comparison, days_for_moving_average):
    two_hundred_day_avg = {}
    values = []
    counter = 0
    for e in comparison:
        sum_of_values = 0
        two_hundred_day_avg[e] = None
        if counter >= days_for_moving_average:
            for ele in range(0, len(values)):
                sum_of_values = sum_of_values + values[ele]
            two_hundred_day_avg[e] = sum_of_values/days_for_moving_average
            values = values[1:] + [comparison[e]['close']]
        else:
            values.append(comparison[e]['close'])
        counter += 1
    return two_hundred_day_avg
    

#######################
#
# VIX VALUE STRATEGIES
#
#######################

def get_maximum_and_minimum_vix(vix):
    maximum_vix = 0
    minimum_vix = 10000000
    for e in vix:
        if vix[e]['close'] > maximum_vix:
            maximum_vix = vix[e]['close']
        if vix[e]['close'] < minimum_vix:
            minimum_vix = vix[e]['close']
    return maximum_vix, minimum_vix


def create_dictionary_of_periods_when_holding_stock_vix_strategy(vix, comparison, vix_limit):
    list_of_comparison_keys = list(comparison.keys())
    number_of_buys = 0
    stock_holding = {}
    buy = False
    for e in vix:
        dictionary = comparison[e]
        if vix[e]['open'] <= vix_limit:
            
            if buy == False:
                dictionary['buy'] = "buy"
                buy = True
                number_of_buys += 1
            else:
                dictionary['buy'] = "hold"
            stock_holding[e] = dictionary

            if vix[e]['close'] > vix_limit:
                buy = False
                if stock_holding[e]['buy'] == "buy":
                    stock_holding[e]['buy'] = "buy and sell"
                else:
                    stock_holding[e]['buy'] = "sell at close"

        else:
            if buy == True:
                dictionary['buy'] = "sell"
                stock_holding[e] = dictionary
            buy = False
            
        if list_of_comparison_keys[-1] == e:
            if buy == True:
                dictionary['buy'] = "sell at close"
                stock_holding[e] = dictionary
            buy = False
            
    return stock_holding, number_of_buys


#######################
#
# CALC RETURNS BY DAY 
#
#######################

def return_values_as_close_to_desired_future_date_as_possible(daily_returns_dictionary, starting_timestamp, months_in_future, last_dictionary_value):
    #months_in_future -1 indicates last date in dictionary
    if months_in_future == -1:
        return daily_returns_dictionary[last_dictionary_value['timestamp']]

    time_in_future = datetime.datetime.fromtimestamp(starting_timestamp) + relativedelta(months=months_in_future)
    timestamp_in_future = time.mktime(datetime.datetime.strptime(str(time_in_future.year) + "-" + str(time_in_future.month) + "-" +  str(time_in_future.day), "%Y-%m-%d").timetuple())

    #find date as close to desired future date as possible (search backwards rather than forwards)
    found = False
    while found == False:
        if timestamp_in_future > last_dictionary_value['timestamp'] or timestamp_in_future <= starting_timestamp:
            return {'month': None, 'year': None, 'day': None, 'open': None, 'close': None}
    
        if timestamp_in_future in daily_returns_dictionary:
            return daily_returns_dictionary[timestamp_in_future]

        one_day_before = datetime.datetime.fromtimestamp(timestamp_in_future) + datetime.timedelta(days=-1)
        timestamp_in_future = time.mktime(datetime.datetime.strptime(str(one_day_before.year) + "-" + str(one_day_before.month) + "-" +  str(one_day_before.day), "%Y-%m-%d").timetuple())

    return {'month': None, 'year': None, 'day': None, 'open': None, 'close': None}
            

def create_list_of_returns(buy_and_hold_dictionary, daily_returns_dictionary):
    long_term_returns_by_day = {}
    open_value = 1
    #buy and hold is here only to provide complete list of dates (daily returns will only provide data for days when stock was held)
    last_dictionary_value = daily_returns_dictionary[(list(daily_returns_dictionary.keys())[-1])]
    for e in buy_and_hold_dictionary:
        try:
            open_value = daily_returns_dictionary[e]['open']
        except:
            pass
        
        one_month_values = return_values_as_close_to_desired_future_date_as_possible(daily_returns_dictionary, e, 1, last_dictionary_value)
        try:
            one_month_return = round(((one_month_values['close'] - open_value)/open_value), 4)
        except:
            one_month_return = None
        
        one_year_values = return_values_as_close_to_desired_future_date_as_possible(daily_returns_dictionary, e, 12, last_dictionary_value)
        try:
            one_year_return = round(((one_year_values['close'] - open_value)/open_value), 4)
        except:
            one_year_return = None
        
        five_year_values = return_values_as_close_to_desired_future_date_as_possible(daily_returns_dictionary, e, 60, last_dictionary_value)
        try:
            five_year_return = round(((five_year_values['close'] - open_value)/open_value), 4)
        except:
            five_year_return = None
        
        ten_year_values = return_values_as_close_to_desired_future_date_as_possible(daily_returns_dictionary, e, 120, last_dictionary_value)
        try:
            ten_year_return = round(((ten_year_values['close'] - open_value)/open_value), 4)
        except:
            ten_year_return = None
        
        furthest_values = return_values_as_close_to_desired_future_date_as_possible(daily_returns_dictionary, e, -1, last_dictionary_value)
        try:
            furthest_return = round(((furthest_values['close'] - open_value)/open_value), 4)
        except:
            furthest_return = None
            
        long_term_returns_by_day[e] = {'date': str(buy_and_hold_dictionary[e]['month']) + "-" + str(buy_and_hold_dictionary[e]['day']) + "-" + str(buy_and_hold_dictionary[e]['year']),
                                       'one_month': one_month_return,
                                       'one_year': one_year_return,
                                       'five_year': five_year_return,
                                       'ten_year': ten_year_return,
                                       'furthest_return': furthest_return} 

        try:
            open_value = daily_returns_dictionary[e]['close']
        except:
            pass
    return long_term_returns_by_day

#######################
#
# EXCEL FUNCTIONS
#
#######################



def create_daily_returns_and_print_to_excel(location_of_excel_folders, stock_holding_buy_and_hold, daily_returns_buy_and_hold, daily_returns_3x_buy_and_hold, daily_returns_3x_200_day, daily_returns_3x_vix, daily_returns_3x_combo):
    long_term_returns_by_day_buy_and_hold = create_list_of_returns(stock_holding_buy_and_hold, daily_returns_buy_and_hold)
    long_term_returns_by_day_buy_and_hold_3x = create_list_of_returns(stock_holding_buy_and_hold, daily_returns_3x_buy_and_hold)
    long_term_returns_by_day_200_day_3x = create_list_of_returns(stock_holding_buy_and_hold, daily_returns_3x_200_day)
    long_term_returns_by_day_vix_3x = create_list_of_returns(stock_holding_buy_and_hold, daily_returns_3x_vix)
    long_term_returns_by_day_combo_3x = create_list_of_returns(stock_holding_buy_and_hold, daily_returns_3x_combo)

    with xlsxwriter.Workbook(location_of_excel_folders + 'long_term_returns_by_day.xlsx') as workbook:
        
        for duration in ['one_month', 'one_year', 'five_year', 'ten_year', 'furthest_return']:
            list_to_write = [["Date", "Buy and Hold", "Buy and Hold 3x", "200 Day 3x", "VIX 3x", "Combo 3x"]]
            for e in long_term_returns_by_day_buy_and_hold:
                list_to_write.append([long_term_returns_by_day_buy_and_hold[e]['date'],
                                      long_term_returns_by_day_buy_and_hold[e][duration],
                                      long_term_returns_by_day_buy_and_hold_3x[e][duration],
                                      long_term_returns_by_day_200_day_3x[e][duration],
                                      long_term_returns_by_day_vix_3x[e][duration],
                                      long_term_returns_by_day_combo_3x[e][duration],
                                       ])
            worksheet = workbook.add_worksheet(duration)
            for row_num, data in enumerate(list_to_write):
                worksheet.write_row(row_num, 0, data)
                
    
#######################
#
# EXECUTE
#
#######################
    


comparison_stock = "QQQ" #this allows qqq, spy, tqqq, spxl 
vix_threshold = 18
location_of_excel_folders = "C:/Users/PC5/Desktop/vix_analysis/"
days_for_moving_average = 25
leverage_multiple = 3


vix = get_vix_data(location_of_excel_folders)
comparison = get_stock_data_from_excel(comparison_stock, location_of_excel_folders)
two_hundred_day_avg = calc_200_day_moving_average(comparison, days_for_moving_average)
    
#comparison = limit_stock_list_to_window_of_time(comparison, "2000-03-10", "2002-10-04") #Dot Com
#comparison = limit_stock_list_to_window_of_time(comparison, "2008-05-01", "2009-03-20") #Financial Crisis
#comparison = limit_stock_list_to_window_of_time(comparison, "2020-02-10", "2021-01-19") #Pandemic

#comparison = limit_stock_list_to_window_of_time(comparison, "2009-03-20", "2020-02-10") #Financial Crisis to Pandemic
#comparison = limit_stock_list_to_window_of_time(comparison, "2002-10-04", "2021-01-15") #End of Dot Com to Today
#comparison = limit_stock_list_to_window_of_time(comparison, "2010-02-11", "2021-01-15") #Since TQQQ was created
#comparison = limit_stock_list_to_window_of_time(comparison, "2000-03-10", "2021-01-15") #Beginning Dot Com to Today
#comparison = limit_stock_list_to_window_of_time(comparison, "2020-01-02", "2021-01-15") 



vix, comparison_limited_to_vix_dates = make_data_sets_the_same_dates(vix, comparison)


#BUY AND HOLD OVER ENTIRE PERIOD
stock_holding_buy_and_hold, number_of_buys_buy_and_hold = create_dictionary_of_periods_when_holding_stock_vix_strategy(vix, comparison_limited_to_vix_dates, 1000)
running_tally_buy_and_hold, running_tally_3x_buy_and_hold, returns_by_month_buy_and_hold, returns_by_month_3x_buy_and_hold, daily_returns_buy_and_hold, daily_returns_3x_buy_and_hold = calculate_return_of_stock_during_holding_periods(stock_holding_buy_and_hold, leverage_multiple)



#200 Day Average
stock_holding_200_day, number_of_buys_200_day = create_dictionary_of_periods_when_holding_stock_200_day_strategy(two_hundred_day_avg, comparison)
running_tally_200_day, running_tally_3x_200_day, returns_by_month_200_day, returns_by_month_3x_200_day, daily_returns_200_day, daily_returns_3x_200_day = calculate_return_of_stock_during_holding_periods(stock_holding_200_day, leverage_multiple)


#VIX
stock_holding_vix, number_of_buys_vix = create_dictionary_of_periods_when_holding_stock_vix_strategy(vix, comparison_limited_to_vix_dates, vix_threshold)
running_tally_vix, running_tally_3x_vix, returns_by_month_vix, returns_by_month_3x_vix, daily_returns_vix, daily_returns_3x_vix = calculate_return_of_stock_during_holding_periods(stock_holding_vix, leverage_multiple)

#COMBO
stock_holding_combo, number_of_buys_combo = create_dictionary_of_periods_when_holding_stock_combo_strategy(vix, two_hundred_day_avg, vix_threshold, comparison)
running_tally_combo, running_tally_3x_combo, returns_by_month_combo, returns_by_month_3x_combo, daily_returns_combo, daily_returns_3x_combo = calculate_return_of_stock_during_holding_periods(stock_holding_combo, leverage_multiple)


#write daily long term returns to excel
create_daily_returns_and_print_to_excel(location_of_excel_folders, stock_holding_buy_and_hold, daily_returns_buy_and_hold, daily_returns_3x_buy_and_hold, daily_returns_3x_200_day, daily_returns_3x_vix, daily_returns_3x_combo)


#######################
#
# REPORT
#
#######################


starting_data = ""
ending_data = ""
for e in comparison:
    if starting_data == "":
        starting_data = comparison[e]
    ending_data = comparison[e]

print("STARTING: " + str(starting_data['actual_day']) + ", " + str(starting_data['open']))
print()
print("ENDING: " + str(ending_data['actual_day']) + ", " + str(ending_data['close']))

print()
print("BUY AND HOLD RETURNS:")
print("DAYS IN THE MARKET: " + str(len(stock_holding_buy_and_hold)) + " OUT OF " + str(len(comparison)) + " DAYS")
print("NUMBER OF BUYS: " + str(number_of_buys_buy_and_hold))
print(comparison_stock + " non-leveraged returns: " + str(round(running_tally_buy_and_hold, 4)) + "x")
print(comparison_stock + " " + str(leverage_multiple) + "x leveraged returns: " + str(round(running_tally_3x_buy_and_hold, 4)) + "x")
print()
print()
print()

print("VIX RELATED RETURNS:")
print("DAYS IN THE MARKET: " + str(len(stock_holding_vix)) + " OUT OF " + str(len(comparison)) + " DAYS")
print("NUMBER OF BUYS: " + str(number_of_buys_vix))
print(comparison_stock + " non-leveraged returns: " + str(round(running_tally_vix, 4)) + "x")
print(comparison_stock + " " + str(leverage_multiple) + "x leveraged returns: " + str(round(running_tally_3x_vix, 4)) + "x")

print()
print()
print()
print(str(days_for_moving_average) + " DAY AVG RELATED RETURNS:")
print("DAYS IN THE MARKET: " + str(len(stock_holding_200_day)) + " OUT OF " + str(len(comparison)) + " DAYS")
print("NUMBER OF BUYS: " + str(number_of_buys_200_day))
print(comparison_stock + " non-leveraged returns: " + str(round(running_tally_200_day, 4)) + "x")
print(comparison_stock + " " + str(leverage_multiple) + "x leveraged returns: " + str(round(running_tally_3x_200_day, 4)) + "x")

print()
print()
print()
print("COMBO RETURNS:")
print("DAYS IN THE MARKET: " + str(len(stock_holding_combo)) + " OUT OF " + str(len(comparison)) + " DAYS")
print("NUMBER OF BUYS: " + str(number_of_buys_combo))
print(comparison_stock + " non-leveraged returns: " + str(round(running_tally_combo, 4)) + "x")
print(comparison_stock + " " + str(leverage_multiple) + "x leveraged returns: " + str(round(running_tally_3x_combo, 4)) + "x")



##print()
##print("RETURNS BY MONTH VIX STRATEGY")
##last_tally = 1
##last_tally_3x = 1
##for e in returns_by_month_vix:
##    value_for_month = round(((e[1] - last_tally)/last_tally)*100, 1)
##    value_for_month_3x = round(((e[2] - last_tally_3x)/last_tally_3x)*100, 1)
##    print(str(e[0]) + ":      " + str(value_for_month) + "%,     " + str(value_for_month_3x) + "%")
##    last_tally = e[1]
##    last_tally_3x = e[2]



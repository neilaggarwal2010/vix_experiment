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

def write_list_to_excel(list_to_write, location_of_excel_folders):
    with xlsxwriter.Workbook(location_of_excel_folders + 'test.xlsx') as workbook:
        worksheet = workbook.add_worksheet()

        for row_num, data in enumerate(list_to_write):
            worksheet.write_row(row_num, 0, data)   

def calculate_return_of_stock_during_holding_periods(stock_holding, leverage_multiple):
    last_month = 0
    last_year = 0
    
    returns_by_month = []
    returns_by_month_3x = []
    
    running_tally = 1
    running_tally_3x = 1
    
    last_price = -1
    for e in stock_holding:
        if last_price > -1 or stock_holding[e]['buy'] == "buy":
            if stock_holding[e]['buy'] == "buy" or stock_holding[e]['buy'] == "buy and sell":
                last_price = stock_holding[e]['open'] # - assume buy at open, should get intraday data and create a buffer
                #print()
                #print()
                #print(stock_holding[e]['buy'] + ": "  + stock_holding[e]['actual_day'] + ", " + str(stock_holding[e]['open']))
                
            if stock_holding[e]['buy'] == "sell":
                #assumes we sell as soon after open as possible - assuming immediate sell - should get intraday data and create a time buffer
                running_tally = running_tally * (1 + ((stock_holding[e]['open'] - last_price)/last_price))
                running_tally_3x = running_tally_3x * (1 + (((stock_holding[e]['open'] - last_price)/last_price)*leverage_multiple))
                #print(stock_holding[e]['buy'] + ": "  + stock_holding[e]['actual_day'] + ", " + str(stock_holding[e]['open']) + ", " + str((stock_holding[e]['open'] - last_price)/last_price) + ", " + str(running_tally))
                
            elif stock_holding[e]['buy'] == "buy and sell" or stock_holding[e]['buy'] == "sell at close":
                #assumes we sell shortly before close - assuming immediate sell - should get intraday data and create a time buffer
                running_tally = running_tally * (1 + ((stock_holding[e]['close'] - last_price)/last_price))
                running_tally_3x = running_tally_3x * (1 + (((stock_holding[e]['close'] - last_price)/last_price)*leverage_multiple))
                #print(stock_holding[e]['buy'] + ": "  + stock_holding[e]['actual_day'] + ", " + str(stock_holding[e]['close']) + ", " + str((stock_holding[e]['close'] - last_price)/last_price) + ", " + str(running_tally))
                
            else:
                running_tally = running_tally * (1 + ((stock_holding[e]['close'] - last_price)/last_price))
                running_tally_3x = running_tally_3x * (1 + (((stock_holding[e]['close'] - last_price)/last_price)*leverage_multiple))
                #print("HOLD: "  + stock_holding[e]['actual_day'] + ", " + str(stock_holding[e]['close']) + ", " + str((stock_holding[e]['close'] - last_price)/last_price) + ", " + str(running_tally))
                last_price = stock_holding[e]['close']


                
            if last_month == 0:
                last_month = stock_holding[e]['month']
            if last_month != stock_holding[e]['month']:
                returns_by_month.append([str(stock_holding[e]['month']) + "-" + str(stock_holding[e]['year']), running_tally, running_tally_3x])
                last_month = stock_holding[e]['month']
        

    return running_tally, running_tally_3x, returns_by_month, returns_by_month_3x

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
                                           'year': year})
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
            if comparison[e]['open'] >= two_hundred_day_avg[e] and vix[e]['open'] <= vix_threshold:

                if buy == False:
                    dictionary['buy'] = "buy"
                    buy = True
                    number_of_buys += 1
                else:
                    dictionary['buy'] = "hold"
                stock_holding[e] = dictionary

                if comparison[e]['close'] < two_hundred_day_avg[e] or vix[e]['close'] > vix_threshold:
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
# EXCEL FUNCTIONS
#
#######################




#######################
#
# EXECUTE
#
#######################
    


comparison_stock = "QQQ" #this allows qqq, spy, tqqq, spxl 
vix_threshold = 18
location_of_excel_folders = "C:/Users/PC5/Desktop/vix_analysis/"
days_for_moving_average = 200
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
running_tally_buy_and_hold, running_tally_3x_buy_and_hold, returns_by_month_buy_and_hold, returns_by_month_3x_buy_and_hold = calculate_return_of_stock_during_holding_periods(stock_holding_buy_and_hold, leverage_multiple)



#200 Day Average
stock_holding_200_day, number_of_buys_200_day = create_dictionary_of_periods_when_holding_stock_200_day_strategy(two_hundred_day_avg, comparison)
running_tally_200_day, running_tally_3x_200_day, returns_by_month_200_day, returns_by_month_3x_200_day = calculate_return_of_stock_during_holding_periods(stock_holding_200_day, leverage_multiple)


#VIX
stock_holding_vix, number_of_buys_vix = create_dictionary_of_periods_when_holding_stock_vix_strategy(vix, comparison_limited_to_vix_dates, vix_threshold)
running_tally_vix, running_tally_3x_vix, returns_by_month_vix, returns_by_month_3x_vix = calculate_return_of_stock_during_holding_periods(stock_holding_vix, leverage_multiple)

#COMBO
stock_holding_combo, number_of_buys_combo = create_dictionary_of_periods_when_holding_stock_combo_strategy(vix, two_hundred_day_avg, vix_threshold, comparison)
running_tally_combo, running_tally_3x_combo, returns_by_month_combo, returns_by_month_3x_combo = calculate_return_of_stock_during_holding_periods(stock_holding_combo, leverage_multiple)


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



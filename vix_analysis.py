import time
import datetime
import traceback
from xlrd import open_workbook
import xlrd
import xlsxwriter
from dateutil.relativedelta import relativedelta
from scipy import stats
import requests
import json
import dateutil.parser
import pandas
import pandas_datareader.data as web

#Four Classes/Sections: Assumptions, Metrics, Triggers, Combos, Returns
#Assumptions are the thresholds and values we use as the foundation of our strategies.  Simplest Example, we set the vix threshold to 18
#Metrics are the data that is required to determine whether a strategy is triggered.  Simplest Example, we need daily Vix data to assess whether we are over the vix threshold
#Triggers are a True/False value for each day to indicate whether we own or don't own the stock.  Simplest Example, for each day we are either above the vix (False) or below (True).
#Combos are essentially similar to Triggers, except combos takes various individual strategies and combine them whereas Triggers are single strategies.  Simple example, triggers is vix threshold strategy only, combos is vix threshold AND moving average strategy
#Returns takes the Trigger data and calculates the return for each strategy simulating a buy when the threshold is met and a sell when the threshold is not met

#side note, types of risk identified so far:
#1. Market Risk - risk the world market or the majority of the world's markets collapse 
#2. Government Risk - risk a particular country's market or set of countries' markets collapse
#3. Industry Risk - risk a particular industry or set of industries collapse 
#4. Company Risk - risk a particular company collapses
#5. Strategy Risk - risk your idea collapses 



#######################
#
# ASSUMPTIONS
#
#######################

class Assumptions():

    def __init__(self,
                 ignore_dividends = True,
                 excel_or_api = "alphavantage", #do you get stock data from a api or excel (e.g.market_stack, tiingo, alphavantage, excel)?
                                                         #Note - VIX defaults to marketstack, but will do excel if marketstack fails
                 market_stack_api_key = "bc68167928271e070e1fd49345cdfd6d", #make this an empty string before sharing with others
                 tiingo_api_key = "ae7d7add411168cb89685d7f4256d9bf0ce2c692",
                 alphavantage_api_key = "SCTCBSEBENCKWVM9",
                 location_of_excel_folders = "./vix_analysis/",
                 
                 stock = "QQQ",
                 leverage_multiple = 3,

                 rolling_stop_loss_threshold = 1.7, #percent, will sell intraday if stock loses more than amount.  Will always be treated as negative number
                 days_out_after_rolling_stop_loss_threshold_met = 1,

                 vix_low_threshold = 14,
                 vix_high_threshold = 18, 
                 vix_super_high_threshold = 30, #will buy when <= threshold.  we have multiple thresholds to allow for different levels of
                                                #scrutiny depending on vix level.
                 vix_astronomically_high_threshold = 40,
                 
                 days_for_moving_average_long = 50, 
                 days_for_moving_average_short = 10,
                 difference_between_long_and_short_moving_average_threshold = -3, #will buy when >= threshold

                 velocity_of_difference_between_long_and_short_moving_averages_threshold = 20, #percentiles, lower percentiles indicate short is quickly
                                                                                               #getting larger than long, buy when above threshold

                 moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_threshold = 0,
                 moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_days = 5,

                 days_for_percent_above_moving_average = 50,#number of days for moving average (which is the underlying metric for this calc)
                 percent_above_moving_average_threshold = 17,#any number here is a percent, .02 is .02%, will buy when x% of previous days was above moving avg
                 
                 vix_velocity_upper_threshold = 90,#percentiles, higher percentile translates to higher slope, will buy between both thresholds
                 vix_velocity_lower_threshold = 10, 
                 days_for_vix_velocity = 10,
                 days_out_after_significant_vix_velocity_move = 1,
                 
                 days_for_moving_avg_stock_velocity = 50,
                 moving_avg_stock_velocity_threshold = 0, #any number here is a percent, .02 is .02%, will buy when avg velocity is above x%
                 
                 days_for_avg_negative = 20,

                 days_for_rsi_calculation = 50, #RSI attempts to calculate when the market is overbought or oversold, high values = overbought, scale of 1-100
                 rsi_high_sell_threshold = 60,
                 rsi_low_sell_threshold = 50,):

        self.ignore_dividends = ignore_dividends
        self.tiingo_api_key = tiingo_api_key
        self.alphavantage_api_key = alphavantage_api_key
        self.excel_or_api = excel_or_api
        self.market_stack_api_key = market_stack_api_key
        self.location_of_excel_folders = location_of_excel_folders    
        self.stock = stock #this allows qqq, spy, tqqq, spxl
        self.leverage_multiple = leverage_multiple

        self.rolling_stop_loss_threshold = abs(rolling_stop_loss_threshold)
        self.days_out_after_rolling_stop_loss_threshold_met = days_out_after_rolling_stop_loss_threshold_met

        self.vix_low_threshold = vix_low_threshold
        self.vix_high_threshold = vix_high_threshold
        self.vix_super_high_threshold = vix_super_high_threshold
        self.vix_astronomically_high_threshold = vix_astronomically_high_threshold

        self.days_for_moving_average_long = days_for_moving_average_long
        self.days_for_moving_average_short = days_for_moving_average_short
        self.difference_between_long_and_short_moving_average_threshold = difference_between_long_and_short_moving_average_threshold

        self.velocity_of_difference_between_long_and_short_moving_averages_threshold = velocity_of_difference_between_long_and_short_moving_averages_threshold

        self.moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_threshold = moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_threshold
        self.moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_days = moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_days
        
        self.days_for_percent_above_moving_average = days_for_percent_above_moving_average
        self.percent_above_moving_average_threshold = percent_above_moving_average_threshold 

        self.vix_velocity_upper_threshold = vix_velocity_upper_threshold
        self.vix_velocity_lower_threshold = vix_velocity_lower_threshold
        self.days_for_vix_velocity = days_for_vix_velocity
        self.days_out_after_significant_vix_velocity_move = days_out_after_significant_vix_velocity_move

        self.days_for_moving_avg_stock_velocity = days_for_moving_avg_stock_velocity
        self.moving_avg_stock_velocity_threshold = moving_avg_stock_velocity_threshold 

        self.days_for_avg_negative = days_for_avg_negative

        self.days_for_rsi_calculation = days_for_rsi_calculation
        self.rsi_high_sell_threshold = rsi_high_sell_threshold
        self.rsi_low_sell_threshold = rsi_low_sell_threshold

#######################
#
# GENERAL FUNCTIONS
#
#######################

def excel_date(date1):
    temp = datetime.datetime(1899, 12, 30)    
    delta = date1 - temp
    return float(delta.days) + (float(delta.seconds) / 86400)

def get_last_item_in_dictionary_of_dictionaries(dictionary_of_dictionaries, key_value):
    return dictionary_of_dictionaries[list(dictionary_of_dictionaries.keys())[-1]][key_value]


#######################
#
# GET STOCK DATA
#
#######################

class LoadStock:

    class GeneralFunctions:
        
        def build_dictionary_of_single_day_data(self, year,
                                                month,
                                                day,
                                                timestamp,
                                                human_readable_date,
                                                stock_open,
                                                stock_close,
                                                stock_low = None,
                                                raw_open = None,
                                                raw_close = None,
                                                raw_low = None):
            if stock_open != "n/a":
                single_day_data = {'year': year,
                                   'month': month,
                                   'day': day,
                                   'timestamp': timestamp,
                                   'human_readable_date': human_readable_date,
                                   'open': stock_open,
                                   'close': stock_close,
                                   'low': stock_low,
                                   'raw_open': raw_open,
                                   'raw_close': raw_close,
                                   'raw_low': raw_low,
                                   }
                return single_day_data
            return None
        
        def extract_date_information_from_human_readable_date_string(self, date):
            date = dateutil.parser.parse(str(date))
            year = int(date.strftime("%Y"))
            month = int(date.strftime("%m"))
            day = int(date.strftime("%d"))
            human_readable_date = str(year) + "-" + str(month) + "-" +  str(day)
            timestamp = time.mktime(datetime.datetime.strptime(str(year) + "-" + str(date.strftime("%m")) + "-" +  str(date.strftime("%d")), "%Y-%m-%d").timetuple())
            return human_readable_date, year, month, day, timestamp

        def create_time_sorted_dictionary(self, data_list):
            temp_stock_data = {}
            data_list = sorted(data_list, key= lambda x: x['timestamp'])
            for ele in data_list:
                temp_stock_data[ele['human_readable_date']] = ele
            return temp_stock_data

    class AdjustStockPrice:
        
        def calculate_cash_dividend_adjustment_factor_by_date(self, stock, dividends):
            #See: https://blog.quandl.com/guide-to-stock-price-calculation
            adjustment_factor_by_date = {}
            aggregate_adjustment_factor = 1
            dividend = 0
            for date, data in sorted(dividends.items(), key=lambda x:x[1]['timestamp'], reverse=True):
                
                #adjustment factor is applied to previous day, this is at the top to implement that requirement (remember, we are looping through a reversed dictionary)
                adjustment = (stock[date]['raw_close'] - dividend)/stock[date]['raw_close']
                aggregate_adjustment_factor = adjustment * aggregate_adjustment_factor
                adjustment_factor_by_date[date] = aggregate_adjustment_factor

                dividend = data['value']
                
            return adjustment_factor_by_date

        def calculate_split_adjustment_factor_by_date(self, stock, splits):
            #See: https://blog.quandl.com/guide-to-stock-price-calculation
            adjustment_factor_by_date = {}
            aggregate_adjustment_factor = 1
            split = 1
            for date, data in sorted(splits.items(), key=lambda x:x[1]['timestamp'], reverse=True):
                
                #adjustment factor is applied to previous day, this is at the top to implement that requirement (remember, we are looping through a reversed dictionary)
                adjustment = 1/split
                aggregate_adjustment_factor = adjustment * aggregate_adjustment_factor
                adjustment_factor_by_date[date] = aggregate_adjustment_factor
                
                split = data['value']
                
            return adjustment_factor_by_date

        def calculate_adjusted_value_by_date(self, stock, aggregate_splits, aggregate_dividends, key):
            for date in stock:
                aggregate_split_adjustment_factor = aggregate_splits[date]
                aggregate_dividend_adjustment_factor = aggregate_dividends[date]

                item = stock[date]["raw_" + key]

                adjusted_value = item * aggregate_split_adjustment_factor * aggregate_dividend_adjustment_factor 

                stock[date][key] = adjusted_value
                
            return stock

        def alter_adjusted_price_to_ignore_dividends(self, stock, aggregate_dividends, key):
            try: #if key is "low", not all apis provide low (ex. we did not include low in the excel sheets in the beginning)
                for date in stock:
                    stock[date][key] = stock[date][key]/aggregate_dividends[date]
            except:
                pass
            return stock
        
    class FromExcel:

        def __init__(self):
            self.stock = {}
        
        def get_sheet_from_excel(self, Assumptions, file_name):
            book = open_workbook(Assumptions.location_of_excel_folders + file_name)
            sheet = book.sheet_by_index(0)
            return book, sheet

        def convert_excel_date_to_component_parts(self, book, excel_date):
            book_datemode = book.datemode
            year, month, day, hour, minute, second = xlrd.xldate_as_tuple(excel_date, book.datemode)
            timestamp = time.mktime(datetime.datetime.strptime(str(year) + "-" + str(month) + "-" +  str(day), "%Y-%m-%d").timetuple())
            human_readable_date = str(year) + "-" + str(month) + "-" +  str(day)
            return year, month, day, hour, minute, second, human_readable_date, timestamp

        def extract_one_row_of_stock_data(self, book, row):
            stock_open = row[1].value
            stock_close = row[2].value
            excel_date = row[0].value
            year, month, day, hour, minute, second, human_readable_date, timestamp = self.convert_excel_date_to_component_parts(book, excel_date)
            return LoadStock().GeneralFunctions().build_dictionary_of_single_day_data(year, month, day, timestamp, human_readable_date, stock_open, stock_close)

        def get_data(self, Assumptions):
            book, sheet = self.get_sheet_from_excel(Assumptions, Assumptions.stock + ".xls")
            counter = 0
            for row in sheet:
                if counter > 0:
                    single_day_data = self.extract_one_row_of_stock_data(book, row)
                    if single_day_data != None:
                        self.stock[single_day_data['human_readable_date']] = single_day_data
                counter += 1
            return self.stock
    
    class FromMarketStack:

        def __init__(self):
            self.stock = {}
            
        def extract_single_row_of_market_stack_data(self, row):
            date = dateutil.parser.parse(row['date'])
            year = int(date.strftime("%Y"))
            month = int(date.strftime("%m"))
            day = int(date.strftime("%d"))
            human_readable_date = str(year) + "-" + str(month) + "-" +  str(day)
            timestamp = time.mktime(datetime.datetime.strptime(str(year) + "-" + str(date.strftime("%m")) + "-" +  str(date.strftime("%d")), "%Y-%m-%d").timetuple())

            if row['adj_open'] == None and row['close'] == row['adj_close']:
                stock_open = row['open']
            else:
                stock_open = row['adj_open']
                
            stock_close = row['adj_close']            
            row_dictionary = LoadStock().GeneralFunctions().build_dictionary_of_single_day_data(year,
                                                                                                month,
                                                                                                day,
                                                                                                timestamp,
                                                                                                human_readable_date,
                                                                                                stock_open,
                                                                                                stock_close,
                                                                                                stock_low = row['adj_low'],
                                                                                                raw_open = row['open'],
                                                                                                raw_close = row['close'],
                                                                                                raw_low = row['low'],)
            return row_dictionary
        
        def get_data(self, Assumptions, ticker):
            stock_list = []
            number_of_records_per_api_call = 1000 #max is 1000 for market stack
            params = {'access_key': Assumptions.market_stack_api_key,
                      'limit': number_of_records_per_api_call}
            offset = 0
            total = 1

            while offset < total + number_of_records_per_api_call:
                params['offset'] = offset
                api_result = requests.get('https://api.marketstack.com/v1/tickers/'+ ticker + '/eod', params)
                api_response = api_result.json()

                offset = api_response['pagination']['offset']
                total = api_response['pagination']['total']
                
                for stock_data in api_response['data']['eod']:
                    stock_list.append(self.extract_single_row_of_market_stack_data(stock_data))
                    
                offset += number_of_records_per_api_call

            prices_by_time = sorted(stock_list, key= lambda x: x['timestamp'])

            self.stock = LoadStock().GeneralFunctions().create_time_sorted_dictionary(prices_by_time)

            return self.stock
            
    class FromTiingo:
        
        def __init__(self):
            self.stock = {}

        def add_stock_data(self, data_type, api_data, key, human_readable_date):
            if data_type == 'adjOpen':
                self.stock[human_readable_date]['open'] = api_data[data_type][key]
            elif data_type == 'adjClose':
                self.stock[human_readable_date]['close'] = api_data[data_type][key]
            elif data_type == 'adjLow':
                self.stock[human_readable_date]['low'] = api_data[data_type][key]
            elif data_type == 'open':
                self.stock[human_readable_date]['raw_open'] = api_data[data_type][key]
            elif data_type == 'close':
                self.stock[human_readable_date]['raw_close'] = api_data[data_type][key]
            elif data_type == 'low':
                self.stock[human_readable_date]['raw_low'] = api_data[data_type][key]
            return self.stock

        def convert_tiingo_dictionary_into_date_value_dictionary(self, tiingo_dictionary):
            data_list = []
            for tiingo_date in tiingo_dictionary:
                human_readable_date, year, month, day, timestamp = LoadStock().GeneralFunctions().extract_date_information_from_human_readable_date_string(tiingo_date[1])
                data_list.append({'human_readable_date': human_readable_date, 'timestamp': timestamp, 'value': tiingo_dictionary[tiingo_date]})

            dictionary = LoadStock().GeneralFunctions().create_time_sorted_dictionary(data_list)
            return dictionary
                                                                                                                                        
        
        def get_data(self, Assumptions, ticker):
            ticker = Assumptions.stock
            data = web.DataReader(ticker.upper(), 'tiingo', start="1899-1-1", api_key=Assumptions.tiingo_api_key)
            api_format_data = data.to_dict()
                
            data_types = ['open', 'close', 'low', 'adjOpen', 'adjClose', 'adjLow']
            for data_type in data_types:
                for ele in api_format_data[data_type]:
                    human_readable_date, year, month, day, timestamp = LoadStock().GeneralFunctions().extract_date_information_from_human_readable_date_string(ele[1])
                    if human_readable_date not in self.stock:
                        self.stock[human_readable_date] = {'year': year,
                                                           'month': month,
                                                           'day': day,
                                                           'timestamp': timestamp,
                                                           'human_readable_date': human_readable_date}
                        
                    self.stock = self.add_stock_data(data_type, api_format_data, ele, human_readable_date)

            dividends = self.convert_tiingo_dictionary_into_date_value_dictionary(api_format_data['divCash'])
            dividend_adjustment_factor_by_day = LoadStock().AdjustStockPrice().calculate_cash_dividend_adjustment_factor_by_date(self.stock, dividends)

            splits = self.convert_tiingo_dictionary_into_date_value_dictionary(api_format_data['splitFactor'])
            split_adjustment_factor_by_day = LoadStock().AdjustStockPrice().calculate_split_adjustment_factor_by_date(self.stock, splits)

            if Assumptions.ignore_dividends:
                self.stock = LoadStock().AdjustStockPrice().alter_adjusted_price_to_ignore_dividends(self.stock, dividend_adjustment_factor_by_day, "close")
                self.stock = LoadStock().AdjustStockPrice().alter_adjusted_price_to_ignore_dividends(self.stock, dividend_adjustment_factor_by_day, "open")
                self.stock = LoadStock().AdjustStockPrice().alter_adjusted_price_to_ignore_dividends(self.stock, dividend_adjustment_factor_by_day, "low")
            
            return self.stock

    class FromAlphaVantage:
        
        def __init__(self):
            self.stock = {}

        
        def get_data(self, Assumptions, ticker):
            url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=%s&apikey=%s&outputsize=full"%(ticker, Assumptions.alphavantage_api_key,)

            json_response = requests.get(url).json()
            data = json_response['Time Series (Daily)']

            prices_by_time = []
            dividends = []
            splits = []
            for date in data:

                human_readable_date, year, month, day, timestamp = LoadStock().GeneralFunctions().extract_date_information_from_human_readable_date_string(date)
                try:
                    
                    dividends.append({'timestamp': timestamp, 'human_readable_date': human_readable_date, 'value': float(data[date]['7. dividend amount'])})
                    splits.append({'timestamp': timestamp, 'human_readable_date': human_readable_date, 'value': float(data[date]['8. split coefficient'])})

                    prices_by_time.append({'year': year,
                                           'month': month,
                                           'day': day,
                                           'timestamp': timestamp,
                                           'human_readable_date': human_readable_date,
                                           'raw_open': float(data[date]['1. open']),
                                           'raw_close': float(data[date]['4. close']),
                                           'raw_low':  float(data[date]['3. low']),
                                           'close': float(data[date]['5. adjusted close']),}) #get rid of adjusted close after expiriment is over
                except:
                    print(traceback.format_exc())

            self.stock = LoadStock().GeneralFunctions().create_time_sorted_dictionary(prices_by_time)
            
            dividends = LoadStock().GeneralFunctions().create_time_sorted_dictionary(dividends)
            dividend_adjustment_factor_by_day = LoadStock().AdjustStockPrice().calculate_cash_dividend_adjustment_factor_by_date(self.stock, dividends)
            
            splits = LoadStock().GeneralFunctions().create_time_sorted_dictionary(splits)
            split_adjustment_factor_by_day = LoadStock().AdjustStockPrice().calculate_split_adjustment_factor_by_date(self.stock, splits)

            self.stock = LoadStock().AdjustStockPrice().calculate_adjusted_value_by_date(self.stock, split_adjustment_factor_by_day, dividend_adjustment_factor_by_day, "low")
            self.stock = LoadStock().AdjustStockPrice().calculate_adjusted_value_by_date(self.stock, split_adjustment_factor_by_day, dividend_adjustment_factor_by_day, "open")

            if Assumptions.ignore_dividends:
                self.stock = LoadStock().AdjustStockPrice().alter_adjusted_price_to_ignore_dividends(self.stock, dividend_adjustment_factor_by_day, "close")
                self.stock = LoadStock().AdjustStockPrice().alter_adjusted_price_to_ignore_dividends(self.stock, dividend_adjustment_factor_by_day, "open")
                self.stock = LoadStock().AdjustStockPrice().alter_adjusted_price_to_ignore_dividends(self.stock, dividend_adjustment_factor_by_day, "low")
            return self.stock

        
    def load_stock(self, Assumptions, ticker):
        try:
            if Assumptions.excel_or_api == "tiingo":
                stock = self.FromTiingo().get_data(Assumptions, ticker)
                    
            elif Assumptions.excel_or_api == "market_stack":
                stock = self.FromMarketStack().get_data(Assumptions, ticker)

            elif Assumptions.excel_or_api == "alphavantage":
                stock = self.FromAlphaVantage().get_data(Assumptions, ticker)

            elif Assumptions.excel_or_api == "excel":
                stock = self.FromExcel().get_data(Assumptions)
                
        except:
            print(traceback.format_exc())
            stock = self.FromExcel().get_data(Assumptions)

        return stock


        
#######################
#
# METRICS 
#
#######################


class Metrics:

    def __init__(self, Assumptions, stock):
        self.LoadStock = LoadStock()
        self.vix = self.GetVixData().load_vix_data(Assumptions)
##        for e in self.vix:
##            print(e)
##            print(self.vix[e])
##        for e in stock:
##            print(e)
##            print(stock[e])
##            print(self.vix[e])
        self.moving_average_by_day_of_stock_price_long = self.calc_moving_avg_of_stock_price_by_day(stock, Assumptions.days_for_moving_average_long)
        self.moving_average_by_day_of_stock_price_short = self.calc_moving_avg_of_stock_price_by_day(stock, Assumptions.days_for_moving_average_short)
        self.moving_average_stock_velocity_by_day = self.calc_moving_avg_of_daily_stock_velocity_by_day(stock, Assumptions)
        self.vix_velocity_moving_average_by_day = self.calc_vix_velocity_moving_average_by_day(Assumptions, self.vix )
        self.percent_above_moving_average = self.calc_percent_of_days_above_moving_average(stock, Assumptions)
        self.velocity_of_difference_between_long_and_short_moving_averages = self.calc_velocity_of_difference_between_long_and_short_moving_averages(Assumptions, self.moving_average_by_day_of_stock_price_long, self.moving_average_by_day_of_stock_price_short)
        self.rsi_by_day = self.CalcRSI().calc_rsi(Assumptions, stock)
        self.moving_avg_of_velocity_of_difference_between_long_and_short_moving_avgs_by_day = self.calc_moving_avg_of_difference_between_long_and_short_moving_avgs(Assumptions, self.moving_average_by_day_of_stock_price_long, self.moving_average_by_day_of_stock_price_short)

    class GetVixData:
        
        def __init__(self):
            self.vix = {}
            
        def extract_one_row_of_vix_data(self, book, row):
            vix_open = row[1].value
            vix_close = row[4].value
            excel_date = row[0].value
            year, month, day, hour, minute, second, human_readable_date, timestamp = LoadStock().FromExcel().convert_excel_date_to_component_parts(book, excel_date)
            return LoadStock().GeneralFunctions().build_dictionary_of_single_day_data(year, month, day, timestamp, human_readable_date, vix_open, vix_close)

        def from_excel(self, Assumptions):
            book, sheet = LoadStock().FromExcel().get_sheet_from_excel(Assumptions, "vix.xls")
            counter = 0
            for row in sheet:
                if counter > 0:
                    single_day_data = self.extract_one_row_of_vix_data(book, row)
                    if single_day_data != None:
                        self.vix[single_day_data['human_readable_date']] = single_day_data
                counter += 1
            return self.vix
        
        def load_vix_data(self, Assumptions):
            try:
                self.vix = LoadStock().FromMarketStack().get_data(Assumptions, "vix.indx")
            except:
                print(traceback.format_exc())
                self.vix = self.from_excel(Assumptions)
            return self.vix

    class CalcRSI:
        
        def __init__(self):
            self.rsi_by_day = {}
    
        def adjust_average(self, up_or_down, average, days, current):
            if days - 1 > 0:
                if (current > 0 and up_or_down == "gain") or (current <= 0 and up_or_down == "loss"):
                    return ((average * (days-1)) + abs(current))/days
                else:
                    return average
            raise        

        def calc_avg_gain_and_loss(self, Assumptions, stock_change_values):
            gain = 0
            days_up_count = 0
            loss = 0
            days_down_count = 0

            for day_change in stock_change_values[Assumptions.days_for_rsi_calculation * -1:]:
                if day_change > 0:
                    gain += abs(day_change)
                    days_up_count += 1
                else:
                    loss += abs(day_change)
                    days_down_count += 1

            avg_gain = gain/days_up_count
            avg_loss = loss/days_down_count
            
            return avg_gain, avg_loss, days_up_count, days_down_count
        
        def calc_rsi(self, Assumptions, stock):
            stock_change_values = []
            days = 0

            last_price = False
            rsi = False
            
            for date in stock:
                try:
                    if rsi is not False:
                        self.rsi_by_day[date] = rsi
                        
                    if days >= Assumptions.days_for_rsi_calculation:
                        avg_gain, avg_loss, days_up_count, days_down_count = self.calc_avg_gain_and_loss(Assumptions, stock_change_values)

                        current_change = stock[date]['close'] - last_price
                        adjusted_avg_gain = self.adjust_average("gain", avg_gain, days_up_count, current_change)
                        adjusted_avg_loss = self.adjust_average("loss", avg_loss, days_down_count, current_change)

                        rs = adjusted_avg_gain/float(adjusted_avg_loss)
                        rsi = 100 - (100/(1+rs))
                except:
                    self.rsi_by_day[date] = None
                    
                if last_price is not False:
                    stock_change_values.append(stock[date]['close'] - last_price)

                last_price = round(stock[date]['close'], 2)
                days += 1
            return self.rsi_by_day

    def calc_velocity_of_difference_between_long_and_short_moving_averages(self, Assumptions, long_moving_average, short_moving_average):
        velocity_of_difference_between_long_and_short_moving_averages_by_day = {}
        velocity_values = []

        last_price = False

        for date in long_moving_average:
            if date in long_moving_average and date in short_moving_average and short_moving_average[date] != None and long_moving_average[date] != None:
                if last_price != False:
                    difference = long_moving_average[date] - short_moving_average[date]
                    velocity = (difference - last_price)/last_price
                    velocity_of_difference_between_long_and_short_moving_averages_by_day[date] = velocity
                    if velocity < 0:
                        velocity_values.append(velocity)
                last_price = long_moving_average[date] - short_moving_average[date]

        #convert velocity to percentiles
        percentiles = [stats.percentileofscore(velocity_values, a, 'strict') for a in velocity_values]

        #replace velocity with percentile score
        for date in velocity_of_difference_between_long_and_short_moving_averages_by_day:
            try:
                if velocity_of_difference_between_long_and_short_moving_averages_by_day[date] in velocity_values:
                    velocity_of_difference_between_long_and_short_moving_averages_by_day[date] = percentiles[velocity_values.index(velocity_of_difference_between_long_and_short_moving_averages_by_day[date])]
                else:
                    velocity_of_difference_between_long_and_short_moving_averages_by_day[date] = 100
            except:
                pass
        return velocity_of_difference_between_long_and_short_moving_averages_by_day

    def calc_moving_avg_of_difference_between_long_and_short_moving_avgs(self, Assumptions, long_moving_average, short_moving_average):
        moving_avg_of_velocity_of_difference_between_long_and_short_moving_avgs_by_day = {}
        velocity_values = []
        days= 0

        last_price = False
        for date in long_moving_average:
            if date in long_moving_average and date in short_moving_average and short_moving_average[date] != None and long_moving_average[date] != None:
                
                if days >= Assumptions.moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_days:
                    sum_of_velocities = sum(velocity_values[-1*Assumptions.moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_days:])
                    average = sum_of_velocities/Assumptions.moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_days
                    moving_avg_of_velocity_of_difference_between_long_and_short_moving_avgs_by_day[date] = average
                    
                if last_price != False:
                    difference = long_moving_average[date] - short_moving_average[date]
                    velocity = difference - last_price
                    velocity_values.append(velocity)
                last_price = long_moving_average[date] - short_moving_average[date]

                days += 1
        return moving_avg_of_velocity_of_difference_between_long_and_short_moving_avgs_by_day        

    def calc_vix_velocity_moving_average_by_day(self, Assumptions, vix):
        vix_velocity_moving_average_by_day = {}
        vix_velocity_moving_average_values = []
        vix_velocity_values = []
        days = 0
        
        last_price = False

        #calculate vix velocity for each day
        for date in vix:
            if days >= Assumptions.days_for_vix_velocity and last_price is not False:

                    sum_of_velocity_values = sum(vix_velocity_values[-1*Assumptions.days_for_vix_velocity:])
                    vix_velocity_average = sum_of_velocity_values/Assumptions.days_for_vix_velocity
                    
                    vix_velocity_moving_average_by_day[date] = vix_velocity_average
                    
                    vix_velocity_moving_average_values.append(vix_velocity_average)
                    vix_velocity_values.append((vix[date]['close'] - last_price)/last_price)
            else:
                vix_velocity_moving_average_by_day[date] = None

            last_price = vix[date]['close']
            days += 1

        #convert vix velocity to percentiles
        percentiles = [stats.percentileofscore(vix_velocity_moving_average_values, a, 'strict') for a in vix_velocity_moving_average_values]

        #replace vix velocity with percentile score
        for date in vix_velocity_moving_average_by_day:
            try:
                if vix_velocity_moving_average_by_day[date] in vix_velocity_moving_average_values:
                    position_of_percentile_value = vix_velocity_moving_average_values.index(vix_velocity_moving_average_by_day[date])
                    vix_velocity_moving_average_by_day[date] = percentiles[position_of_percentile_value]
            except:
                pass
        return vix_velocity_moving_average_by_day

    def calc_percent_of_days_above_moving_average(self, stock, Assumptions):
        percent_above_moving_average = {}
        moving_average_by_day = self.calc_moving_avg_of_stock_price_by_day(stock, Assumptions.days_for_percent_above_moving_average)

        tally_of_days_above_and_below = []

        for date in stock:
            try:
                days_above_moving_average = 0
                for above in tally_of_days_above_and_below[Assumptions.days_for_percent_above_moving_average * -1:]:
                    if above:
                        days_above_moving_average += 1

                percent_above_moving_average[date] = days_above_moving_average/Assumptions.days_for_percent_above_moving_average
                
                if date in moving_average_by_day:
                    if stock[date]['open'] > moving_average_by_day[date]:
                        tally_of_days_above_and_below.append(True)
                    else:
                        tally_of_days_above_and_below.append(False)
            except:
                percent_above_moving_average[date] = None
        return percent_above_moving_average

    def calc_moving_avg_of_daily_stock_velocity_by_day(self, stock, Assumptions):
        moving_average_stock_velocity_by_day = {}
        stock_velocity_values = []
        days = 0
        last_price = False
        
        for date in stock:
            if last_price is not False:
                sum_of_stock_velocity_values = 0
                if days >= Assumptions.days_for_moving_avg_stock_velocity:
                    sum_of_stock_velocity_values =  sum(stock_velocity_values[-1*Assumptions.days_for_moving_avg_stock_velocity:])
                    moving_average_stock_velocity_by_day[date] = sum_of_stock_velocity_values/Assumptions.days_for_moving_avg_stock_velocity
                else:
                    moving_average_stock_velocity_by_day[date] = None
                stock_velocity_values.append((stock[date]['close']-last_price)/last_price)
            last_price = stock[date]['close']
            days += 1
        return moving_average_stock_velocity_by_day    

    def calc_moving_avg_of_stock_price_by_day(self, stock, days_for_moving_average):
        moving_average_by_day = {}
        stock_values = []
        days = 0
        for date in stock:
            sum_of_stock_values = 0
            if days >= days_for_moving_average:
                sum_of_stock_values = sum(stock_values[-1*days_for_moving_average:])
                moving_average_by_day[date] = sum_of_stock_values/days_for_moving_average
            else:
                moving_average_by_day[date] = None
            stock_values.append(stock[date]['close'])
            days += 1
        return moving_average_by_day
#######################
#
# TRIGGERS 
#
#######################



class Triggers:

    def __init__(self, Assumptions, stock, Metrics):
        self.buy_and_hold = self.buy_and_hold(stock)
        self.vix_position_below_high_threshold = self.check_whether_vix_is_below_threshold_by_day(Metrics, Assumptions.vix_high_threshold)
        self.vix_position_below_low_threshold = self.check_whether_vix_is_below_threshold_by_day(Metrics, Assumptions.vix_low_threshold)
        self.vix_position_below_super_high_threshold = self.check_whether_vix_is_below_threshold_by_day(Metrics, Assumptions.vix_super_high_threshold)
        self.vix_position_below_astronomically_high_threshold = self.check_whether_vix_is_below_threshold_by_day(Metrics, Assumptions.vix_astronomically_high_threshold)
        self.stock_price_above_moving_average_long = self.check_whether_daily_stock_price_is_above_moving_average(stock,
                                                                                                             Metrics.moving_average_by_day_of_stock_price_long)
        self.stock_price_above_moving_average_short = self.check_whether_daily_stock_price_is_above_moving_average(stock,
                                                                                                              Metrics.moving_average_by_day_of_stock_price_short)
        self.moving_avg_stock_velocity_above_threshold = self.check_whether_moving_avg_stock_velocity_is_above_threshold(Assumptions, Metrics)
        self.difference_between_long_and_short_moving_avg_above_threshold = self.check_whether_difference_between_long_and_short_stock_moving_avgs_above_threshold(Assumptions, Metrics)
        self.vix_velocity_between_thresholds = self.check_whether_vix_velocity_is_between_thresholds(Assumptions, Metrics)
        self.percent_of_days_above_moving_average_above_threshold = self.check_whether_percent_of_days_above_moving_average_is_above_threshold(Assumptions, Metrics)
        self.velocity_of_difference_between_long_and_short_below_threshold = self.check_whether_velocity_of_difference_between_long_and_short_below_threshold(Assumptions, Metrics)
        self.rsi_below_high_sell_threshold = self.check_whether_rsi_is_below_threshold(Metrics, Assumptions.rsi_high_sell_threshold)
        self.rsi_below_low_sell_threshold = self.check_whether_rsi_is_below_threshold(Metrics, Assumptions.rsi_low_sell_threshold)

    def buy_and_hold(self, stock):
        buy_and_hold_triggers = {}
        for date in stock:
            buy_and_hold_triggers[date] = {'open': True}
        return buy_and_hold_triggers

    def check_whether_vix_is_below_threshold_by_day(self, Metrics, vix_threshold):
        vix_position_below_treshold = {}
        for date in Metrics.vix:
            
            vix_position_below_treshold[date] = {'open': False, 'close': False}
            if Metrics.vix[date]['open'] <= vix_threshold:
                vix_position_below_treshold[date]['open'] = True
                
            if Metrics.vix[date]['close'] <= vix_threshold:
                vix_position_below_treshold[date]['close'] = True
                
        return vix_position_below_treshold

    def check_whether_vix_velocity_is_between_thresholds(self, Assumptions, Metrics):
        days_out = False
        vix_velocity_between_thresholds = {}
        for date in Metrics.vix_velocity_moving_average_by_day:
            if Metrics.vix_velocity_moving_average_by_day[date] != None:
                vix_velocity_between_thresholds[date] = {'open': False}

                if days_out >= Assumptions.days_out_after_significant_vix_velocity_move:
                    days_out = False

                if Assumptions.vix_velocity_lower_threshold <= Metrics.vix_velocity_moving_average_by_day[date] <= Assumptions.vix_velocity_upper_threshold:
                    if days_out == False:
                        vix_velocity_between_thresholds[date]['open'] = True
                    else:
                        days_out += 1
                else:
                    days_out = 1
 
                
        return vix_velocity_between_thresholds

    def check_whether_percent_of_days_above_moving_average_is_above_threshold(self, Assumptions, Metrics):
        percent_of_days_above_moving_average_above_threshold = {}
        for date in Metrics.percent_above_moving_average:
            if Metrics.percent_above_moving_average[date] != None:
                percent_of_days_above_moving_average_above_threshold[date] = {'open': False}

                if Metrics.percent_above_moving_average[date] * 100 >= Assumptions.percent_above_moving_average_threshold:
                    percent_of_days_above_moving_average_above_threshold[date]['open'] = True
                    
        return percent_of_days_above_moving_average_above_threshold


    def check_whether_moving_avg_stock_velocity_is_above_threshold(self, Assumptions, Metrics):
        moving_avg_stock_velocity_above_threshold = {}
        for date in Metrics.moving_average_stock_velocity_by_day:
            if Metrics.moving_average_stock_velocity_by_day[date] != None:
                moving_avg_stock_velocity_above_threshold[date] = {'open': False}

                if Metrics.moving_average_stock_velocity_by_day[date] >= Assumptions.moving_avg_stock_velocity_threshold:
                    moving_avg_stock_velocity_above_threshold[date]['open'] = True
                    
                
        return moving_avg_stock_velocity_above_threshold    

    def check_whether_daily_stock_price_is_above_moving_average(self, stock, moving_average_by_day):
        stock_price_is_above_moving_average = {}
        for date in moving_average_by_day:
            if moving_average_by_day[date] != None and date in stock:
                
                stock_price_is_above_moving_average[date] = {'open': False, 'close': False}
                
                if stock[date]['open'] >= moving_average_by_day[date]:
                    stock_price_is_above_moving_average[date]['open'] = True
     
                if stock[date]['close'] >= moving_average_by_day[date]:
                    stock_price_is_above_moving_average[date]['close'] = True

        return stock_price_is_above_moving_average    

    def check_whether_difference_between_long_and_short_stock_moving_avgs_above_threshold(self, Assumptions, Metrics):
        difference_between_long_and_short_moving_avg_above_threshold = {}
        
        for date in Metrics.moving_average_by_day_of_stock_price_long:
            if Metrics.moving_average_by_day_of_stock_price_long[date] != None and Metrics.moving_average_by_day_of_stock_price_short[date] != None:
                
                difference_between_long_and_short_moving_avg_above_threshold[date] = {'open': False}
                
                long_moving_average = Metrics.moving_average_by_day_of_stock_price_long[date]
                short_moving_average = Metrics.moving_average_by_day_of_stock_price_short[date]
                
                difference_between_moving_averages = long_moving_average - short_moving_average
                
                if difference_between_moving_averages >= Assumptions.difference_between_long_and_short_moving_average_threshold:
                    difference_between_long_and_short_moving_avg_above_threshold[date]['open'] = True

        return difference_between_long_and_short_moving_avg_above_threshold    

    def check_whether_velocity_of_difference_between_long_and_short_below_threshold(self, Assumptions, Metrics):
        velocity_of_difference_between_long_and_short_below_threshold = {}
        
        for date in Metrics.velocity_of_difference_between_long_and_short_moving_averages:
                
                velocity_of_difference_between_long_and_short_below_threshold[date] = {'open': False}

                
                if Metrics.velocity_of_difference_between_long_and_short_moving_averages[date] >= Assumptions.velocity_of_difference_between_long_and_short_moving_averages_threshold:
                    velocity_of_difference_between_long_and_short_below_threshold[date]['open'] = True

        return velocity_of_difference_between_long_and_short_below_threshold

                #REFERENCE FOR BELOW
                 #moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_threshold = 0,
                 #moving_average_of_velocity_of_difference_between_long_and_short_moving_avg_days = 10,

                 #FINISH THIS
##    def check_whether_moving_avg_of_difference_between_long_and_short_below_threshold(self, Assumptions, Metrics):
##        moving_avg_velocity_of_difference_between_long_and_short_below_threshold = {}
##
##        for date in Metrics.moving_avg_of_velocity_of_difference_between_long_and_short_moving_avgs_by_day:
##            moving_avg_velocity_of_difference_between_long_and_short_below_threshold = {'open': False}
##
##            if Metrics.moving_avg_of_velocity_of_difference_between_long_and_short_moving_avgs_by_day[date] <
            

    def check_whether_rsi_is_below_threshold(self, Metrics, rsi_sell_threshold):
        rsi_below_threshold = {}
        for date in Metrics.rsi_by_day:
            if Metrics.rsi_by_day[date] != None:
                rsi_below_threshold[date] = {'open': False}
                if Metrics.rsi_by_day[date] <= rsi_sell_threshold:
                    rsi_below_threshold[date]['open'] = True
        return rsi_below_threshold
                    
#######################
#
# COMBOS
#
#######################

class Combos:

    def __init__(self, Triggers):
        self.combo_1 = self.combo_1(Triggers)
        self.combo_2 = self.combo_2(Triggers)
        self.combo_3 = self.combo_3(Triggers)
        self.combo_4 = self.combo_4(Triggers)
        self.combo_5 = self.combo_5(Triggers)
        self.combo_6 = self.combo_6(Triggers)
        self.combo_7 = self.combo_7(Triggers)
        self.combo_8 = self.combo_8(Triggers)
        self.combo_9 = self.combo_9(Triggers)

    def combo_9(self, Triggers):
        combo_9_by_day = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold and date in Triggers.rsi_below_high_sell_threshold:

                combo_9_by_day[date] = {'open': False}


                if Triggers.vix_position_below_high_threshold[date]['open'] == True: #VIX IS BELOW HIGH
                    if (Triggers.vix_velocity_between_thresholds[date]['open'] == True
                        and Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True
                        and Triggers.rsi_below_high_sell_threshold[date]['open'] == True):
                    
                        combo_9_by_day[date]['open'] = True

                        
                elif Triggers.vix_position_below_super_high_threshold[date]['open'] == True: #VIX IS BETWEEN HIGH AND SUPER HIGH
                    if (Triggers.stock_price_above_moving_average_long[date]['open'] == True 
                        and Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True 
                        and Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True 
                        and Triggers.rsi_below_high_sell_threshold[date]['open'] == True):

                        combo_9_by_day[date]['open'] = True


                elif Triggers.vix_position_below_astronomically_high_threshold[date]['open'] == True: #VIX IS BETWEEN SUPER HIGH AND ASTRONOMICAL

                        combo_9_by_day[date]['open'] = True
                
        return combo_9_by_day

    def combo_8(self, Triggers):
        combo_8_by_day = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold and date in Triggers.rsi_below_high_sell_threshold:

                combo_8_by_day[date] = {'open': False}


                if Triggers.vix_position_below_high_threshold[date]['open'] == True: #VIX IS BELOW HIGH
                    if (Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True
                        and Triggers.rsi_below_high_sell_threshold[date]['open'] == True):
                    
                        combo_8_by_day[date]['open'] = True

                        
                elif Triggers.vix_position_below_super_high_threshold[date]['open'] == True: #VIX IS BETWEEN HIGH AND SUPER HIGH
                    if (Triggers.stock_price_above_moving_average_long[date]['open'] == True 
                        and Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True 
                        and Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True 
                        and Triggers.rsi_below_high_sell_threshold[date]['open'] == True):

                        combo_8_by_day[date]['open'] = True


                elif Triggers.vix_position_below_astronomically_high_threshold[date]['open'] == True: #VIX IS BETWEEN SUPER HIGH AND ASTRONOMICAL
                    if (Triggers.rsi_below_high_sell_threshold[date]['open'] == True 
                        and Triggers.vix_velocity_between_thresholds[date]['open'] == True):

                        combo_8_by_day[date]['open'] = True
                
        return combo_8_by_day

    def combo_7(self, Triggers):
        combo_7_by_day = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold and date in Triggers.rsi_below_high_sell_threshold:

                combo_7_by_day[date] = {'open': False}

                if Triggers.vix_position_below_high_threshold[date]['open'] == True: #VIX IS BELOW HIGH
                    if Triggers.vix_velocity_between_thresholds[date]['open'] == True:
                    
                        combo_7_by_day[date]['open'] = True


                elif Triggers.vix_position_below_super_high_threshold[date]['open'] == True:  #VIX IS BETWEEN HIGH AND SUPER HIGH
                    if (Triggers.stock_price_above_moving_average_long[date]['open'] == True and
                        Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True and
                        Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True and
                        Triggers.rsi_below_high_sell_threshold[date]['open'] == True):

                        combo_7_by_day[date]['open'] = True
                        
                else:                                                   #VIX IS ABOVE SUPER HIGH
                    if Triggers.rsi_below_high_sell_threshold[date]['open'] == True:
                
                        combo_7_by_day[date]['open'] = True
                
                
        return combo_7_by_day
                    
    def combo_6(self, Triggers):
        combo_6 = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold and date in Triggers.rsi_below_high_sell_threshold:
                
                combo_6[date] = {'open': False}

                if Triggers.rsi_below_high_sell_threshold[date]['open'] == True:

                    if (Triggers.vix_position_below_high_threshold[date]['open'] == True and #VIX BELOW HIGH
                        Triggers.vix_velocity_between_thresholds[date]['open'] == True):

                        combo_6[date]['open'] = True

                        
                    elif (Triggers.vix_position_below_super_high_threshold[date]['open'] == False and #VIX BETWEEN HIGH AND SUPER HIGH
                        Triggers.rsi_below_low_sell_threshold[date]['open'] == True):
                    
                        combo_6[date]['open'] = True
                    
                    elif (Triggers.stock_price_above_moving_average_long[date]['open'] == True and #VIX ABOVE SUPER HIGH
                          Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True and
                          Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True):

                        combo_6[date]['open'] = True
                    
        return combo_6



    def combo_5(self, Triggers):
        combo_5 = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold:
                
                combo_5[date] = {'open': False}
                
                if (Triggers.percent_of_days_above_moving_average_above_threshold[date]['open'] == True and #NO VIX STANDARD
                    Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True):

                    combo_5[date]['open'] = True
                    
        return combo_5    

    def combo_4(self, Triggers):
        combo_4 = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold:
                
                combo_4[date] = {'open': False}
                
                if (Triggers.stock_price_above_moving_average_long[date]['open'] == True and #NO VIX STANDARD
                    Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True and
                    Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True):

                    combo_4[date]['open'] = True
                    
        return combo_4
        


    def combo_3(self, Triggers):
        combo_3 = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold:
                
                combo_3[date] = {'open': False}

                if Triggers.vix_position_below_high_threshold[date]['open'] == True: #VIX BELOW HIGH

                    combo_3[date]['open'] = True
                    
                elif (Triggers.stock_price_above_moving_average_long[date]['open'] == True and #VIX ABOVE HIGH
                      Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True and
                      Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True):
                    
                    combo_3[date]['open'] = True
                    
        return combo_3


    def combo_2(self, Triggers):
        combo_2 = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold:
                
                combo_2[date] = {'open': False}
                
                if Triggers.vix_position_below_high_threshold[date]['open'] == True: #VIX BELOW HIGH
                    
                    combo_2[date]['open'] = True

                elif (Triggers.stock_price_above_moving_average_long[date]['open'] == True and #VIX ABOVE HIGH
                      Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True):
                    
                    combo_2[date]['open'] = True
                    
        return combo_2

    def combo_1(self, Triggers):
        combo_1 = {}
        for date in Triggers.vix_position_below_high_threshold:
            if date in Triggers.stock_price_above_moving_average_long:
                
                combo_1[date] = {'open': False}
                
                if Triggers.vix_position_below_high_threshold[date]['open'] == True: #VIX BELOW HIGH
                    combo_1[date]['open'] = True
                    
                elif Triggers.stock_price_above_moving_average_long[date]['open'] == True: #VIX ABOVE HIGH
                    combo_1[date]['open'] = True
                    
        return combo_1


    

#######################
#
# EXCEL
#
#######################

    #######################
    #
    # COMPARE DATA SOURCES
    #
    #######################

def compare_data_source(Assumptions):
    excel = LoadStock().FromExcel().get_data(Assumptions)
    market_stack = LoadStock().FromMarketStack().get_data(Assumptions, Assumptions.stock)
    tiingo = LoadStock().FromTiingo().get_data(Assumptions, Assumptions.stock)
    alphavantage = LoadStock().FromAlphaVantage().get_data(Assumptions, Assumptions.stock)

    rows = ["A", "B", "C", "D", "E', "F', "G', "H", "I", "J", "K", "L", "M", "N", "O", "P" , "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
    data_sources = {'excel': excel, 'market_stack': market_stack, 'tiingo': tiingo, 'alpha_vantage': alphavantage}
    data_fields = ['raw_open', 'raw_close', 'open', 'close']
                    
    with xlsxwriter.Workbook(Assumptions.location_of_excel_folders + 'all_data_sources.xlsx') as workbook:
        currency_format = workbook.add_format({'num_format': '$#,##0.00;[Red]($#,##0.00)'})
        date_format = workbook.add_format({'num_format': 'm/d/yy'})

        data = []
        headers = [{'header': 'date', 'format': date_format}]
        for date in tiingo: #assumption is that tiingo has most days covered
            single_row_data = []
            single_row_data.append(excel_date(datetime.datetime(tiingo[date]['year'], tiingo[date]['month'], tiingo[date]['day'])))

            counter = 0
            for data_source in data_sources:
                for field in data_fields:
                    
                    if data_source + field not in headers:
                        headers.append({'header': data_source + field, 'format': currency_format})

                    try:
                        single_row_data.append(data_sources[data_source][date][field])
                    except:
                        #print(traceback.format_exc())
                        single_row_data.append("")

                    counter += 1
            data.append(single_row_data)
                        
        worksheet = workbook.add_worksheet()
        worksheet.add_table(0,
                            0,
                            len(data),
                            counter,
                            {'data': data,
                             'columns': headers})
        
    #######################
    #
    # VIEW STRATEGY ALONGSIDE RELEVANT METRICS BY DAY
    #
    #######################

def create_view_strategy_alongside_relevant_metrics_by_day_data(strategy_name, stock, Assumptions, Metrics, Triggers, Returns):
    last_stock_aggregate_return = 1
    last_strategy_aggregate_return = 1

    list_to_write = []

    strategy_running_tally_3x = getattr(Returns,strategy_name).running_tally_by_day_3x
    buy_and_hold_runing_tally = getattr(Returns,"buy_and_hold_strategy").running_tally_by_day
    
    for date in stock:
        msft_date = excel_date(datetime.datetime(stock[date]['year'], stock[date]['month'], stock[date]['day']))
        
        stock_aggregate_return = round(buy_and_hold_runing_tally[date]['close_running_tally'], 4) - 1
        stock_daily_return = round((buy_and_hold_runing_tally[date]['close_running_tally'] - last_stock_aggregate_return)/last_stock_aggregate_return, 4)

        try:
            strategy_aggregate_return = round(strategy_running_tally_3x[date]['close_running_tally'], 4) - 1
            strategy_daily_return = round((strategy_running_tally_3x[date]['close_running_tally'] - last_strategy_aggregate_return)/last_strategy_aggregate_return, 4)
        except:
            strategy_aggregate_return = last_strategy_aggregate_return - 1
            strategy_daily_return = ""

        try:
            dividend = stock[date]['aggregate_dividend']
        except:
            #print(traceback.format_exc())
            dividend = ""
            
        
        try:
            buy_instruction = strategy_running_tally_3x[date]['buy_sell_order']
        except:
            buy_instruction = ""

        try:
            stock_price_above_moving_average_long = Triggers.stock_price_above_moving_average_long[date]['open']
        except:
            stock_price_above_moving_average_long = ""

        try:
            moving_average_difference = Metrics.moving_average_by_day_of_stock_price_long[date] - Metrics.moving_average_by_day_of_stock_price_short[date]
        except:
            moving_average_difference = ""

        try:
            moving_average_stock_velocity_by_day = Metrics.moving_average_stock_velocity_by_day[date]
        except:
            moving_average_stock_velocity_by_day = ""

        try:
            vix = Metrics.vix[date]['open']
        except:
            #print(traceback.format_exc())
            vix = ""

        try:
            vix_velocity_moving_average_by_day = round(Metrics.vix_velocity_moving_average_by_day[date], 2)
        except:
            vix_velocity_moving_average_by_day = ""

        try:
            moving_average_difference_velocity_percentile = Metrics.velocity_of_difference_between_long_and_short_moving_averages[date]
        except:
            moving_average_difference_velocity_percentile = ""

        try:
            rsi_by_day = Metrics.rsi_by_day[date]
        except:
            rsi_by_day = ""

            
        list_to_write.append([msft_date,
                              stock[date]['open'],
                              stock[date]['close'],
                              dividend,
                              stock_daily_return,
                              stock_aggregate_return,
                              strategy_daily_return,
                              strategy_aggregate_return,
                              buy_instruction,
                              vix,
                              vix_velocity_moving_average_by_day,
                              stock_price_above_moving_average_long,
                              Metrics.moving_average_by_day_of_stock_price_long[date],
                              Metrics.moving_average_by_day_of_stock_price_short[date],
                              moving_average_difference,
                              moving_average_difference_velocity_percentile,
                              moving_average_stock_velocity_by_day,
                              rsi_by_day
                                ])
        try:
            last_stock_aggregate_return = buy_and_hold_runing_tally[date]['close_running_tally']
            last_strategy_aggregate_return = strategy_running_tally_3x[date]['close_running_tally']
        except:
            pass
    return list_to_write

def write_view_strategy_alongside_relevant_metrics_by_day_to_excel(data_for_excel, Assumptions):
    with xlsxwriter.Workbook(Assumptions.location_of_excel_folders + 'strategy_alongside_metrics.xlsx') as workbook:
        negative_number_format = workbook.add_format({'num_format': '#,##0.0000;[Red](#,##0.0000)'})
        currency_format = workbook.add_format({'num_format': '$#,##0.00;[Red]($#,##0.00)'})
        percentage_format = workbook.add_format({'num_format': '0.00%'})
        date_format = workbook.add_format({'num_format': 'm/d/yy'})

        for data_title in data_for_excel:               
            worksheet = workbook.add_worksheet(data_title)
            worksheet.add_table(0,
                                0,
                                len(data_for_excel[data_title]),
                                len(data_for_excel[data_title][0]) -1,
                                {'data': data_for_excel[data_title],
                                 'columns': [{'header': 'date', 'format': date_format},
                                             {'header': 'Stock Open', 'format': currency_format},
                                             {'header': 'Stock Close', 'format': currency_format},
                                             {'header': 'Aggregate Dividend', 'format': currency_format},
                                             {'header': 'Stock Daily Return', 'format': percentage_format},
                                             {'header': 'Stock Agg Return', 'format': percentage_format},
                                             {'header': 'Strategy Daily Return', 'format': percentage_format},
                                             {'header': 'Strategy Agg Return', 'format': percentage_format},
                                             {'header': 'Buy Instruction'},
                                             {'header': 'VIX', 'format': negative_number_format},
                                             {'header': 'VIX Mov Avg Velocity Percentile', 'format': negative_number_format},
                                             {'header': 'Above Mov Avg Long?'},
                                             {'header': 'Stock Mov Avg Long', 'format': negative_number_format},
                                             {'header': 'Stock Mov Avg Short', 'format': negative_number_format},
                                             {'header': 'Stock Mov Avg Difference', 'format': negative_number_format},
                                             {'header': 'Stock Mov Avg Difference Velocity Percentile', 'format': negative_number_format},
                                             {'header': 'Stock Mov Avg Velocity', 'format': negative_number_format},
                                             {'header': 'RSI', 'format': negative_number_format},
                                                ]})
            chart = workbook.add_chart({'type': 'line'})
            
            chart.add_series({'name': '=\'' + data_title + "\'!$F$1",
                              'categories': '=\'' + data_title + "\'!$A2:$A" + str(len(data_for_excel[data_title])),
                              'values': '=\'' + data_title + "\'!$F2:$F" + str(len(data_for_excel[data_title]))})
            
            chart.add_series({'name': '=\'' + data_title + "\'!$H$1",
                              'categories': '=\'' + data_title + "\'!$A2:$A" + str(len(data_for_excel[data_title])),
                              'values': '=\'' + data_title + "\'!$H2:$H" + str(len(data_for_excel[data_title]))})
            
            chart.set_title({'name': "Aggregate Returns Leveraged v. Non Leveraged"})
            worksheet.insert_chart('N2', chart, {'x_offset': 25, 'y_offset': 10})
        
    return None

#######################
#
# RETURNS 
#
#######################     

class Returns:

    def __init__(self, stock, Triggers, Assumptions, Combos):
        self.buy_and_hold_strategy = self.SingleStrategyReturns(stock, Triggers.buy_and_hold, Assumptions)
        self.vix_position_high_strategy = self.SingleStrategyReturns(stock, Triggers.vix_position_below_high_threshold, Assumptions)
        self.vix_position_low_strategy = self.SingleStrategyReturns(stock, Triggers.vix_position_below_low_threshold, Assumptions)
        self.vix_position_super_high_strategy = self.SingleStrategyReturns(stock, Triggers.vix_position_below_super_high_threshold, Assumptions)
        self.vix_position_astronomically_high_strategy = self.SingleStrategyReturns(stock, Triggers.vix_position_below_astronomically_high_threshold, Assumptions)
        self.stock_price_moving_average_long_strategy = self.SingleStrategyReturns(stock, Triggers.stock_price_above_moving_average_long, Assumptions)
        self.stock_price_moving_average_short_strategy = self.SingleStrategyReturns(stock, Triggers.stock_price_above_moving_average_short, Assumptions)
        self.stock_velocity_moving_average_strategy = self.SingleStrategyReturns(stock, Triggers.moving_avg_stock_velocity_above_threshold, Assumptions)
        self.difference_between_long_and_short_stock_moving_avg_strategy = self.SingleStrategyReturns(stock, Triggers.difference_between_long_and_short_moving_avg_above_threshold, Assumptions)
        self.vix_velocity_strategy = self.SingleStrategyReturns(stock, Triggers.vix_velocity_between_thresholds, Assumptions)
        self.percent_days_above_moving_average_strategy = self.SingleStrategyReturns(stock, Triggers.percent_of_days_above_moving_average_above_threshold, Assumptions)
        self.rsi_is_below_high_sell_threshold = self.SingleStrategyReturns(stock, Triggers.rsi_below_high_sell_threshold, Assumptions)
        self.rsi_is_below_low_sell_threshold = self.SingleStrategyReturns(stock, Triggers.rsi_below_low_sell_threshold, Assumptions)
        self.velocity_of_difference_between_long_and_short_below_threshold = self.SingleStrategyReturns(stock, Triggers.velocity_of_difference_between_long_and_short_below_threshold, Assumptions)
        
        self.combo_1 = self.SingleStrategyReturns(stock, Combos.combo_1, Assumptions)
        self.combo_2 = self.SingleStrategyReturns(stock, Combos.combo_2, Assumptions)
        self.combo_3 = self.SingleStrategyReturns(stock, Combos.combo_3, Assumptions)
        self.combo_4 = self.SingleStrategyReturns(stock, Combos.combo_4, Assumptions)
        self.combo_5 = self.SingleStrategyReturns(stock, Combos.combo_5, Assumptions)
        self.combo_6 = self.SingleStrategyReturns(stock, Combos.combo_6, Assumptions)
        self.combo_7 = self.SingleStrategyReturns(stock, Combos.combo_7, Assumptions)
        self.combo_8 = self.SingleStrategyReturns(stock, Combos.combo_8, Assumptions)
        self.combo_9 = self.SingleStrategyReturns(stock, Combos.combo_9, Assumptions)

    class SingleStrategyReturns:

        def __init__(self, stock, triggers_by_day, Assumptions):
            self.leverage_multiple = Assumptions.leverage_multiple
            self.rolling_stop_loss_threshold = Assumptions.rolling_stop_loss_threshold
            self.days_out_after_rolling_stop_loss_threshold_met = Assumptions.days_out_after_rolling_stop_loss_threshold_met
            self.days_actually_out = self.days_out_after_rolling_stop_loss_threshold_met + 1
            
            self.running_tally_by_day = {}
            self.running_tally_by_day_3x = {}
            self.running_tally = 1
            self.running_tally_3x = 1
            self.running_tally_by_day, self.running_tally_by_day_3x = self.calculate_return_of_stock(stock, triggers_by_day)

        def rolling_stop_loss_threshold_met(self, stock, date):
            try: #if there is no low key, except is hit
                day_loss = ((stock[date]['low'] - stock[date]['open'])/stock[date]['open']) * 100
                if day_loss < (self.rolling_stop_loss_threshold * -1):
                    return True
            except:
                pass
            return False

        def create_buy_sell_orders(self, triggers_by_day, stock, implement_rolling_stop_loss):
            last_date_we_have_data_for_stock = list(triggers_by_day.keys())[-1]
            buy_and_sell_orders_by_day = {}
            currently_holding_stock = False
            
            for date in triggers_by_day: #this assumes all buy and sells orders are triggered at open, except for rolling_stop_loss
                buy_and_sell_orders_by_day[date] = None
                if date in stock:

                    self.days_actually_out += 1
                    if implement_rolling_stop_loss and currently_holding_stock and self.rolling_stop_loss_threshold_met(stock, date):
                        buy_and_sell_orders_by_day[date] = "stop_loss_threshold_met"
                        self.days_actually_out = 0
                        currently_holding_stock = False
                    
                    elif triggers_by_day[date]['open'] and self.days_actually_out >= self.days_out_after_rolling_stop_loss_threshold_met:
                        if not currently_holding_stock:
                            buy_and_sell_orders_by_day[date] = "buy"
                            currently_holding_stock = True
                        else:
                            buy_and_sell_orders_by_day[date] = "hold"

                    elif currently_holding_stock:
                        buy_and_sell_orders_by_day[date] = "sell"
                        currently_holding_stock = False

                    if currently_holding_stock:
                        self.days_actually_out = self.days_out_after_rolling_stop_loss_threshold_met + 1

            return buy_and_sell_orders_by_day
        
        def calculate_current_return(self, current_price, last_price):
            running_tally = self.running_tally * (1+ ((current_price - last_price)/last_price))
            running_tally_3x = self.running_tally_3x * (1+ (((current_price - last_price)/last_price) * self.leverage_multiple))
            return running_tally, running_tally_3x

        def calculate_current_return_after_stop_loss_threshold_met(self, last_price):
            last_price = last_price * (1 + (-1 * (self.rolling_stop_loss_threshold/100)))
            running_tally = self.running_tally * (1+ (-1 * (self.rolling_stop_loss_threshold/100)))
            running_tally_3x = self.running_tally_3x * (1+ ((-1 * (self.rolling_stop_loss_threshold/100)) * self.leverage_multiple))
            return running_tally, running_tally_3x, last_price           
        
        def add_running_tally_by_day_open_data(self, stock, date, last_price):
            try: #if last price is False, we have not made any returns yet
                open_running_tally, open_running_tally_3x = self.calculate_current_return(stock[date]['open'], last_price)
            except:
                open_running_tally = 1
                open_running_tally_3x = 1
                
            self.running_tally_by_day[date] = {'month': stock[date]['month'],
                                               'day': stock[date]['day'],
                                               'year': stock[date]['year'],
                                               'open_running_tally': open_running_tally}

            self.running_tally_by_day_3x[date] = {'month': stock[date]['month'],
                                                  'day': stock[date]['day'],
                                                  'year': stock[date]['year'],
                                                  'open_running_tally': open_running_tally_3x}

        def add_running_tally_by_day_close_data(self, date, buy_and_sell_orders_by_day):
            
            self.running_tally_by_day[date]['close_running_tally'] = self.running_tally
            self.running_tally_by_day[date]['buy_sell_order'] = buy_and_sell_orders_by_day[date]
            
            self.running_tally_by_day_3x[date]['close_running_tally'] = self.running_tally_3x
            self.running_tally_by_day_3x[date]['buy_sell_order'] = buy_and_sell_orders_by_day[date]

        def calculate_return_of_stock(self, stock, triggers_by_day, implement_rolling_stop_loss=False):
            
            try:
                buy_and_sell_orders_by_day = self.create_buy_sell_orders(triggers_by_day, stock, implement_rolling_stop_loss)

                last_price = False 
                for date in buy_and_sell_orders_by_day:
                    if date in stock and buy_and_sell_orders_by_day[date] != None:
                        self.add_running_tally_by_day_open_data(stock, date, last_price)

                        if buy_and_sell_orders_by_day[date] == "buy":
                            last_price = stock[date]['open']

                        if buy_and_sell_orders_by_day[date] == "sell":
                            self.running_tally, self.running_tally_3x = self.calculate_current_return(stock[date]['open'], last_price)

                        elif buy_and_sell_orders_by_day[date] == "stop_loss_threshold_met":
                            self.running_tally, self.running_tally_3x, last_price = self.calculate_current_return_after_stop_loss_threshold_met(last_price)
                            
                        else: 
                            self.running_tally, self.running_tally_3x = self.calculate_current_return(stock[date]['close'], last_price)
                            last_price = stock[date]['close']
                            
                        self.add_running_tally_by_day_close_data(date, buy_and_sell_orders_by_day)
            except:
                print(traceback.format_exc())
                        
            return self.running_tally_by_day, self.running_tally_by_day_3x

        
#######################
#
# CALC DATA
#
#######################

class CalcReturnsBetweenDateRanges:
    
    def __init__(self, start_date, end_date, stock, Assumptions, Metrics):
        if start_date != None and end_date != None:
            self.stock = self.limit_stock_list_to_window_of_time(stock, start_date, end_date)
        else:
            self.stock = stock
        self.Triggers = Triggers(Assumptions, self.stock, Metrics)
        self.Combos = Combos(self.Triggers)
        self.Returns = Returns(self.stock, self.Triggers, Assumptions, self.Combos)
        
    def calc_triggers_combos_and_returns(self):
        return self.stock, self.Triggers, self.Combos, self.Returns

    def limit_stock_list_to_window_of_time(self, stock, date_start, date_end):
        timestamp_start = time.mktime(datetime.datetime.strptime(date_start, "%Y-%m-%d").timetuple())
        timestamp_end = time.mktime(datetime.datetime.strptime(date_end, "%Y-%m-%d").timetuple())
        temp_stock = {}
        for date in stock:
            if time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple()) > timestamp_end:
                break
            if time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple()) >= timestamp_start:
                temp_stock[date] = stock[date]
        return temp_stock


#######################
#
# REPORTS
#
#######################

class GenerateReports:

    def __init__(self, strategy_to_see):
        self.strategy_to_see = strategy_to_see
        self.Assumptions = Assumptions()
        self.stock = LoadStock().load_stock(self.Assumptions, self.Assumptions.stock)
        self.Metrics = Metrics(self.Assumptions, self.stock)
        self.date_ranges = [{'name': 'Entire Period', 'start_date': None, 'end_date': None},
                            {'name': 'From TQQQ Inception', 'start_date': '2010-2-11', 'end_date':'2021-2-18'}, 
                            {'name': 'Before Dot Com', 'start_date': "1999-3-10", 'end_date': "2000-3-10"},
                            {'name': 'Dot Com', 'start_date': "2000-3-10", 'end_date': "2002-10-4"},
                            {'name': 'Between Dot Com and Crisis', 'start_date': "2002-10-4", 'end_date': "2008-5-1"},
                            {'name': 'Financial Crisis', 'start_date': "2008-5-1", 'end_date': "2009-3-20"},
                            {'name': 'End Crisis to Pandemic', 'start_date': "2009-3-20", 'end_date': "2020-2-10"},
                            {'name': 'Top Pandemic to Bottom', 'start_date': "2020-2-10", 'end_date': "2020-3-23"},
                            {'name': 'Bottom Pandemic to Today', 'start_date': "2020-3-23", 'end_date': "2021-1-19"}]

    def stock_date_exists_for_entire_date_range(self, stock, start_date, end_date):
        if start_date == None and end_date == None:
            return True
        if start_date in stock and end_date in stock:
            return True
        return False
            
        
    def create_spreadsheet_of_strategy_and_metrics_by_timeperiod_for_specific_strategy(self):
        data_for_excel = {}

        for date_range in self.date_ranges: #for each date range compile list of excel data separately
            try:
                if self.stock_date_exists_for_entire_date_range(self.stock, date_range['start_date'], date_range['end_date']):
                    stock, Triggers, Combos, Returns = CalcReturnsBetweenDateRanges(date_range['start_date'], date_range['end_date'], self.stock, self.Assumptions, self.Metrics).calc_triggers_combos_and_returns()
                    data = create_view_strategy_alongside_relevant_metrics_by_day_data(self.strategy_to_see,
                                                                    stock,
                                                                    self.Assumptions,
                                                                    self.Metrics,
                                                                    Triggers,
                                                                    Returns)
                    data_for_excel[date_range['name']] = data
            except:
                print(traceback.format_exc())
        
        empty = write_view_strategy_alongside_relevant_metrics_by_day_to_excel(data_for_excel, self.Assumptions) #write lists to excel

    def get_first_date_for_stock(self, stock):
        return stock[list(stock.keys())[0]]['human_readable_date']
    
    def get_last_date_for_stock(self, stock):
        return stock[list(stock.keys())[-1]]['human_readable_date']

    def get_buy_and_sell_count(self, running_tally_by_day):
        buy = 0
        sell = 0
        for date in running_tally_by_day:
            if running_tally_by_day[date]['buy_sell_order'] == "buy":
                buy += 1
            elif running_tally_by_day[date]['buy_sell_order'] == "sell":
                sell += 1
        return buy + sell

    def get_days_in_market(self, running_tally_by_day):
        days_in_market = 0

        for date in running_tally_by_day:
            if running_tally_by_day[date]['buy_sell_order'] != None:
                days_in_market += 1
        return days_in_market
        
    def print_report_to_IDE(self, start_date, end_date):
        stock, Triggers, Combos, Returns = CalcReturnsBetweenDateRanges(start_date, end_date, self.stock, self.Assumptions, self.Metrics).calc_triggers_combos_and_returns()
        for attribute in [a for a in dir(Returns) if not a.startswith('__')]:
            print(attribute)

            try:
                strategy_returns = getattr(Returns,attribute)
                running_tally_by_day = strategy_returns.running_tally_by_day
                running_tally_by_day_3x = strategy_returns.running_tally_by_day_3x
                
                print(self.get_first_date_for_stock(stock) + " to " + self.get_last_date_for_stock(stock))
                print("Number of Buys and Sells: " + str(self.get_buy_and_sell_count(running_tally_by_day)))
                print("Days in Market: " + str(self.get_days_in_market(running_tally_by_day)))
                print("No Leverage: " + str(round(get_last_item_in_dictionary_of_dictionaries(running_tally_by_day, 'close_running_tally'), 1))+"x")
                print("With Leverage: " + str(round(get_last_item_in_dictionary_of_dictionaries(running_tally_by_day_3x, 'close_running_tally'), 1))+"x")

            except:
                print(traceback.format_exc())
                print("No Leverage: 1")
                print("With Leverage: 1")
            print()
            print()

#######################
#
# EXPERIMENTS
#
#######################

class Experiments:
    
    def __init__(self, Assumptions, start_date = None, end_date = None):
        self.start_date = start_date
        self.end_date = end_date
        self.Assumptions = Assumptions
        self.stock = LoadStock().load_stock(self.Assumptions, self.Assumptions.stock)
        self.Metrics = Metrics(self.Assumptions, self.stock)
        self.stock, self.Triggers, self.Combos, self.Returns = CalcReturnsBetweenDateRanges(self.start_date, self.end_date, self.stock, self.Assumptions, self.Metrics).calc_triggers_combos_and_returns()
        self.running_tally = 1
        self.last_price = 1
        self.percent_change = 0
        self.last_date = 0
        self.buy = False

    def calc_running_tally(self):
        self.running_tally = self.running_tally * (1+self.percent_change)

    def calc_percent_change(self, date):
        current_price = self.Returns.buy_and_hold_strategy.running_tally_by_day_3x[date]['open_running_tally']
        self.percent_change = (current_price - self.last_price)/self.last_price

    def update_last_price(self, date):
        self.last_price = self.Returns.buy_and_hold_strategy.running_tally_by_day_3x[date]['open_running_tally']

    def print_results(self):
        print(self.last_date) #the date when the condition was met
        print(self.percent_change * 100) #the change between when the condition was met and the next open
        print(self.running_tally)
        print()
        print()

    def sell_stock_and_calculate_returns(self, date):
        if self.buy == True: #this is the next morning after the previous buy (the buy happens below)
            self.calc_percent_change(date)
            self.calc_running_tally()
            self.buy = False

    def experiment_combo_8_between_high_and_super_high_add_vix_velocity(self):

        #adding vix velocity to vix between high and super high
        #but only if you add a lower threshold
        #vix_velocity_upper_threshold = 85
        #Experiments(Assumptions(vix_velocity_upper_threshold = 85)).experiment_combo_8_add_vix_velocity()
        
        for date in self.Returns.buy_and_hold_strategy.running_tally_by_day_3x:

            self.sell_stock_and_calculate_returns(date)  
            
            try: 

                
                if (self.Triggers.vix_position_below_super_high_threshold[date]['open'] == True
                    and self.Triggers.vix_position_below_high_threshold[date]['open'] == False): 

                    if (self.Triggers.stock_price_above_moving_average_long[date]['open'] == True 
                        and self.Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True 
                        and self.Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True 
                        and self.Triggers.rsi_below_high_sell_threshold[date]['open'] == True
                        and self.Triggers.vix_velocity_between_thresholds[date]['open'] == True): #this line is new, but only helps with vix_velocity_upper_threshold = 85 

                        self.buy = True
            except:
                pass
            
            self.update_last_price(date) 
            self.last_date = date
        print(self.running_tally)

    def experiment_combo_8_between_super_high_and_astronomical_add_vix_velocity_and_increase_astronimical_limit(self):

        #increase astronomical vix threshold to 50
        #add vix_velocity but only if you decrease upper limit
        #vix_velocity_upper_threshold = 85
        #Experiments = Experiments(Assumptions(vix_astronomically_high_threshold = 50, vix_velocity_upper_threshold = 85)).experiment_combo_8_between_super_high_and_astronomical_add_vix_velocity_and_increase_astronimical_limit()
        
        for date in self.Returns.buy_and_hold_strategy.running_tally_by_day_3x:

            self.sell_stock_and_calculate_returns(date)  
            
            try: 

                
                if (self.Triggers.vix_position_below_super_high_threshold[date]['open'] == True
                    and self.Triggers.vix_position_below_high_threshold[date]['open'] == False): 

                    if (self.Triggers.stock_price_above_moving_average_long[date]['open'] == True 
                        and self.Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True 
                        and self.Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True 
                        and self.Triggers.rsi_below_high_sell_threshold[date]['open'] == True
                        and self.Triggers.vix_velocity_between_thresholds[date]['open'] == True): #this line is new, but only helps with vix_velocity_upper_threshold = 85 

                        self.buy = True
            except:
                pass
            
            self.update_last_price(date) 
            self.last_date = date
        print(self.running_tally)

    def experiment_vix_above_40_and_vix_velocity_results_in_earnings(self):

        #you can make 27 percent if you are in the market when the vix is above 40
        #so long as you exit the market for 2 days every time the vix velocity thresholds are met
        #Experiments = Experiments(Assumptions(vix_super_high_threshold = 40, days_out_after_significant_vix_velocity_move = 2)).experiment_vix_above_40_and_vix_velocity_results_in_earnings()
        
        for date in self.Returns.buy_and_hold_strategy.running_tally_by_day_3x:

            self.sell_stock_and_calculate_returns(date)  
            
            try: 

                
                if self.Triggers.vix_position_below_super_high_threshold[date]['open'] == False: #VIX IS ABOVE SUPER HIGH

                    if self.Triggers.vix_velocity_between_thresholds[date]['open'] == True:
                        
                        self.buy = True
            except:
                pass
            
            self.update_last_price(date) 
            self.last_date = date
        print(self.running_tally)

    def experiment_vix_above_70(self):

        #you can make 36 percent if you are in the market when the vix is above 70
        #Experiments = Experiments(Assumptions(vix_super_high_threshold = 70, days_out_after_significant_vix_velocity_move = 0)).experiment()
        
        for date in self.Returns.buy_and_hold_strategy.running_tally_by_day_3x:

            self.sell_stock_and_calculate_returns(date)  
            
            try: 

                
                if self.Triggers.vix_position_below_super_high_threshold[date]['open'] == False: #VIX IS ABOVE SUPER HIGH
                        
                        self.buy = True
            except:
                pass
            
            self.update_last_price(date) 
            self.last_date = date
        print(self.running_tally)
        
    def experiment(self):
        #this assumes we buy at open on the day the conditions are met and sell the next open
        for date in self.Returns.buy_and_hold_strategy.running_tally_by_day_3x:

            self.sell_stock_and_calculate_returns(date) #this is the next morning after the previous buy (the buy happens below) 
            #self.print_results() #uncomment this if you want to see day by day results printed to the shell
            
            try: #if date is not in one of the triggers, you will get an error.

                
                if self.Triggers.vix_position_below_high_threshold[date]['open'] == True: #VIX IS BETWEEN HIGH AND SUPER HIGH
                    #if self.Triggers.vix_position_below_high_threshold[date]['open'] == False:
                        #if (self.Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True
                            #and self.Triggers.rsi_below_high_sell_threshold[date]['open'] == True):

                                print(date)
                                print(self.running_tally)
                                print()
                                print()

                                ###############################################
                                # DO NOT ACCIDENTALLY DELETE THE FOLLOWING LINE
                                ###############################################
                                self.buy = True
            except:
                #print(traceback.format_exc()) #if you get a result that is extreme, uncomment this line and ensure the errors are only related to date not being in triggers
                pass
            
            self.update_last_price(date) #open price
            self.last_date = date
        print(self.running_tally)

            
#Experiments = Experiments(Assumptions(), start_date = "1999-3-10", end_date = "2000-9-05").experiment()




#######################
#
# REPORTS
#
#######################

start_date = None #for custom dates, use this format: "1999-3-10".  For the entire data set, use None for start and end date
end_date = None
strategy_to_see = "combo_8"


compare_data_source(Assumptions())
Reports = GenerateReports(strategy_to_see)
Reports.print_report_to_IDE(None, None)
Reports.create_spreadsheet_of_strategy_and_metrics_by_timeperiod_for_specific_strategy()



import time
import datetime
import traceback
from xlrd import open_workbook
import xlrd
import xlsxwriter
from dateutil.relativedelta import relativedelta
from scipy import stats

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
                 location_of_excel_folders = "./vix_analysis/",
                 stock = "QQQ",
                 leverage_multiple = 3,

                 vix_low_threshold = 14,
                 vix_high_threshold = 18, 
                 vix_super_high_threshold = 30, #will buy when <= threshold.  we have multiple thresholds to allow for different levels of scrutiny depending on vix level.
                 vix_astronomically_high_threshold = 40,
                 
                 days_for_moving_average_long = 50, 
                 days_for_moving_average_short = 10,
                 difference_between_long_and_short_moving_average_threshold = -3, #will buy when >= threshold

                 velocity_of_difference_between_long_and_short_moving_averages_threshold = 20, #percentiles, lower percentiles indicate short is quickly getting larger than long, buy when above threshold

                 days_for_percent_above_moving_average = 50,#number of days for moving average (which is the underlying metric for this calc)
                 percent_above_moving_average_threshold = 17,#any number here is a percent, .02 is .02%, will buy when x% of previous days was above moving avg
                 
                 vix_velocity_upper_threshold = 90,#percentiles, higher percentile translates to higher slope, will buy between both thresholds
                 vix_velocity_lower_threshold = 10, 
                 days_for_vix_velocity = 10,
                 
                 days_for_moving_avg_stock_velocity = 50,
                 moving_avg_stock_velocity_threshold = 0, #any number here is a percent, .02 is .02%, will buy when avg velocity is above x%
                 
                 days_for_avg_negative = 20,

                 days_for_rsi_calculation = 50, #RSI attempts to calculate when the market is overbought or oversold
                 rsi_high_sell_threshold = 60,
                 rsi_low_sell_threshold = 50,): 
        
        self.location_of_excel_folders = location_of_excel_folders    
        self.stock = stock #this allows qqq, spy, tqqq, spxl
        self.leverage_multiple = leverage_multiple

        self.vix_low_threshold = vix_low_threshold
        self.vix_high_threshold = vix_high_threshold
        self.vix_super_high_threshold = vix_super_high_threshold
        self.vix_astronomically_high_threshold = vix_astronomically_high_threshold

        self.days_for_moving_average_long = days_for_moving_average_long
        self.days_for_moving_average_short = days_for_moving_average_short
        self.difference_between_long_and_short_moving_average_threshold = difference_between_long_and_short_moving_average_threshold

        self.velocity_of_difference_between_long_and_short_moving_averages_threshold = velocity_of_difference_between_long_and_short_moving_averages_threshold

        self.days_for_percent_above_moving_average = days_for_percent_above_moving_average
        self.percent_above_moving_average_threshold = percent_above_moving_average_threshold 

        self.vix_velocity_upper_threshold = vix_velocity_upper_threshold
        self.vix_velocity_lower_threshold = vix_velocity_lower_threshold
        self.days_for_vix_velocity = days_for_vix_velocity 

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

    def build_dictionary_of_single_day_data(self, year,
                                            month,
                                            day,
                                            timestamp,
                                            human_readable_date,
                                            stock_open,
                                            stock_close):
        if stock_open != "n/a":
            single_day_data = {'year': year,
                               'month': month,
                               'day': day,
                               'timestamp': timestamp,
                               'human_readable_date': human_readable_date,
                               'open': stock_open,
                               'close': stock_close
                               }
            return single_day_data
        return None

    def extract_one_row_of_stock_data(self, book, row):
        stock_open = row[1].value
        stock_close = row[2].value
        excel_date = row[0].value
        year, month, day, hour, minute, second, human_readable_date, timestamp = self.convert_excel_date_to_component_parts(book, excel_date)
        return self.build_dictionary_of_single_day_data(year, month, day, timestamp, human_readable_date, stock_open, stock_close)

    def load_stock_data(self, Assumptions):
        book, sheet = self.get_sheet_from_excel(Assumptions, Assumptions.stock + ".xls")
        counter = 0
        for row in sheet:
            if counter > 0:
                single_day_data = self.extract_one_row_of_stock_data(book, row)
                if single_day_data != None:
                    self.stock[single_day_data['human_readable_date']] = single_day_data
            counter += 1
        return self.stock
   
        
#######################
#
# METRICS 
#
#######################


class Metrics:

    def __init__(self, Assumptions, stock):
        self.vix = self.GetVixData().load_vix_data(Assumptions)
        self.moving_average_by_day_of_stock_price_long = self.calc_moving_avg_of_stock_price_by_day(stock, Assumptions.days_for_moving_average_long)
        self.moving_average_by_day_of_stock_price_short = self.calc_moving_avg_of_stock_price_by_day(stock, Assumptions.days_for_moving_average_short)
        self.moving_average_stock_velocity_by_day = self.calc_moving_avg_of_daily_stock_velocity_by_day(stock, Assumptions)
        self.vix_velocity_moving_average_by_day = self.calc_vix_velocity_moving_average_by_day(Assumptions, self.vix )
        self.percent_above_moving_average = self.calc_percent_of_days_above_moving_average(stock, Assumptions)
        self.velocity_of_difference_between_long_and_short_moving_averages = self.calc_velocity_of_difference_between_long_and_short_moving_averages(Assumptions, self.moving_average_by_day_of_stock_price_long, self.moving_average_by_day_of_stock_price_short)
        self.rsi_by_day = self.CalcRSI().calc_rsi(Assumptions, stock)

    class GetVixData:
        
        def __init__(self):
            self.file_name = "vix.xls"
            self.vix = {}
            
        def extract_one_row_of_vix_data(self, book, row):
            vix_open = row[1].value
            vix_close = row[4].value
            excel_date = row[0].value
            year, month, day, hour, minute, second, human_readable_date, timestamp = LoadStock().convert_excel_date_to_component_parts(book, excel_date)
            return LoadStock().build_dictionary_of_single_day_data(year, month, day, timestamp, human_readable_date, vix_open, vix_close)

        def load_vix_data(self, Assumptions):
            book, sheet = LoadStock().get_sheet_from_excel(Assumptions, self.file_name)
            counter = 0
            for row in sheet:
                if counter > 0:
                    single_day_data = self.extract_one_row_of_vix_data(book, row)
                    if single_day_data != None:
                        self.vix[single_day_data['human_readable_date']] = single_day_data
                counter += 1
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
                    print(traceback.format_exc())
                    self.rsi_by_day[date] = None
                    
                if last_price is not False:
                    stock_change_values.append(stock[date]['close'] - last_price)

                last_price = stock[date]['close']
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
                    for velocity in stock_velocity_values[-1*Assumptions.days_for_moving_avg_stock_velocity:]:
                        sum_of_stock_velocity_values += velocity
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
                for close_price in stock_values[-1*days_for_moving_average:]:
                    sum_of_stock_values += close_price
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
        self.vix_position_below_high_treshold = self.check_whether_vix_is_below_threshold_by_day(Metrics, Assumptions.vix_high_threshold)
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
        vix_velocity_between_thresholds = {}
        for date in Metrics.vix_velocity_moving_average_by_day:
            if Metrics.vix_velocity_moving_average_by_day[date] != None:
                vix_velocity_between_thresholds[date] = {'open': False}
                
                if Assumptions.vix_velocity_lower_threshold <= Metrics.vix_velocity_moving_average_by_day[date] <= Assumptions.vix_velocity_upper_threshold:
                    vix_velocity_between_thresholds[date]['open'] = True
                
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
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold and date in Triggers.rsi_below_high_sell_threshold:

                combo_9_by_day[date] = {'open': False}


                if Triggers.vix_position_below_high_treshold[date]['open'] == True: #VIX IS BELOW HIGH

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
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold and date in Triggers.rsi_below_high_sell_threshold:

                combo_8_by_day[date] = {'open': False}


                if Triggers.vix_position_below_high_treshold[date]['open'] == True: #VIX IS BELOW HIGH
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
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold and date in Triggers.rsi_below_high_sell_threshold:

                combo_7_by_day[date] = {'open': False}

                if Triggers.vix_position_below_high_treshold[date]['open'] == True: #VIX IS BELOW HIGH
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
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold and date in Triggers.rsi_below_high_sell_threshold:
                
                combo_6[date] = {'open': False}

                if Triggers.rsi_below_high_sell_threshold[date]['open'] == True:

                    if (Triggers.vix_position_below_high_treshold[date]['open'] == True and #VIX BELOW HIGH
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
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold:
                
                combo_5[date] = {'open': False}
                
                if (Triggers.percent_of_days_above_moving_average_above_threshold[date]['open'] == True and #NO VIX STANDARD
                    Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True):

                    combo_5[date]['open'] = True
                    
        return combo_5    

    def combo_4(self, Triggers):
        combo_4 = {}
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold:
                
                combo_4[date] = {'open': False}
                
                if (Triggers.stock_price_above_moving_average_long[date]['open'] == True and #NO VIX STANDARD
                    Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True and
                    Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True):

                    combo_4[date]['open'] = True
                    
        return combo_4
        


    def combo_3(self, Triggers):
        combo_3 = {}
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold:
                
                combo_3[date] = {'open': False}

                if Triggers.vix_position_below_high_treshold[date]['open'] == True: #VIX BELOW HIGH

                    combo_3[date]['open'] = True
                    
                elif (Triggers.stock_price_above_moving_average_long[date]['open'] == True and #VIX ABOVE HIGH
                      Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True and
                      Triggers.difference_between_long_and_short_moving_avg_above_threshold[date]['open'] == True):
                    
                    combo_3[date]['open'] = True
                    
        return combo_3


    def combo_2(self, Triggers):
        combo_2 = {}
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long and date in Triggers.moving_avg_stock_velocity_above_threshold:
                
                combo_2[date] = {'open': False}
                
                if (Triggers.vix_position_below_high_treshold[date]['open'] == True or #VIX BELOW HIGH
                    (Triggers.stock_price_above_moving_average_long[date]['open'] == True and
                     Triggers.moving_avg_stock_velocity_above_threshold[date]['open'] == True)):
                    
                    combo_2[date]['open'] = True
                    
        return combo_2

    def combo_1(self, Triggers):
        combo_1 = {}
        for date in Triggers.vix_position_below_high_treshold:
            if date in Triggers.stock_price_above_moving_average_long:
                
                combo_1[date] = {'open': False}
                
                if Triggers.vix_position_below_high_treshold[date]['open'] == True: #VIX BELOW HIGH
                    combo_1[date]['open'] = True
                    
                if Triggers.stock_price_above_moving_average_long[date]['open'] == True:
                    combo_1[date]['open'] = True
                    
        return combo_1

#######################
#
# EXCEL
#
#######################

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
            
            chart.add_series({'name': '=\'' + data_title + "\'!$E$1",
                              'categories': '=\'' + data_title + "\'!$A2:$A" + str(len(data_for_excel[data_title])),
                              'values': '=\'' + data_title + "\'!$E2:$E" + str(len(data_for_excel[data_title]))})
            
            chart.add_series({'name': '=\'' + data_title + "\'!$G$1",
                  'categories': '=\'' + data_title + "\'!$A2:$A" + str(len(data_for_excel[data_title])),
                  'values': '=\'' + data_title + "\'!$G2:$G" + str(len(data_for_excel[data_title]))})
            
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
        self.buy_and_hold_strategy = self.Single_Strategy_Returns(stock, Triggers.buy_and_hold, Assumptions)
        self.vix_position_high_strategy = self.Single_Strategy_Returns(stock, Triggers.vix_position_below_high_treshold, Assumptions)
        self.vix_position_low_strategy = self.Single_Strategy_Returns(stock, Triggers.vix_position_below_low_threshold, Assumptions)
        self.vix_position_super_high_strategy = self.Single_Strategy_Returns(stock, Triggers.vix_position_below_super_high_threshold, Assumptions)
        self.vix_position_astronomically_high_strategy = self.Single_Strategy_Returns(stock, Triggers.vix_position_below_astronomically_high_threshold, Assumptions)
        self.stock_price_moving_average_long_strategy = self.Single_Strategy_Returns(stock, Triggers.stock_price_above_moving_average_long, Assumptions)
        self.stock_price_moving_average_short_strategy = self.Single_Strategy_Returns(stock, Triggers.stock_price_above_moving_average_short, Assumptions)
        self.stock_velocity_moving_average_strategy = self.Single_Strategy_Returns(stock, Triggers.moving_avg_stock_velocity_above_threshold, Assumptions)
        self.difference_between_long_and_short_stock_moving_avg_strategy = self.Single_Strategy_Returns(stock, Triggers.difference_between_long_and_short_moving_avg_above_threshold, Assumptions)
        self.vix_velocity_strategy = self.Single_Strategy_Returns(stock, Triggers.vix_velocity_between_thresholds, Assumptions)
        self.percent_days_above_moving_average_strategy = self.Single_Strategy_Returns(stock, Triggers.percent_of_days_above_moving_average_above_threshold, Assumptions)
        self.rsi_is_below_high_sell_threshold = self.Single_Strategy_Returns(stock, Triggers.rsi_below_high_sell_threshold, Assumptions)
        self.rsi_is_below_low_sell_threshold = self.Single_Strategy_Returns(stock, Triggers.rsi_below_low_sell_threshold, Assumptions)
        self.velocity_of_difference_between_long_and_short_below_threshold = self.Single_Strategy_Returns(stock, Triggers.velocity_of_difference_between_long_and_short_below_threshold, Assumptions)
        
        self.combo_1 = self.Single_Strategy_Returns(stock, Combos.combo_1, Assumptions)
        self.combo_2 = self.Single_Strategy_Returns(stock, Combos.combo_2, Assumptions)
        self.combo_3 = self.Single_Strategy_Returns(stock, Combos.combo_3, Assumptions)
        self.combo_4 = self.Single_Strategy_Returns(stock, Combos.combo_4, Assumptions)
        self.combo_5 = self.Single_Strategy_Returns(stock, Combos.combo_5, Assumptions)
        self.combo_6 = self.Single_Strategy_Returns(stock, Combos.combo_6, Assumptions)
        self.combo_7 = self.Single_Strategy_Returns(stock, Combos.combo_7, Assumptions)
        self.combo_8 = self.Single_Strategy_Returns(stock, Combos.combo_8, Assumptions)
        self.combo_9 = self.Single_Strategy_Returns(stock, Combos.combo_9, Assumptions)

    class Single_Strategy_Returns:

        def __init__(self, stock, triggers_by_day, Assumptions):
            self.leverage_multiple = Assumptions.leverage_multiple
            self.running_tally_by_day = {}
            self.running_tally_by_day_3x = {}
            self.running_tally = 1
            self.running_tally_3x = 1
            self.running_tally_by_day, self.running_tally_by_day_3x = self.calculate_return_of_stock(stock, triggers_by_day)

        def create_buy_sell_orders(self, triggers_by_day, stock):
            last_date_we_have_data_for_stock = list(triggers_by_day.keys())[-1]
            buy_and_sell_orders_by_day = {}
            currently_holding_stock = False
            
            for date in triggers_by_day: #this assumes all buy and sells orders are triggered at open
                
                if date in stock:
                        
                    if triggers_by_day[date]['open']:
                        if not currently_holding_stock:
                            buy_and_sell_orders_by_day[date] = "buy"
                            currently_holding_stock = True
                        else:
                            buy_and_sell_orders_by_day[date] = "hold"

                    elif currently_holding_stock:
                        buy_and_sell_orders_by_day[date] = "sell"
                        currently_holding_stock = False

            return buy_and_sell_orders_by_day

        def add_running_tally_by_day_open_data(self, stock, date):
            
            self.running_tally_by_day[date] = {'month': stock[date]['month'],
                                               'day': stock[date]['day'],
                                               'year': stock[date]['year'],
                                               'open_running_tally': self.running_tally}
            
            self.running_tally_by_day_3x[date] = {'month': stock[date]['month'],
                                                  'day': stock[date]['day'],
                                                  'year': stock[date]['year'],
                                                  'open_running_tally': self.running_tally_3x}

        def add_running_tally_by_day_close_data(self, date, buy_and_sell_orders_by_day):
            
            self.running_tally_by_day[date]['close_running_tally'] = self.running_tally
            self.running_tally_by_day[date]['buy_sell_order'] = buy_and_sell_orders_by_day[date]
            
            self.running_tally_by_day_3x[date]['close_running_tally'] = self.running_tally_3x
            self.running_tally_by_day_3x[date]['buy_sell_order'] = buy_and_sell_orders_by_day[date]
        
        def calculate_current_return(self, current_price, last_price):
            running_tally = self.running_tally * (1+ ((current_price - last_price)/last_price))
            running_tally_3x = self.running_tally_3x * (1+ (((current_price - last_price)/last_price) * self.leverage_multiple))
            return running_tally, running_tally_3x

        def calculate_return_of_stock(self, stock, triggers_by_day):
            buy_and_sell_orders_by_day = self.create_buy_sell_orders(triggers_by_day, stock)

            last_price = False 
            for date in buy_and_sell_orders_by_day:
                if date in stock:
                    self.add_running_tally_by_day_open_data(stock, date)

                    if buy_and_sell_orders_by_day[date] == "buy":
                        last_price = stock[date]['open']

                    if buy_and_sell_orders_by_day[date] == "sell":
                        self.running_tally, self.running_tally_3x = self.calculate_current_return(stock[date]['open'], last_price)

                    else: 
                        self.running_tally, self.running_tally_3x = self.calculate_current_return(stock[date]['close'], last_price)
                        last_price = stock[date]['close']
                        
                    self.add_running_tally_by_day_close_data(date, buy_and_sell_orders_by_day)
                        
            return self.running_tally_by_day, self.running_tally_by_day_3x  
#######################
#
# CALC DATA
#
#######################

class CalcData:
    
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
        self.stock = LoadStock().load_stock_data(self.Assumptions)
        self.Metrics = Metrics(self.Assumptions, self.stock)
        self.date_ranges = [{'name': 'Entire Period', 'start_date': None, 'end_date': None},
                            {'name': 'Before Dot Com', 'start_date': "1999-03-10", 'end_date': "2000-03-10"},
                            {'name': 'Dot Com', 'start_date': "2000-03-10", 'end_date': "2002-10-04"},
                            {'name': 'Between Dot Com and Crisis', 'start_date': "2002-10-04", 'end_date': "2008-05-01"},
                            {'name': 'Financial Crisis', 'start_date': "2008-05-01", 'end_date': "2009-03-20"},
                            {'name': 'End Crisis to Pandemic', 'start_date': "2009-03-20", 'end_date': "2020-02-10"},
                            {'name': 'Top Pandemic to Bottom', 'start_date': "2020-02-10", 'end_date': "2020-03-23"},
                            {'name': 'Bottom Pandemic to Today', 'start_date': "2020-03-23", 'end_date': "2021-01-19"}]
        
    def create_spreadsheet_of_strategy_and_metrics_by_timeperiod_for_specific_strategy(self):
        data_for_excel = {}

        for date_range in self.date_ranges: #for each date range compile list of excel data separately
            stock, Triggers, Combos, Returns = CalcData(date_range['start_date'], date_range['end_date'], self.stock, self.Assumptions, self.Metrics).calc_triggers_combos_and_returns()
            data = create_view_strategy_alongside_relevant_metrics_by_day_data(self.strategy_to_see,
                                                            stock,
                                                            self.Assumptions,
                                                            self.Metrics,
                                                            Triggers,
                                                            Returns)
            data_for_excel[date_range['name']] = data
            
        empty = write_view_strategy_alongside_relevant_metrics_by_day_to_excel(data_for_excel, self.Assumptions) #write lists to excel

    def print_report_to_IDE(self, start_date, end_date):
        stock, Triggers, Combos, Returns = CalcData(start_date, end_date, self.stock, self.Assumptions, self.Metrics).calc_triggers_combos_and_returns()
        for attribute in [a for a in dir(Returns) if not a.startswith('__')]:
            print(attribute)

            try:
                strategy_returns = getattr(Returns,attribute)
                running_tally_by_day = strategy_returns.running_tally_by_day
                running_tally_by_day_3x = strategy_returns.running_tally_by_day_3x

                print("No Leverage: " + str(get_last_item_in_dictionary_of_dictionaries(running_tally_by_day, 'close_running_tally')))
                print("With Leverage: " + str(get_last_item_in_dictionary_of_dictionaries(running_tally_by_day_3x, 'close_running_tally')))

            except:
                print("No Leverage: 1")
                print("With Leverage: 1")
            print()
            print()


#######################
#
# REPORTS
#
#######################

start_date = None #for custom dates, use this format: "1999-03-10".  For the entire data set, use None for start and end date
end_date = None
strategy_to_see = "combo_8"

Reports = GenerateReports(strategy_to_see)
Reports.print_report_to_IDE(None, None)
Reports.create_spreadsheet_of_strategy_and_metrics_by_timeperiod_for_specific_strategy()



# CHANGE THESE FIRST

startDate = df['Date'].dt.date.min()
date_filter = daysElapsed + datetime(startDate)




import pandas as pd
from datetime import datetime
import sys 
sys.setrecursionlimit(10**7)

# Step 1: Improve the dataframe and check the dates are in correct format, and also the prices in Rs
file_path_da = '/Users/akshat.singhlohum.com/Desktop/PROJECTS/IEX/DataAnalysis/DA_Clean_With_MA.xlsx'
df = pd.read_excel(file_path_da) 

df['MCP'] = df['MCP']/1000
df['Price_MA_12'] = df['Price_MA_12']/1000
df['Price_MA_8'] = df['Price_MA_8']/1000
df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
df = df[~((df['Date'].dt.year == 2024) & (df['Date'].dt.month == 4))]

startDate = df['Date'].dt.date.min()

#df['Month'] = df['Date'].dt.month
#df['Year'] = df['Date'].dt.year 
#df['DateNo'] = df['Date'].dt.day

riskFreeRate = 0.04/365

# Helps calculate the factor by which the time value of money has degraded. This is in excess of 1, so divide this factor to get the real value in starting date's time
def tvm(interestRate, date1=None, date2=None, days_diff=None): 
    # If days_diff is provided, use it directly
    if days_diff is not None:
        if not isinstance(days_diff, int):
            raise ValueError("days_diff must be an integer")
        diff = days_diff
    # If date1 and date2 are provided, calculate the difference in days
    elif date1 is not None and date2 is not None:
        if not isinstance(date1, datetime) or not isinstance(date2, datetime):
            raise ValueError("date1 and date2 must be datetime objects")
        diff = abs((date2 - date1).days)
    else:
        raise ValueError("You must provide either days_diff or both date1 and date2")
    
    return (1+interestRate) ** diff

# This is a helper function to help the profit DP function calculate the profits
def solve(startidx , action , BuyDF, SellDF, noTrades, coolDownAfterBuy , coolDownAfterSell):

    global dp

    len_BuyDF = len(BuyDF)
    if (startidx > len_BuyDF-1) :
        return 0

    if (startidx, action) in dp:
        return dp[(startidx, action)]


    if action == -1:
        curr1 = -BuyDF[startidx]    + solve(startidx+1+coolDownAfterBuy,    1,  BuyDF, SellDF, noTrades,    coolDownAfterBuy , coolDownAfterSell) #BUY
        curr2 = 0                   + solve(startidx+1,                     -1, BuyDF, SellDF, noTrades,    coolDownAfterBuy , coolDownAfterSell) # Do nothing
    elif action == 1:
        curr1 = SellDF[startidx]    + solve(startidx+1+coolDownAfterSell,   -1, BuyDF, SellDF, noTrades-1,  coolDownAfterBuy , coolDownAfterSell) # SELL
        curr2 = 0                   + solve(startidx+1,                     1,  BuyDF, SellDF, noTrades,    coolDownAfterBuy , coolDownAfterSell) # Do nothing

    curr = max(curr1, curr2)    
    dp[(startidx, action)] = curr
    return curr

# This is the total profit given we pass the sell and the buy arrays and mention no of trades
def calculateProfit(BuyDF, SellDF, noTrades, coolDownAfterBuy = 12, coolDownAfterSell = 8):    
    a = len(BuyDF)
    if a<2:
        return 0

    global dp
    dp = {}
    # start_idx, next action = buy/sell(-1 or +1), array
    ans = solve(0, -1, BuyDF, SellDF, noTrades, coolDownAfterBuy , coolDownAfterSell) 
    
    if dp == {}:
        return 0

    ans = dp[(0, -1)]
    dp = {}
    
    return ans

results ={} # This shall store the date_trades vs profit distinction

#Calculates the results dictionary to calculate a,b,c
for date_df in df['Date'].dt.date.unique():
    for trades in range(1,4):
        key_results = str(date_df) + '_'+ str(trades)
        # Slice and give BuyDF and SellDF
        
        BuyDF  = df[df['Date'].dt.date == date_df]['Price_MA_12'].to_numpy()
        SellDF = df[df['Date'].dt.date == date_df]['Price_MA_8'].to_numpy()

        profitsToday =  calculateProfit(BuyDF, SellDF, trades)
        results[key_results] = profitsToday

# This shall tell us the frequency of no of trades that make up for an optimal path
mostFrequentDuration = {0:0, 1:0, 2:0, 3:0}

#DP to calculate the actual path for max IRR
def calculateResidualValue(cyclesRemaining, daysElapsed, IRR):
    if daysElapsed == 1825:
        return 2*cyclesRemaining / tvm(IRR, 1825)
    
    elif (cyclesRemaining, daysElapsed) in dp:
        return dp[(cyclesRemaining, daysElapsed)]
    
    date_filter = daysElapsed + datetime(startDate)
    BuyDF  = df[df['Date'].dt.date == date_filter]['Price_MA_12'].to_numpy()
    SellDF  = df[df['Date'].dt.date == date_filter]['Price_MA_8'].to_numpy()

    
    noCycle     = calculateResidualValue(cyclesRemaining,   daysElapsed+1)
    oneCycle    = calculateResidualValue(cyclesRemaining-1, daysElapsed+1)
    twoCycle    = calculateResidualValue(cyclesRemaining-2, daysElapsed+1)
    threeCycle  = calculateResidualValue(cyclesRemaining-3, daysElapsed+1)

    Profit0 = 0
    Profit1 = calculateProfit(BuyDF, SellDF, 1) /tvm(IRR, days_diff = daysElapsed) # Function to retrieve a,b,c
    Profit2 = calculateProfit(BuyDF, SellDF, 2) /tvm(IRR, days_diff = daysElapsed)
    Profit3 = calculateProfit(BuyDF, SellDF, 3) /tvm(IRR, days_diff = daysElapsed)

    profits =  [Profit0 + noCycle, Profit1 + oneCycle, Profit2 + twoCycle, Profit3 + threeCycle] 
    profits_max = max(profits)

    for i in range(len(profits)):
        if profits[i] == profits_max:
            mostFrequentDuration[i] = mostFrequentDuration[i] + 1

    return profits_max 


surplus_dict = {}
surplus = 0

for IRR in range(0.05,0.55, 0.05):
    IRR_Derived = calculateResidualValue(6000, 0, IRR)
    surplus_dict[IRR] = IRR_Derived 

print(surplus_dict)

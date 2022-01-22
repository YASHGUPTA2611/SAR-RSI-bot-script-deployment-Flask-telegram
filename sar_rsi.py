import ta
import requests
from flask import Flask
import config
from config import in_position
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from ta.trend import PSARIndicator
import ccxt
from config import telegram_auth_token, telegram_group_id
import pandas as pd
import schedule
import time
from datetime import datetime
import schedule
import warnings
warnings.filterwarnings("ignore")
pd.set_option('display.max_rows', None)


app = Flask(__name__)

@app.route('/')
def hello():
    return 'Welcome to Giant_Leap executing orders'

@app.route('/giving_orders')
def giving_orders():
    exchange = ccxt.ftx({
    "apiKey": config.FTX_API_KEY,
    "secret": config.FTX_SECRET_KEY,
    "headers": { 'FTX-SUBACCOUNT': 'bot' },
    "enableRateLimit":True
    })

    def get_rsi(df, period=14):
        rsi= RSIIndicator(df['close'],period)
        df['rsi'] = rsi.rsi()

    def get_PSAR(df,step=0.05,max_step=0.5):
        psar = PSARIndicator(df['high'], df['low'], df['close'], step, max_step)
        df['psar'] = psar.psar()


    def condi(df, rsi_lower=50,rsi_upper=70):
        df['in_up_psar']=True
        df['in_rsi_lower']=True
        df['in_rsi_upper']=True

        for current in range(1,len(df.index)):
            if df['close'][current]>df['psar'][current]:
                df['in_up_psar'][current] = True
            else:
                df['in_up_psar'][current] = False
            if df['rsi'][current]<rsi_lower:
                df['in_rsi_lower'][current]=True
            else:
                df['in_rsi_lower'][current]=False
            if df['rsi'][current]>rsi_upper:
                df['in_rsi_upper'][current]=True
            else:
                df['in_rsi_upper'][current]=False
                
        return df
    


    def check_buy_sell_signals(df,amount):
        global in_position
        current=  len(df.index)-1
        
        if df['in_rsi_lower'][current]==True and df['in_up_psar'][current]==True:
            print("changed to uptrend : Buy")
            if in_position==False:
                order = exchange.create_order('LUNA-PERP',amount,'limit', 'buy',df['close'][current])
                print(order)
                telegram_api_url = f"https://api.telegram.org/bot{telegram_auth_token}/sendMessage?chat_id=@{telegram_group_id}&text={order}"
                tel_resp = requests.get(telegram_api_url)
                in_position = True
            else:
                print("already in postion")
        if df['in_rsi_upper'][current]==True and df['in_up_psar'][current]==False:
            print("changed to downtrend : Sell")
            if in_position==True:
                order = exchange.create_order('LUNA-PERP',amount, 'limit','sell',df['close']-df['atr'])
                print(order)
                telegram_api_url = f"https://api.telegram.org/bot{telegram_auth_token}/sendMessage?chat_id=@{telegram_group_id}&text={order}"
                tel_resp = requests.get(telegram_api_url)
                in_position = False
            else:
                print("You are't in position, nothing to sell")
        

    def run_bot():
        print(f"Fetching new bars for {datetime.now().isoformat()}")
        bars = exchange.fetch_ohlcv('LUNA-PERP', timeframe='15m', limit=365)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index(df['timestamp'], inplace=True)
        df.drop('timestamp', axis=1, inplace=True)
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'])
        df['atr'] = atr.average_true_range()
        df['atr'] = df['atr'] * (-1.05)
        get_PSAR(df)
        get_rsi(df)
        conditions = condi(df)
        print(conditions)
        check_buy_sell_signals(conditions,1)

    schedule.every(10).seconds.do(run_bot)
    
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)




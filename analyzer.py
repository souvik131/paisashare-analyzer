import mibian
import numpy as np
import json
from json import JSONEncoder
import math
import sys,os
import linecache
from flask import Flask, request, jsonify, make_response

analyzer = Flask(__name__)







def get_current_premium(type_of_option,underlying_price,strike,price,days_to_expiry,after_n_days,interest_rate,given_iv=None):
    try:
        if type_of_option=="CALL":
            if given_iv==None:
                if days_to_expiry>0:
                    iv = mibian.BS([underlying_price, strike, interest_rate, days_to_expiry], callPrice= price).impliedVolatility
                else:
                    iv = mibian.BS([underlying_price, strike, interest_rate, 1], callPrice= price).impliedVolatility
            else:
                iv = given_iv
            if (days_to_expiry-after_n_days)>0:
                bsm = mibian.BS([underlying_price, strike, interest_rate, days_to_expiry-after_n_days], volatility = iv)
            else:
                bsm = mibian.BS([underlying_price, strike, interest_rate, 1], volatility = iv)
            return {
                "price":bsm.callPrice,
                "delta":bsm.callDelta,
                "theta":bsm.callTheta,
                "vega":bsm.vega,
                "gamma":bsm.gamma,
                "type":"CALL"
            }
        else:
            if given_iv==None:
                if days_to_expiry>0:
                    iv = mibian.BS([underlying_price, strike, interest_rate, days_to_expiry], putPrice= price).impliedVolatility
                else:
                    iv = mibian.BS([underlying_price, strike, interest_rate, 1], putPrice= price).impliedVolatility
            else:
                iv = given_iv
            if (days_to_expiry-after_n_days)>0:
                bsm = mibian.BS([underlying_price, strike, interest_rate, days_to_expiry-after_n_days], volatility = iv)
            else:
                bsm = mibian.BS([underlying_price, strike, interest_rate, 1], volatility = iv)
            return {
                "price":bsm.putPrice,
                "delta":bsm.putDelta,
                "theta":bsm.putTheta,
                "vega":bsm.vega,
                "gamma":bsm.gamma,
                "type":"PUT"
            }
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        raise Exception('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))

def get_final_premium(type_of_option,underlying_price,strike,price):
    try:
        price=0
        if type_of_option=="CALL":
            if (underlying_price>strike):
                price=underlying_price-strike
            return {
                "price":price,
                "type":"CALL"
            }
        else:
            if (underlying_price<strike):
                price=strike-underlying_price
            return {
                "price":price,
                "type":"PUT"
            }
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        raise Exception('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))
    
def get_strategy_data(underlying_price,interest_rate,after_n_days,legs):
    try:
        strategy_data={
            "premium_pnl":0,
            "delta":0,
            "gamma":0,
            "theta":0,
            "vega":0
        }
        all_legs_data=[]
        for leg in legs:
            leg_data=get_current_premium(leg["type"],underlying_price,leg["strike"],leg["price"],leg["days_to_expiry"],after_n_days,interest_rate,leg["iv"])
            if leg["transaction_type"]=="SELL":
                strategy_data["premium_pnl"]+=(leg["executed_price"]-leg_data["price"])*leg["size"]*leg["lot_size"]
                strategy_data["delta"]-=leg_data["delta"]*leg["size"]*leg["lot_size"]
                strategy_data["gamma"]+=leg_data["gamma"]*leg["size"]*leg["lot_size"]
                strategy_data["theta"]-=leg_data["theta"]*leg["size"]*leg["lot_size"]
                strategy_data["vega"]-=leg_data["vega"]*leg["size"]*leg["lot_size"]
                leg["delta"]=leg_data["delta"]*leg["size"]*leg["lot_size"]
                leg["gamma"]=leg_data["gamma"]*leg["size"]*leg["lot_size"]
                leg["vega"]=-leg_data["vega"]*leg["size"]*leg["lot_size"]
                leg["theta"]=-leg_data["theta"]*leg["size"]*leg["lot_size"]
                all_legs_data.append(leg)
            else:
                strategy_data["premium_pnl"]+=(leg_data["price"]-leg["executed_price"])*leg["size"]*leg["lot_size"]
                strategy_data["delta"]+=leg_data["delta"]*leg["size"]*leg["lot_size"]
                strategy_data["gamma"]+=leg_data["gamma"]*leg["size"]*leg["lot_size"]
                strategy_data["theta"]+=leg_data["theta"]*leg["size"]*leg["lot_size"]
                strategy_data["vega"]+=leg_data["vega"]*leg["size"]*leg["lot_size"]
                leg["delta"]=leg_data["delta"]*leg["size"]*leg["lot_size"]
                leg["gamma"]=leg_data["gamma"]*leg["size"]*leg["lot_size"]
                leg["vega"]=leg_data["vega"]*leg["size"]*leg["lot_size"]
                leg["theta"]=leg_data["theta"]*leg["size"]*leg["lot_size"]
                all_legs_data.append(leg)
        return {"overall":strategy_data,"legs":all_legs_data}
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        raise Exception('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))

def get_premium_pnl(underlying_price,minimum_days_to_expiry,interest_rate,after_n_days,legs):
    try:
        current_premium_pnl=0
        final_premium_pnl=0
        for i,leg in enumerate(legs):
            leg_data_current=get_current_premium(leg["type"],underlying_price,leg["strike"],leg["price"],leg["days_to_expiry"],after_n_days,interest_rate,leg["iv"])
            if leg["days_to_expiry"]-minimum_days_to_expiry==0:
                leg_data_final=get_final_premium(leg["type"],underlying_price,leg["strike"],leg["price"])
            else:
                leg_data_final=get_current_premium(leg["type"],underlying_price,leg["strike"],leg["price"],leg["days_to_expiry"]-minimum_days_to_expiry,after_n_days,interest_rate,leg["iv"])
            if leg["transaction_type"]=="SELL":
                current_premium_pnl+=(leg["executed_price"]-leg_data_current["price"])*leg["size"]*leg["lot_size"]
                final_premium_pnl+=(leg["executed_price"]-leg_data_final["price"])*leg["size"]*leg["lot_size"]
            else:
                current_premium_pnl+=(leg_data_current["price"]-leg["executed_price"])*leg["size"]*leg["lot_size"]
                final_premium_pnl+=(leg_data_final["price"]-leg["executed_price"])*leg["size"]*leg["lot_size"]
        return {
            "current_premium_pnl":current_premium_pnl,
            "final_premium_pnl":final_premium_pnl
        }
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        raise Exception('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))


def get_payoff_graph(underlying_price,deviation_yearly,strike_difference,interest_rate,after_n_days,legs):
    try:
        maximum_strike = 0
        minimum_strike = 10000000000
        minimum_days_to_expiry = 10000000000
        for leg in legs:
            if minimum_strike>leg["strike"]:
                minimum_strike=leg["strike"]
            if maximum_strike<leg["strike"]:
                maximum_strike=leg["strike"]
            if minimum_days_to_expiry>leg["days_to_expiry"]:
                minimum_days_to_expiry=leg["days_to_expiry"]
                
        
        buffer=underlying_price*(5*deviation_yearly/(365/31))/100
        upper_limit=math.ceil((maximum_strike+buffer)/strike_difference)*strike_difference
        lower_limit=math.floor((minimum_strike-buffer)/strike_difference)*strike_difference+strike_difference
        current_premium_pnls=[]
        final_premium_pnls=[]
        prices=[]
        
        for price in range(lower_limit,upper_limit,strike_difference):
            pnls=get_premium_pnl(price,minimum_days_to_expiry,interest_rate,after_n_days,legs)
            prices.append(price)
            current_premium_pnls.append(pnls["current_premium_pnl"])
            final_premium_pnls.append(pnls["final_premium_pnl"])
        return {
            "prices":prices,
            "current_premium_pnls":current_premium_pnls,
            "final_premium_pnls":final_premium_pnls
        }
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        raise Exception('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))




def runBSM(spot_price,volatility,strike_difference,interest_rate,after_n_days,legs):
    try:
        strategy_data=get_strategy_data(spot_price,interest_rate,after_n_days,legs)
        payoff = get_payoff_graph(spot_price,volatility,strike_difference,interest_rate,after_n_days,legs)
        return {"strategy_data":strategy_data,"payoff":payoff}
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        raise Exception('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))


def findPNL(final_pnl,strategy_data):
    try:
        pnl_list=np.asarray(final_pnl)
        max_profit=np.max(pnl_list)
        max_loss=np.min(pnl_list)
        pnl_till_now=0
        legs= strategy_data["legs"]
        for i,leg in enumerate(legs):
            if leg["transaction_type"]=="SELL":
                legs[i]["pnl"]=(leg["executed_price"]-leg["price"])*leg["lot_size"]*leg["size"]
                pnl_till_now += legs[i]["pnl"]
                
            else:
                legs[i]["pnl"]=(leg["price"]-leg["executed_price"])*leg["lot_size"]*leg["size"]
                pnl_till_now += legs[i]["pnl"]
        buys=0
        sells=0
        for leg in legs:
            if leg["transaction_type"]=="SELL":
                sells+=1
            else:
                buys+=1
        if buys>sells:
            max_profit="Unlimited"
        elif sells>buys:
            max_loss="Unlimited"
        strategy_data["overall"]["max_profit"]=max_profit
        strategy_data["overall"]["max_loss"]=max_loss
        strategy_data["overall"]["pnl"]=pnl_till_now
        strategy_data["legs"]=legs
        return strategy_data
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        raise Exception('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))

def runAnalysis(spot_price,volatility,strike_difference,interest_rate,after_n_days,legs):
    try:
        bsm_data = runBSM(spot_price,volatility,strike_difference,interest_rate,after_n_days,legs)
        bsm_data["strategy_data"] = findPNL(bsm_data["payoff"]["final_premium_pnls"],bsm_data["strategy_data"])
        return bsm_data
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('{} EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        raise Exception('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj))









class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NpEncoder, self).default(obj)


analyzer.json_encoder=NpEncoder
@analyzer.route('/',methods=['POST'])
def index():
    try:
        request_data=request.json
        analysis_data = runAnalysis(request_data["spot"],request_data["iv"],request_data["strike_difference"],0,1,request_data["legs"])
        return make_response(jsonify({"status":"success","data":analysis_data}),200)
    except Exception as e:
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        print('EXCEPTION IN ({}, LINE {} "{}"): {}'.format(e,filename, lineno, line.strip(), exc_obj))
        return make_response(jsonify({"status":"failure","message":"Failed to process"}), 200)

if __name__ == '__main__':
    # Dev Running at 7000 and prod running at 6000
    analyzer.run(debug=True,host='127.0.0.1', port='7000')
    # analyzer.run(debug=True)


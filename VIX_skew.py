# -*- coding: utf-8 -*-
"""
Created on Thu Apr 11 22:07:40 2019

@author: Administrator
"""
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from WindPy import *
from datetime import timedelta
w.start()

from datetime import date

jintian=date.strftime(date.today(),'%Y-%m-%d')
dts = w.tdays("2015-02-10",jintian, "Period=Q").Data[0]



df = pd.DataFrame()

for i in range(len(dts)-1):
    st_str = dts[i].strftime("%Y-%m-%d")
    et = dts[i+1]-timedelta(1)
    et_str = et.strftime("%Y-%m-%d")
    
    print((st_str,et_str))
    
    _,df_price = w.wset("optiondailyquotationstastics","startdate="+st_str+";enddate="+et_str+";exchange=sse;windcode=510050.SH",usedf=True)
    
    df_price = df_price.sort_values('date')
    
    df = pd.concat([df, df_price])
    
df.to_csv('data/option_price.csv')


# 准备数据
def prepare_data():
    df_price = pd.read_csv('data/option_price.csv', index_col=0, parse_dates=['date'], dtype={'option_code':str})    
    
    _,df_con = w.wset("optioncontractbasicinfo","exchange=sse;windcode=510050.SH;status=all", usedf=True)
    con_col = df_con.columns.values
    con_col[0] = 'option_code'
    df_con.columns = con_col
    df_data = pd.merge(df_price, df_con, on='option_code')
    df_data['maturity']=(pd.DatetimeIndex(df_data['exercise_date'])-df_data['date'])/timedelta(365)
    
    use_cols = ['date','close','call_or_put','exercise_price','maturity']
    df_use = df_data[use_cols]
    df_use['date'] = [i.strftime("%Y-%m-%d") for i in df_use['date'].tolist()]
    df_use['call_or_put'] = df_use['call_or_put'].map({"认购":"call","认沽":"put"})
    
    df_use = df_use.sort_values('date')
    
    df_use.index = range(len(df_use))
    return df_use



# 选出当日的近远月合约(且到期日大于1周)
def filter_contract(cur_df):
    ex_t = cur_df['maturity'].unique() # 今天在交易的合约的到期日
    ex_t = ex_t[ex_t>7.0/365] # 选择到期日大于7天的数据
    
    jy_dt,cjy_dt = np.sort(ex_t)[0:2] # 到期日排序，最小两个为近月、次近月
    maturity_dict = dict(zip(['jy','cjy'],[jy_dt,cjy_dt]))
    cur_df = cur_df[cur_df['maturity'].isin([jy_dt,cjy_dt])] # 选取近月及次近月合约
    
    keep_cols = ['close','call_or_put', 'exercise_price']
    
    cur_df_jy = cur_df[cur_df["maturity"]==maturity_dict['jy']][keep_cols]
    cur_df_cjy = cur_df[cur_df["maturity"]==maturity_dict['cjy']][keep_cols]
        
    cur_df_jy = cur_df_jy.pivot_table(index='exercise_price',columns='call_or_put',values='close')
    cur_df_cjy = cur_df_cjy.pivot_table(index='exercise_price',columns='call_or_put',values='close')    
    
    cur_df_jy['diff'] = np.abs(cur_df_jy['call'] - cur_df_jy['put'])
    cur_df_cjy['diff'] = np.abs(cur_df_cjy['call'] - cur_df_cjy['put'])

    return maturity_dict, cur_df_jy, cur_df_cjy

# 计算远期价格
def cal_forward_price(maturity, rf_rate, df):
       
    min_con = df.sort_values('diff').head(1)
    
    k_min = min_con.index[0]
    
    f_price = k_min+np.exp(maturity*rf_rate)*(min_con['call']-min_con['put']).values[0]

    return f_price

# 计算中间价格
def cal_mid_price(maturity, df, forward_price):
    def _cal_mid_fun(x,val):        
        res = None
        if x['exercise_price']<val:
            res = x['put']
        elif x['exercise_price']>val:
            res = x['call']
        else:
            res = (x['put']+x['call'])/2
        return res
            
    m_k = nearest_k(df, forward_price) # 小于远期价格且最靠近的合约的行权价
    
    ret = pd.DataFrame(index=df.index)
    
    m_p_lst = df.reset_index().apply(lambda x: _cal_mid_fun(x,val=m_k),axis=1) # 计算中间件
    
    ret['mid_p'] = m_p_lst.values
    
    return ret

# 寻找最近合约
def nearest_k(df, forward_price):
    
    temp_df = df[df.index<forward_price] # 行权价小于远期价格的合约
    
    if temp_df.empty:
        
        temp_df = df
    
    m_k = temp_df.sort_values('diff').index[0]
    return m_k

# 计算行权价间隔
def cal_k_diff(df):
    arr_k = df.index.values
    ret = pd.DataFrame(index=df.index)
    res = []
    res.append(arr_k[1]-arr_k[0])
    res.extend(0.5*(arr_k[2:]-arr_k[0:-2]))
    res.append(arr_k[-1]-arr_k[-2])
    ret['diff_k'] = res
    return ret

# 计算VIX
def cal_vix_sub(df,forward_price,rf_rate,maturity, nearest_k):
    
    def _vix_sub_fun(x):        
        ret=x['diff_k']*np.exp(rf_rate*maturity)*x['mid_p']/np.square(x['exercise_price'])
        return ret
    
    temp_var = df.apply(lambda x:_vix_sub_fun(x),axis=1)
        
    sigma = 2*temp_var.sum()/maturity - np.square(forward_price/nearest_k-1)/maturity
    
    return sigma
        
# 计算近、次近月VIX
def cal_vix(df_jy,forward_price_jy,rf_rate_jy,maturity_jy, nearest_k_jy,df_cjy,forward_price_cjy,rf_rate_cjy,maturity_cjy, nearest_k_cjy):
    
    sigma_jy = cal_vix_sub(df_jy,forward_price_jy,rf_rate_jy,maturity_jy, nearest_k_jy)
    
    sigma_cjy = cal_vix_sub(df_cjy,forward_price_cjy,rf_rate_cjy,maturity_cjy, nearest_k_cjy)
    
    w = (maturity_cjy - 30.0/365)/(maturity_cjy - maturity_jy)
    
    to_sqrt = maturity_jy*sigma_jy*w+maturity_cjy*sigma_cjy*(1-w)
    
    vix = np.nan
    
    if to_sqrt.values[0]>=0:
        vix = 100*np.sqrt(to_sqrt*365.0/30)
    
    return vix

# 计算SKEW
def cal_skew(df_jy,forward_price_jy,rf_rate_jy,maturity_jy, nearest_k_jy,df_cjy,forward_price_cjy,rf_rate_cjy,maturity_cjy, nearest_k_cjy):
    s_jy = cal_moments_sub(df_jy,maturity_jy,rf_rate_jy,forward_price_jy, nearest_k_jy)
    s_cjy = cal_moments_sub(df_cjy,maturity_cjy,rf_rate_cjy,forward_price_cjy, nearest_k_cjy)
    
    w = (maturity_cjy - 30.0/365)/(maturity_cjy - maturity_jy)
    
    skew = 100 -10*(w*s_jy+(1-w)*s_cjy)
    
    return skew

    
def cal_epsilon(forward_price, nearest_k):
    
    e1 = -(1+np.log(forward_price/nearest_k)-forward_price/nearest_k)
    e2 = 2*np.log(forward_price/nearest_k)*(forward_price/nearest_k-1)+np.square(np.log(forward_price/nearest_k))*0.5
    e3 = 3*np.square(np.log(forward_price/nearest_k))*(np.log(forward_price/nearest_k)/3-1+forward_price/nearest_k)
    
    return e1, e2, e3

def cal_moments_sub(df,maturity,rf_rate,forward_price, nearest_k):
    e1, e2, e3 = cal_epsilon(forward_price, nearest_k)
    temp_p1 = -np.sum(df['mid_p']*df['diff_k']/np.square(df['exercise_price']))
    p1 = np.exp(maturity*rf_rate)*(temp_p1)+e1
    temp_p2 = np.sum(df['mid_p']*df['diff_k']*2*(1-np.log(df['exercise_price']/forward_price))/np.square(df['exercise_price']))
    p2 = np.exp(maturity*rf_rate)*(temp_p2)+e2
    temp_p3 = np.sum(df['mid_p']*df['diff_k']*3*(2*np.log(df['exercise_price']/forward_price)-np.square(np.log(forward_price/nearest_k)))/np.square(df['exercise_price']))
    p3 = np.exp(maturity*rf_rate)*(temp_p3)+e3
    
    s = (p3-3*p1*p2+2*p1**3)/(p2-p1**2)**(3/2)
    
    return s

    
def get_rf_rate_hist(start_dt, end_dt):
        
    error_code,df_rate = w.wsd("SHIBORON.IR,SHIBOR1W.IR,SHIBOR2W.IR,SHIBOR1M.IR,SHIBOR3M.IR,SHIBOR6M.IR,SHIBOR9M.IR,SHIBOR1Y.IR", "close", start_dt, end_dt, "", usedf=True)
    
    if error_code != 0:
        
        return "API Error {}".format(error_code)
    
    xx = np.arange(1,361) 
    x = [1,7,14,30,90,180,270,360]
    def interpld_fun(y):
        y_vals = y.values/100
        f =  interp1d(x,y_vals,kind='cubic')
        ts = pd.Series(data=f(xx),index=xx)
        return ts
    df_rate = df_rate.apply(lambda x: interpld_fun(x), axis=1)
    
    df_rate.index = pd.DatetimeIndex(df_rate.index)
    return df_rate



def main():
    vix_lst = []
    dt_lst = []
    skew_lst = []
    df_use = prepare_data()
    
    start_dt =  df_use['date'].values[0]
    end_dt =  df_use['date'].values[-1]
    
    df_rate = get_rf_rate_hist(start_dt, end_dt)
    
    i = 0
    
    for df_dt in df_use.groupby('date'):

        dt, df = df_dt
        # 合约过滤
        maturity, df_jy, df_cjy = filter_contract(df)
                
        # 获取无风险收益率
        if i%100 ==0:
            print(dt)
        rf_rate_jy = df_rate.loc[dt,int(maturity['jy']*365)]
        rf_rate_cjy = df_rate.loc[dt,int(maturity['cjy']*365)]

        # 计算远期价格
        fp_jy = cal_forward_price(maturity['jy'], rf_rate=0.035, df=df_jy)
        fp_cjy = cal_forward_price(maturity['cjy'], rf_rate=0.035, df=df_cjy)

        # 计算中间价格
        df_mp_jy = cal_mid_price(maturity['jy'], df_jy, fp_jy)
        df_mp_cjy = cal_mid_price(maturity['cjy'], df_cjy, fp_cjy)

        # 计算行权价差
        df_diff_k_jy =  cal_k_diff(df_jy)
        df_diff_k_cjy =  cal_k_diff(df_cjy)

        # 计算VIX
        df_tovix_jy = pd.concat([df_mp_jy,df_diff_k_jy],axis=1).reset_index()
        df_tovix_cjy = pd.concat([df_mp_cjy,df_diff_k_cjy],axis=1).reset_index()

        nearest_k_jy = nearest_k(df_jy, fp_jy)
        nearest_k_cjy = nearest_k(df_cjy, fp_cjy)
        
        vix = cal_vix(df_tovix_jy,fp_jy,rf_rate_jy,maturity['jy'], nearest_k_jy,df_tovix_cjy,fp_cjy,rf_rate_cjy,maturity['cjy'], nearest_k_cjy)
        
        skew = cal_skew(df_tovix_jy,fp_jy,rf_rate_jy,maturity['jy'], nearest_k_jy,df_tovix_cjy,fp_cjy,rf_rate_cjy,maturity['cjy'], nearest_k_cjy)
        
        dt_lst.append(dt)
        vix_lst.append(vix.values[0])
        skew_lst.append(skew.values[0])
        
        # 计算SKEW
        
        ret = pd.DataFrame(data={"VIX":vix_lst,"SKEW":skew_lst}, index=dt_lst)
        
        ret = ret.fillna(method='pad')
        
        ret = ret.sort_index()
        
        ret.index = pd.DatetimeIndex(ret.index)
        
        i += 1
        
    return ret



res = main()
import seaborn as se
res.plot(figsize=(15,10))
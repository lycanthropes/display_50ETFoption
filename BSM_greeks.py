#
# Black-Scholes-Merton (1973) European Call Option Greeks and Implied volatility

#
import math
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
from BSM_option_valuation import d1f, N, dN
mpl.rcParams['font.family'] = 'serif'
from scipy.stats import norm
#
# Functions for Greeks


# 期权看涨-看跌平价公式
def asset_price(c , p , K, r, t):  #计算标的资产价格
    S = c + K*math.exp(-r*t) - p
    return S

def BSM_call_delta(St, K, t, r, sigma):
    ''' Black-Scholes-Merton DELTA of European call option.

    Parameters
    ==========
    St : float
        stock/index level at time t
    K : float
        strike price
    t : float
        valuation date
    T : float
        date of maturity/time-to-maturity if t = 0; T > t
    r : float
        constant, risk-less short rate
    sigma : float
        volatility

    Returns
    =======
    delta : float
        European call option DELTA
    '''
    d1 = d1f(St, K, t, r, sigma)
    delta = N(d1)
    return delta


def BSM_put_delta(St,k,t,r,sigma):
    d1=d1f(St , k , t , r , sigma)
    delta=N(d1)-1
    return delta


def BSM_gamma(St, K, t, r, sigma):
    ''' Black-Scholes-Merton GAMMA of European call option.

    Parameters
    ==========
    St : float
        stock/index level at time t
    K : float
        strike price
    t : float
        valuation date
    T : float
        date of maturity/time-to-maturity if t = 0; T > t
    r : float
        constant, risk-less short rate
    sigma : float
        volatility

    Returns
    =======
    gamma : float
        European call option GAMM
    '''
    d1 = d1f(St, K, t, r, sigma)
    gamma = dN(d1) / (St * sigma * math.sqrt(t))
    return gamma


def BSM_call_theta(St, K, t, r, sigma):
    ''' Black-Scholes-Merton THETA of European call option.

    Parameters
    ==========
    St : float
        stock/index level at time t
    K : float
        strike price
    t : float
        valuation date
    T : float
        date of maturity/time-to-maturity if t = 0; T > t
    r : float
        constant, risk-less short rate
    sigma : float
        volatility

    Returns
    =======
    theta : float
        European call option THETA
    '''
    d1 = d1f(St, K, t, r, sigma)
    d2 = d1 - sigma * math.sqrt(t)
    theta = -(St * dN(d1) * sigma / (2 * math.sqrt(t)) + r * K * math.exp(-r * (t)) * N(d2))
    return theta


def BSM_put_theta(St,K,t,r,sigma):
    d1 = d1f(St, K, t, r, sigma)
    d2 = d1 - sigma * math.sqrt(t)
    theta = -St * dN(d1) * sigma / (2 * math.sqrt(t)) + r * K * math.exp(-r * (t)) * N(-d2)
    return theta


def BSM_call_rho(St, K, t, r, sigma):
    ''' Black-Scholes-Merton RHO of European call option.

    Parameters
    ==========
    St : float
        stock/index level at time t
    K : float
        strike price
    t : float
        valuation date
    T : float
        date of maturity/time-to-maturity if t = 0; T > t
    r : float
        constant, risk-less short rate
    sigma : float
        volatility

    Returns
    =======
    rho : float
        European call option RHO
    '''
    d1 = d1f(St, K, t, r, sigma)
    d2 = d1 - sigma * math.sqrt(t)
    rho = K * (t) * math.exp(-r * (t)) * N(d2)
    return rho


def BSM_put_rho(St,K,t,r,sigma):
    d1 = d1f(St, K, t, r, sigma)
    d2 = d1 - sigma * math.sqrt(t)
    rho = -K * (t) * math.exp(-r * (t)) * N(-d2)
    return rho
    

def BSM_vega(St, K, t, r, sigma):
    ''' Black-Scholes-Merton VEGA of European call option.

    Parameters
    ==========
    St : float
        stock/index level at time t
    K : float
        strike price
    t : float
        valuation date
    T : float
        date of maturity/time-to-maturity if t = 0; T > t
    r : float
        constant, risk-less short rate
    sigma : float
        volatility

    Returns
    =======
    vega : float
        European call option VEGA
    '''
    d1 = d1f(St, K, t, r, sigma)
    vega = St * dN(d1) * math.sqrt(t)
    return vega

#
# Plotting the Greeks
#

'''
def ImpVolCall(MktPrice, Strike, Expiry, Asset, IntRate, Dividend, error):
    for i in range(10000):
        imvol=0.0001*(i+1)
        diff=MktPrice-BSM_call_value(Asset, Strike, Expiry, IntRate, imvol)
        if abs(diff)<error:
            print(diff)
            break
    return imvol

def ImpVolPut(MktPrice,Strike,Expiry,Asset,IntRate,Dividend,error):
    for i in range(10000):
        imvol=0.0001*(i+1)
        diff=MktPrice-BSM_put_value(Asset, Strike, Expiry, IntRate, imvol)
        if abs(diff)<error:
            break
    return imvol    
'''    
def ImpVolCall(MktPrice, Strike, Expiry, Asset, IntRate, Dividend, Sigma, error):
    n = 1
    Volatility = Sigma   #初始值
    dv = error + 1
    while abs(dv) > error:
        d1 = np.log(Asset / Strike) + (IntRate - Dividend + 0.5 * Volatility **2) * Expiry
        d1 = d1 / (Volatility * np.sqrt(Expiry))
        d2 = d1 - Volatility * np.sqrt(Expiry)
        PriceError = Asset * math.exp(-Dividend * Expiry) * norm.cdf(d1) - Strike * math.exp(-IntRate * Expiry) * norm.cdf(d2) - MktPrice
        Vega1 = Asset * np.sqrt(Expiry / 3.1415926 / 2) * math.exp(-0.5 * d1 **2 )
        dv = PriceError / Vega1
        Volatility = Volatility - dv    #修正隐含波动率
        n = n + 1
        
        if n > 300:     #迭代次数过多的话
            ImpVolCall = 0.0
            break
        
        ImpVolCall = Volatility
    
    return ImpVolCall  



def ImpVolPut(MktPrice, Strike, Expiry, Asset, IntRate, Dividend, Sigma, error):
    n = 1
    Volatility = Sigma   #初始值
    dv = error + 1
    while abs(dv) > error:
        d1 = np.log(Asset / Strike) + (IntRate - Dividend + 0.5 * Volatility **2) * Expiry
        d1 = d1 / (Volatility * np.sqrt(Expiry))
        d2 = d1 - Volatility * np.sqrt(Expiry)
        PriceError = -Asset * math.exp(-Dividend * Expiry) * norm.cdf(-d1) + Strike * math.exp(-IntRate * Expiry) * norm.cdf(-d2) - MktPrice
        Vega1 = Asset * np.sqrt(Expiry / 3.1415926 / 2) * math.exp(-0.5 * d1 **2 )
        dv = PriceError / Vega1  
        Volatility = Volatility - dv      #修正隐含波动率
        n = n + 1

        if n > 300:     #迭代次数过多的话
            ImpVolPut = 0.0
            break

        ImpVolPut = Volatility

    return ImpVolPut

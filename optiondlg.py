# -*- coding: utf-8 -*-
"""
Created on Wed Apr 10 11:16:13 2019

@author: Administrator
"""

# -*- coding:utf-8 -*-
import os
os.chdir(r'C:\\Users\\Administrator.USER01607071755\\Desktop\\option_quote')
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.Qt import *
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot
import quote_option
import threading
import wsq
import globaldef
from WindPy import w
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas  # matplotlib对PyQt5的支持
from matplotlib.figure import Figure
from BSM_greeks import *
w.start()
import pandas as pd
MAC = True
try:
    from PyQt5.QtGui import qt_mac_set_native_menubar
except ImportError:
    MAC = False


from datetime import date, timedelta

jintian=date.strftime(date.today(),'%Y-%m-%d')
zuotian=date.strftime(date.today()-timedelta(1),'%Y-%m-%d')
# 如果wind API接口数据流量充足，可运行以下三行代码
#option_data = w.wset("optionchain","date="+jintian+";us_code=510050.SH;option_var=全部;call_put=全部")
#option_data = pd.DataFrame(option_data.Data, index=option_data.Fields, columns=option_data.Codes).T
#option_data=option_data.to_csv('option_data.csv')
# 如果API接口无数据流量，则可运行该行代码
option_data=pd.read_csv('option_data.csv',index_col=0)
option_data = option_data[['us_name','option_code','exe_type','strike_price','call_put','expiredate']]
option_data['expiredate'] = option_data['expiredate']/365      #年化剩余存续期
option_data['q'] = 0
# 取shibor三月期的利率收盘价，不能用未来函数，因此取昨天的收盘价。
_,shibor3=w.wss("SHIBOR3M.IR", "close","tradeDate="+zuotian+";priceAdj=U;cycle=D",usedf=True)
shibor3=shibor3.values[0][0]


class QuoteDlg(QDialog, quote_option.Ui_Form):

    def __init__(self, parent=None):
        super(QuoteDlg, self).__init__(parent)
        self.setupUi(self)

        self.setWindowTitle("Option calculations")
        self.updateUi()
        self.security_ID.setFocus()
        self.initGraph()

    def initGraph(self):
        self.scene = QGraphicsScene()
        self.dr = Figure_Canvas()
        self.scene.addWidget(self.dr)
        self.graphicsView.setScene(self.scene)

    @Slot()
    def on_subscribeButton_clicked(self):
        self.subscribeButton.setEnabled(False)
        self.cancel_subscribe_Button.setEnabled(True)
        self.info_stream.clear()
        globaldef.secID = []
        globaldef.indID = []
        globaldef.secID.extend([self.security_ID.text().upper(), self.security_ID2.text().upper()])
        globaldef.indID.extend(['rt_time'.upper(), 'rt_bid1'.upper(), 'rt_ask1'.upper(),
                                'rt_vol'.upper(),'rt_latest'.upper()])
        self.qThread = wsq.feeder()
        self.qThread.start()
        print("check point--01")
        self.qThread.update_data.connect(self.handle_display)
        print("check point--02")
        #self.qThread.update_data.connect(self.handle_graphic)
        #print("check point--03")
        # 增加希腊值的计算函数
        self.qThread.update_data.connect(self.greeks_display)
        #self.qThread.gengxin_price.connect(self.greeks_display)
        print("check point --04")

    def handle_display(self, data):
        # Update UI
        print(data)
        self.buy_one.setText(str(data[0][1]))
        self.buy_one2.setText(str(data[1][1]))
        self.sell_one.setText(str(data[0][2]))
        self.sell_one2.setText(str(data[1][2]))
        self.volume.setText(str(data[0][3]))
        self.volume2.setText(str(data[1][3]))
        self.security_du.setText(self.security_ID.text())
        self.security_du2.setText(self.security_ID2.text())
        self.newprice.setText(str(data[0][4]))
        self.newprice2.setText(str(data[1][4]))




    def handle_graphic(self, data):
        print(data)
       # self.dr.plot()
        
        
    def greeks_display(self,data):
        print(data)
        imvols=[0,0]
        deltas=[0,0]
        gammas=[0,0]
        vegas=[0,0]
        thetas=[0,0]
        rhos=[0,0]
        for i,elem in enumerate(globaldef.secID):
            nindex=option_data[option_data['option_code']==elem].index[0]
            strikes=option_data.at[nindex,'strike_price']
            remain_days=option_data.at[nindex,'expiredate']
            ky=option_data[(option_data['option_code']!=elem)&(option_data['strike_price']==strikes)&(option_data['expiredate']==remain_days)]
            mkt=data[i][4]
            if option_data.loc[nindex,'call_put']=='认购':
                _,p=w.wss(ky['option_code'].tolist(), "close","tradeDate="+jintian+";priceAdj=U;cycle=D",usedf=True)
                p=p.iat[0,0]
                r=shibor3/100
                S=asset_price(mkt,p,strikes,r,remain_days)
                sigma,error=1,0.001
                # 以下greeks函数都在BSM_greeks.py中。
                imvols[i]=ImpVolCall(mkt,strikes,remain_days,S,r,0,sigma,error)
                deltas[i]=BSM_call_delta(S, strikes, remain_days, r, imvols[i])
                gammas[i]=BSM_gamma(S, strikes, remain_days, r, imvols[i])
                vegas[i]=BSM_vega(S, strikes, remain_days, r, imvols[i])
                thetas[i]= BSM_call_theta(S, strikes, remain_days, r, imvols[i])
                rhos[i]=BSM_call_rho(S, strikes, remain_days, r, imvols[i])
            elif option_data.loc[nindex,'call_put']=='认沽':
                _,c=w.wss(ky['option_code'].tolist(), "close","tradeDate="+jintian+";priceAdj=U;cycle=D",usedf=True)
                c=c.iat[0,0]
                r=shibor3/100
                S=asset_price(c,mkt,strikes,r,remain_days)
                sigma,error=1,0.001
                imvols[i]=ImpVolPut(mkt, Strikes, remain_days, S, IntRate, 0, Sigma, error)
                deltas[i]=BSMBSM_put_delta(S,strikes,remain_days,r,imvols[i])
                gammas[i]=BSM_gamma(S, strikes, remain_days, r, imvols[i])
                vegas[i]=BSM_vega(S, strikes, remain_days, r, imvols[i])
                thetas[i]=BSM_put_theta(S,strikes,remain_days,r,imvols[i])
                rhos[i]=BSM_put_rho(S,strikes,remain_days,r,imvols[i])
        self.iv_1.setText(str(imvols[0]))       
        self.iv_2.setText(str(imvols[1]))
        self.delta_1.setText(str(deltas[0]))
        self.delta_2.setText(str(deltas[1]))
        self.gamma_1.setText(str(gammas[0]))
        self.gamma_2.setText(str(gammas[1]))
        self.vega_1.setText(str(vegas[0]))
        self.vega_2.setText(str(vegas[1]))
        self.theta_1.setText(str(thetas[0]))
        self.theta_2.setText(str(thetas[1]))
        self.rho_1.setText(str(rhos[0]))
        self.rho_2.setText(str(rhos[1])) 
        
        
        
        
        
    @Slot()
    def on_cancel_subscribe_Button_clicked(self):
        self.subscribeButton.setEnabled(True)
        self.cancel_subscribe_Button.setEnabled(False)
        self.qThread.finished()

    @Slot('QString')
    def on_security_ID_textEdited(self, text):
        self.updateUi()

    @Slot('QString')
    def on_security_ID2_textEdited(self, text):
        self.updateUi()

    def updateUi(self):
        enable = bool(self.security_ID.text()) and bool(self.security_ID2.text())
        self.subscribeButton.setEnabled(enable)
        self.cancel_subscribe_Button.setEnabled(enable)


class Figure_Canvas(FigureCanvas):
    # 通过继承FigureCanvas类，使得该类既是一个PyQt5的Qwidget
    # 又是一个matplotlib的FigureCanvas，这是连接PyQt5与matplotlib的关键
    def __init__(self, parent=None, width=7.4, height=5, dpi=100):
        # 创建一个Figure，注意：该Figure为matplotlib下的figure，不是matplotlib.pyplot下面的figure
        fig = Figure(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, fig)  # 初始化父类
        self.setParent(parent)
        # 调用figure下面的add_subplot方法，类似于matplotlib.pyplot下面的subplot方法
        self.axes1 = fig.add_subplot(311)
        #self.axes2 = fig.add_subplot(312)
        #self.axes3 = fig.add_subplot(313)

        # FigureCanvas.setSizePolicy(self,
        #                           QSizePolicy.Expanding,
        #                           QSizePolicy.Expanding)
        # FigureCanvas.updateGeometry(self)

    def plot(self):
        self.axes1.plot(globaldef.plotLast)
        # self.axes1.hold(False)
        self.axes1.grid(True)
        self.axes1.xaxis.set_visible(False)
        self.axes1.set_title("Real Time Spread_Last Trend Graph", fontsize=10)
        self.axes2.plot(globaldef.plotBid)
        # self.axes2.hold(False)
        self.axes2.grid(True)
        self.axes2.xaxis.set_visible(False)
        self.axes2.set_title("Real Time Spread_Bid Trend Graph", fontsize=10)
        self.axes3.plot(globaldef.plotAsk)
        # self.axes3.hold(False)
        self.axes3.grid(True)
        self.axes3.set_title("Real Time Spread_Ask Trend Graph", fontsize=10)
        self.draw()


if __name__ == "__main__":
    import sys
    app=QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    form = QuoteDlg()
    form.show()
    app.exec_()

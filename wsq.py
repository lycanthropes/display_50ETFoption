# -*- coding:utf-8 -*-
import threading
from WindPy import w
import globaldef
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import pyqtSlot as Slot


class feeder(QThread):
    update_data = Signal(object)
    gengxin_price=Signal(object)
    # def __init__(self, threadID, name):
    #    QThread.Thread.__init__(self)
    #    self.threadID = threadID
    #     self.name = name

    def run(self):
        w.start()
        secstring = ",".join(globaldef.secID)
        indstring = ",".join(globaldef.indID)
        w.wsq(secstring, indstring, func=self.myCallback)
        
    def finished(self):
        w.cancelRequest(0)

    def myCallback(self, indata):
        if indata.ErrorCode != 0:
            print('error code:' + str(indata.ErrorCode) + '\n')
            return ()

        for j in range(0, len(indata.Fields)):
            indindex = globaldef.indID.index(indata.Fields[j])
            for k in range(0, len(indata.Codes)):
                if indata.Codes[k] == globaldef.secID[0]:
                    globaldef.gdata[0][indindex] = indata.Data[j][k]
                if indata.Codes[k] == globaldef.secID[1]:
                    globaldef.gdata[1][indindex] = indata.Data[j][k]
                # R如果订阅的SecID较多，可以用下面方式获取数据
                # codeindex = globaldef.secID.index(indata.Codes[k])
                # globaldef.gdata[codeindex][indindex] = indata.Data[j][k]

        #globaldef.latest_price = [globaldef.gdata[0][4],globaldef.gdata[1][4]]
        self.update_data.emit(globaldef.gdata)
       # self.gengxin_price.emit(globaldef.latest_price)

        print("-----------------------------------")
        print(indata)


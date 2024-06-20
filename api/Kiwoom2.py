import time

import pandas as pd
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *


class Kiwoom2(QAxWidget):
    def __init__(self):
        super().__init__()
        self._make_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()
        self.account_number = self.get_account_number()

    def _make_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)
        self.OnReceiveTrData.connect(self._on_receive_tr_data)

    def _comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def _login_slot(self, err_code):
        if err_code == 0:
            print("Connected to server")
        else:
            print("Failed to connect to server")
        self.login_event_loop.exit()

    def get_account_number(self, tag="ACCNO"):
        account_list = self.dynamicCall("GetLoginInfo(QString)", tag)
        account_number = account_list.split(';')[0]
        return account_number

    def get_price_data(self, code):
        tr_data = self._request_tr_data(code)
        df = self._parse_tr_data(tr_data)
        return df

    def _request_tr_data(self, code):
        self.tr_event_loop = QEventLoop()
        self.has_next_tr_data = True
        self.tr_data = []

        while self.has_next_tr_data:
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
            self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
            self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 0, "0001")
            self.tr_event_loop.exec_()

        return self.tr_data

    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        tr_data_cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)

        if next == '2':
            self.has_next_tr_data = True
        else:
            self.has_next_tr_data = False

        if rqname == "opt10081_req":
            for i in range(tr_data_cnt):
                date = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "일자").strip()
                open_price = int(self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "시가"))
                high_price = int(self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "고가"))
                low_price = int(self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "저가"))
                close_price = int(self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "현재가"))
                volume = int(self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, rqname, i, "거래량"))

                self.tr_data.append({
                    'date': date,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })

        self.tr_event_loop.exit()

        time.sleep(0.5)


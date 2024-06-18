from PyQt5.QAxContainer import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import pandas as pd
import time

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._make_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()
        self.account_number = self.get_account_number()
        self.tr_event_loop = QEventLoop()                                                           # tr에 사용할 event_loop 변수

    # 레지스트리에서 API 정보 가지고 옴
    def _make_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    # 슬롯 생성
    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)                                               # OnEventConnect(변수) : OnEventConnect 처리결과가 변수로 전달
        self.OnReceiveTrData.connect(self._on_receive_tr_data)                                      # OnReceiveTrData(변수): Tr 리시버용 구현.  TR의 응답 결과를 변수로 전달
                                                                                                    # signal, slost
                                                                                                    # self.fileSelect.clicked.connect(self.selectFunction)
                                                                                                    # fileSelect.clicked 이벤트가 발생하면, selectFunction 슬롯을 실행
                                                                                                    # 형식 : 이벤트(슬롯)

    # 로그인 슬롯 발생
    def _login_slot(self, err_code):
        if err_code == 0:
            print("connected")
        else:
            print("not connected")

        self.login_event_loop.exit()                                                                #   loop.exit()   # 이벤트 루프 종료


    # 로그인 접속
    def _comm_connect(self):
        self.dynamicCall("CommConnect()")                                                           # dynamicCall()  <== request와 같은 동작
                                                                                                    # kiwoom API 함수를 직접 사용할 수 없어서, dynamicCall(API) 형식으로 사용
                                                                                                    # OCX 방식이기 때문에 API 호출 시 dynamicCall 사용
                                                                                                    # QAxWidget -> self.kiwoom -> dynamicCall(kiwoom API)

                                                                                                    # CommConnect(): 로그인창 출력
        self.login_event_loop = QEventLoop()                                                        # QEventLoop(): PyQt5 메소드. 이벤트 루프 객체 생성 해서 loop_event_loop로 전달
        self.login_event_loop.exec_()
                                                                                                    #
                                                                                                    #   loop = QEventLoop()
                                                                                                    #   loop.exec_()  # 이벤트 루프 시작
                                                                                                    #   이 메서드는 quit() 또는 exit()가 호출될 때까지 블로킹됩니다.

    def get_account_number(self, tag="ACCNO"):
        account_list = self.dynamicCall("GetLoginInfo(QString)", tag)
        account_number = account_list.split(';')[0]
        print(account_number)
        return account_number

    # 전체 종목코드 리스트 출력
    def get_code_list_by_market(self, market_type):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_type)
        code_list = code_list.split(';')[:-1]                                                       # list 형식으로 변환
        return code_list

    # 전체 종목이름 리스트 출력
    def get_master_code_name(self, code):
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return code_name



                                                                                                    # TR을 조회하기 전, 미리 각 TR 설명에서 몇가지 속성 지정을 요구함
                                                                                                    # opt10081 TR을 사용하기 위해서는 3가지 속성을 미리 설정해야 함
                                                                                                    #   self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
                                                                                                    #   self.dynamicCall("SetInputValue(QString, QString)", "기준일자", "20210726")
                                                                                                    #   self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")

    # [ OPT10081 : 주식일봉차트조회요청 ]
    def get_price_data(self, code):                                                                 #
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)                                    # TR(주식일봉차트조회) 시 해당 종목코드
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")                                  # TR(주식일봉차트조회) 시 검색 최종 기준일자
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 0, "0001")   # 해당 종목의 수정주가 여부 : 1 수정주가

        self.tr_event_loop.exec_()

        ohlcv = self.tr_data

        while self.has_next_tr_data:
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
            self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
            self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 2, "0001")
            self.tr_event_loop.exec_()

            for key, val in self.tr_data.items():
                ohlcv[key][-1:] = val

        df = pd.DataFrame(ohlcv, columns=['open', 'high', 'low', 'close', 'volume'], index=ohlcv['date'])

        return df[::-1]

    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):    # TR 조회의 응답 결과를 얻어 오는 함수
        print("[Kiwoom] _on_receive_tr_data is called {} / {} / {}".format(screen_no, rqname, trcode))
        tr_data_cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)

        if next == '2':
            self.has_next_tr_data = True
        else:
            self.has_next_tr_data = False

        if rqname == "opt10081_req":
            ohlcv = {'date': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}

            for i in range(tr_data_cnt):
                date = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "일자")
                open = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "시가")
                high = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "고가")
                low = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "저가")
                close = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                volume = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "거래량")

                ohlcv['date'].append(date.strip())
                ohlcv['open'].append(int(open))
                ohlcv['high'].append(int(high))
                ohlcv['low'].append(int(low))
                ohlcv['close'].append(int(close))
                ohlcv['volume'].append(int(volume))

            self.tr_data = ohlcv

        self.tr_event_loop.exit()
        time.sleep(0.5)
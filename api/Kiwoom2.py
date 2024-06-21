import time

import pandas as pd
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._make_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()
        self.account_number = self.get_account_number()

        self.tr_event_loop = QEventLoop()

    # 레지스트리에서 API 정보 가지고 옴
    def _make_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    # 슬롯 생성
    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)
        self.OnReceiveTrData.connect(self._on_receive_tr_data)

    # 로그인 슬롯 발생
    def _login_slot(self, err_code):
        if err_code == 0:
            print("connected")
        else:
            print("not connected")

        self.login_event_loop.exit()


    # 로그인 접속
    def _comm_connect(self):
        self.dynamicCall("CommConnect()")                                                           # CommConnect(): 로그인창 출력
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def get_account_number(self, tag="ACCNO"):
        account_list = self.dynamicCall("GetLoginInfo(QString)", tag)                               # 키움 API : GetLoginInfo
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


    # [ OPT10081 : 주식일봉차트조회요청 ]
    # TR요청을 1회하면, 600개씩 끊어서 18회 이벤트 동작
    def get_price_data(self, code):
        # 첫 TR처리. 600개 처리
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 0, "0001")   # 서버로 TR 요청 (TR요청 때는 인자 4개)
        self.tr_event_loop.exec_()

        ohlcv = self.tr_data

        # 2회차 TR 반복 처리. TR 1건 마다 600행 포함
        while self.has_next_tr_data:
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
            self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
            self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 2, "0001")
            self.tr_event_loop.exec_()                                                              # TR 1건씩 처리:1건에 600행

            for key, val in self.tr_data.items():
                ohlcv[key][-1:] = val                                                               # 기존 딕셔너리 마지막에 추가. 각 컬럼(6) * 600건씩 처리

        df = pd.DataFrame(ohlcv, columns=['open', 'high', 'low', 'close', 'volume'], index=ohlcv['date'])

        return df[::-1]



    # OnReceiveTrData 시그널에 의한 슬롯 처리  <= TR 수신 시 메인 처리 모듈
    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2,unused3, unused4):
        # 수신된 TR 정보 출력
        print("[Kiwoom] _on_receive_tr_data is called {} / {} / {}".format(screen_no, rqname, trcode))
        tr_data_cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)            # GetRepeatCnt : 수신된 TR의 Row Count
        # print("[Kiwoom] tr_data_cnt: %s " % tr_data_cnt)
        # print("[Kiwoom] OnReceiveTrData.next : %s" % next)

        # TR 다음 데이터가 추가로 있는지 검사
        if next == '2':
            self.has_next_tr_data = True
        else:
            self.has_next_tr_data = False

        # TR : opt10081 (주식일봉차트조회요청)
        if rqname == "opt10081_req":
            ohlcv = {'date': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}      # 임시 처리용 딕셔너리 생성

            # TR 1건 처리(주식일봉차트조회요청는 TR 1건이 600행)
            for i in range(tr_data_cnt):
                # 1) TR로부터 항목별 값을 받아와서 임시 변수에 저장

                print("i : %s " % i)
                date = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "일자")
                open = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "시가")
                high = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "고가")
                low = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "저가")
                close = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                volume = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "거래량")

                # 2) 딕셔너리에 저장(ohlcv)
                ohlcv['date'].append(date.strip())
                ohlcv['open'].append(int(open))
                ohlcv['high'].append(int(high))
                ohlcv['low'].append(int(low))
                ohlcv['close'].append(int(close))
                ohlcv['volume'].append(int(volume))

            #  3) 객체(self.tr_data)에 저장
            self.tr_data = ohlcv                                                                    # 임시 저장용 딕셔너리를 객체에 저장


        # TR: 예수금 조회 (opw00001)
        elif rqname == "opw00001_req":
            deposit = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, 0, "주문가능금액")
            self.tr_data = int(deposit)
            print(self.tr_data)



        self.tr_event_loop.exit()                                                                   # TR 슬롯 호출지점 복귀 (멀티행일 경우 재실행)
        time.sleep(0.5)


    # 예수금 얻어오기
    def get_deposit(self):                                                                          #------ 조회 대상 계좌의 예수금을 얻어 오는 함수
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_number)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "2")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opw00001_req", "opw00001", 0, "0002")

        self.tr_event_loop.exec_()
        return self.tr_data
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
        # 첫 600개 처리
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 0, "0001")   # 서버로 TR 요청 (TR요청 때는 인자 4개)
                                                                                                                # TR 반환때는 (OnReceiveTrData)는 인자 9개
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


    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2,unused3, unused4):  # OnReceiveTrData 이벤트가 반환한 값 형식을 구현
        print("[Kiwoom] _on_receive_tr_data is called {} / {} / {}".format(screen_no, rqname, trcode))
        tr_data_cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)            # GetRepeatCnt : 수신된 TR의 Row Count

        if next == '2':
            self.has_next_tr_data = True
        else:
            self.has_next_tr_data = False

        if rqname == "opt10081_req":
            ohlcv = {'date': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}      # 임시 처리용 딕셔너리 생성

            # 받아온 TR 값을(멀티행)을 항목별로 임시변수에 저장 => 딕셔너리에 저장(ohlcv) => 객체(self.tr_data)에 저장
            for i in range(tr_data_cnt):
                # TR로부터 항목별 값을 받아와서 임시 변수에 저장
                date = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "일자")
                open = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "시가")
                high = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "고가")
                low = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "저가")
                close = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                volume = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "거래량")
                                                                                                    # 1) Open API 조회 함수 입력값을 설정합니다. (사전처리)
                                                                                                    #     종목코드 = 전문 조회할 종목코드
                                                                                                    #     SetInputValue("종목코드"	,  "입력값 1");

                                                                                                    #     기준일자 = YYYYMMDD (연도4자리, 월 2자리, 일 2자리 형식)
                                                                                                    #     SetInputValue("기준일자"	,  "입력값 2");

                                                                                                    #     수정주가구분 = 0 or 1, 수신데이터 1:유상증자, 2:무상증자, 4:배당락, 8:액면분할, 16:액면병합, 32:기업합병, 64:감자, 256:권리락
                                                                                                    #     SetInputValue("수정주가구분"	,  "입력값 3");

                                                                                                    # 2) Open API 조회 함수를 호출해서 전문을 서버로 전송합니다. (TR 요청)
                                                                                                    #    CommRqData( "RQName"	,  "OPT10081"	,  "0"	,  "화면번호");

                                                                                                    # 3) TR 데이터 수신
                                                                                                    #    GetCommData(
                                                                                                    #               BSTR strTrCode,   // TR 이름
                                                                                                    #               BSTR strRecordName,   // 레코드이름
                                                                                                    #               long nIndex,      // nIndex번째
                                                                                                    #               BSTR strItemName) // TR에서 얻어오려는 출력항목이름
                                                                                                    #
                                                                                                    #  OnReceiveTRData()이벤트가 발생될때 수신한 데이터를 얻어오는 함수입니다.
                                                                                                    #  이 함수는 OnReceiveTRData()이벤트가 발생될때 그 안에서 사용해야 합니다.
                # 저장된 임시변수 값을 딕셔너리에 저장
                ohlcv['date'].append(date.strip())
                ohlcv['open'].append(int(open))
                ohlcv['high'].append(int(high))
                ohlcv['low'].append(int(low))
                ohlcv['close'].append(int(close))
                ohlcv['volume'].append(int(volume))

            self.tr_data = ohlcv                                                                    # 임시 저장용 딕셔너리를 객체에 저장

        self.tr_event_loop.exit()                                                                   # 600개 처리 후 루핑종료 => 다시 받아오는 동작 시행
                                                                                                    # self.tr_event_loop.exit()가 호출되면, 코드 실행이 exec_() 호출 이후의 지점으로 돌아감
        time.sleep(0.5)
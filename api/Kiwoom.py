import time

import pandas as pd
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._make_kiwoom_instance()
        self._set_signal_slots()                                                                    # Connect 이벤트, TR 리시버 이번트 생성
        self._comm_connect()
        self.account_number = self.get_account_number()
        self.tr_event_loop = QEventLoop()                                                           # QEventLoop : 루프 객체 생성 후 tr_event_loop로 전달

    # 레지스트리에서 API 정보 가지고 옴
    def _make_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    # 슬롯 생성
    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)                                               # OnEventConnect(변수) : 서버 Connect 시 작동 이벤트
        self.OnReceiveTrData.connect(self._on_receive_tr_data)                                      # OnReceiveTrData(변수): TR 반환 시 작동 이벤트

                                                                                                    # 형식  signal(slost)
                                                                                                    # self.fileSelect.clicked.connect(self.selectFunction)
                                                                                                    # 이벤트(OnReceiveTrData.connect)가 발생하면 슬롯(_on_receive_tr_data) 실행

    # 로그인 슬롯 발생
    def _login_slot(self, err_code):                                                                # self.OnEventConnect.connect(self._login_slot)에 의해서 대기 중에 Connect 이벤트가 발생하자 동작
        if err_code == 0:
            print("connected")
        else:
            print("not connected")

        self.login_event_loop.exit()                                                                #   _comm_connect에서 생성한  self.login_event_loop.exec_() 대기 루드 이벤트 종료


    # 로그인 접속
    def _comm_connect(self):
        self.dynamicCall("CommConnect()")                                                           # CommConnect(): 로그인창 출력
        self.login_event_loop = QEventLoop()                                                        # 루핑 이벤트 객체 생성(login_event_loop)
        self.login_event_loop.exec_()                                                               # 로그인 될 때까지 모든 코드 대기

                                                                                                    # loop = QEventLoop()    <== 대기 루프 이벤트 시작. quit() 또는 exit()가 호출될 때까지 모든 코드 중지
                                                                                                    # loop.exec_()           <== 이벤트 루프 시작

                                                                                                    # kiwoom API 함수를 직접 사용할 수 없어서, dynamicCall(API) 형식으로 사용
                                                                                                    # OCX 방식이기 때문에 API 호출 시 dynamicCall 사용
                                                                                                    # QAxWidget -> self.kiwoom -> dynamicCall(kiwoom API)

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
    def get_price_data(self, code):
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 0, "0001")   # 서버로 TR 요청
        self.tr_event_loop.exec_()                                                                  # 서버 응답올때까지 루프 시작


                                                                                                    # TR을 조회하기 전, 미리 각 TR 설명에서 몇가지 속성 지정을 요구함
                                                                                                    # opt10081 TR을 사용하기 위해서는 3가지 속성을 미리 설정해야 함
                                                                                                    #   self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
                                                                                                    #   self.dynamicCall("SetInputValue(QString, QString)", "기준일자", "20210726")
                                                                                                    #   self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
                                                                                                    # CommRqData(TR_별명, TR_No, 연속여부, "화면번호4자리")

                                                                                                    # TR: 키움서버로 데이터 요구단위
                                                                                                    # DynamicCall( "함수(변수)","변수값" )
                                                                                                    # DynamicCall( "함수(변수1, 변수2, 변수3, 변수4)", "변수1값", "변수2값", "변수3값", "변수4값" )
                                                                                                    # TR(주식일봉차트조회) 시 해당 종목코드
                                                                                                    # TR(주식일봉차트조회) 시 검색 최종 기준일자
                                                                                                    # 해당 종목의 수정주가 여부 : 1 수정주가
                                                                                                    # TR 요청을 보낸 후 응답 대기 상태로 만듬
                                                                                                    # self.tr_event_loop.exec_() 이후 코드는 TR에 대한 응답이 도착한 후 실행될 수 있습니다

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

    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2,unused3, unused4):  # TOnReceiveTrData 이벤트가 반환한 값 형식을 구현
        print("[Kiwoom] _on_receive_tr_data is called {} / {} / {}".format(screen_no, rqname, trcode))
        tr_data_cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)            # GetRepeatCnt : 수신된 TR의 Row Count

        if next == '2':
            self.has_next_tr_data = True
        else:
            self.has_next_tr_data = False

        if rqname == "opt10081_req":
            ohlcv = {'date': [], 'open': [], 'high': [], 'low': [], 'close': [],
                     'volume': []}  # 딕셔너리

            for i in range(tr_data_cnt):
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

                ohlcv['date'].append(date.strip())
                ohlcv['open'].append(int(open))
                ohlcv['high'].append(int(high))
                ohlcv['low'].append(int(low))
                ohlcv['close'].append(int(close))
                ohlcv['volume'].append(int(volume))

            self.tr_data = ohlcv

        self.tr_event_loop.exit()
        time.sleep(0.5)
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

        self.tr_event_loop = QEventLoop()                                                           # 전 처리(절차적 처리)를 다 마치고, 이벤트 대기 루핑 객체 생성 후 main으로 복귀
                                                                                                    # QEventLoop : 루프 객체 생성 후 tr_event_loop로 전달
                                                                                                    # 객체만 생성하고 로핑 실행은 아직 안했음
                                                                                                    # 루프 객체 생성 후 tr_event_loop로 전달
                                                                                                    # tr_event_loop.exec_()     <== 루핑 시작
                                                                                                    # tr_event_loop.exec()      <== 루핑 종료

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
    def _login_slot(self, err_code):                                                                # self.OnEventConnect.connect(self._login_slot)에 의해서 대기 중에,  Connect 이벤트가 발생하면 _login_slot 동작
        if err_code == 0:
            print("connected")
        else:
            print("not connected")

        self.login_event_loop.exit()                                                                # _comm_connect에서 생성한  self.login_event_loop.exec_() 대기 루드 이벤트 종료


    # 로그인 접속
    def _comm_connect(self):
        self.dynamicCall("CommConnect()")                                                           # CommConnect(): 로그인창 출력
        self.login_event_loop = QEventLoop()                                                        # 루핑 이벤트 객체 생성(login_event_loop)
        self.login_event_loop.exec_()                                                               # 로그인 될 때까지 모든 코드 대기

                                                                                                    # loop = QEventLoop()    <== 대기 루프 이벤트 객체 생성 == > 대기 루핑 시작. quit() 또는 exit()가 호출될 때까지 모든 코드 중지
                                                                                                    # loop.exec_()           <== 이벤트 루프 시작

                                                                                                    # kiwoom API 함수를 직접 사용할 수 없어서, dynamicCall(API) 형식으로 사용
                                                                                                    # OCX 방식이기 때문에 API 호출 시 dynamicCall 사용
                                                                                                    # QAxWidget -> self.kiwoom -> dynamicCall(kiwoom API)

    def get_account_number(self, tag="ACCNO"):
        account_list = self.dynamicCall("GetLoginInfo(QString)", tag)                               # 키움 API : GetLoginInfo
        account_number = account_list.split(';')[0]
        print(account_number)
        return account_number
                                                                                                    # [LONG GetLoginInfo()]
                                                                                                    #
                                                                                                    # 로그인 후 사용할 수 있으며 인자값에 대응하는 정보를 얻을 수 있습니다.
                                                                                                    #
                                                                                                    # 인자는 다음값을 사용할 수 있습니다.
                                                                                                    #
                                                                                                    # "ACCOUNT_CNT" : 보유계좌 갯수를 반환합니다.
                                                                                                    # "ACCLIST" 또는 "ACCNO" : 구분자 ';'로 연결된 보유계좌 목록을 반환합니다.
                                                                                                    # "USER_ID" : 사용자 ID를 반환합니다.
                                                                                                    # "USER_NAME" : 사용자 이름을 반환합니다.
                                                                                                    # "GetServerGubun" : 접속서버 구분을 반환합니다.(1 : 모의투자, 나머지 : 실거래 서버)
                                                                                                    # "KEY_BSECGB" : 키보드 보안 해지여부를 반환합니다.(0 : 정상, 1 : 해지)
                                                                                                    # "FIREW_SECGB" : 방화벽 설정여부를 반환합니다.(0 : 미설정, 1 : 설정, 2 : 해지)


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
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 0, "0001")   # 서버로 opt10081번 TR 요청
        self.tr_event_loop.exec_()                                                                  # 서버 응답올 때까지 대기 루프 시작 : def __init__(self):에서 루프 객체 생성

                                                                                                    # OS의 이벤트를 기다림
                                                                                                    # 위 에서 선언한 OnReceiveTrData에 의해 TR response 발생하면  _on_receive_tr_data 실행
                                                                                                    # def _set_signal_slots(self):
                                                                                                    #         self.OnEventConnect.connect(self._login_slot)
                                                                                                    #         self.OnReceiveTrData.connect(self._on_receive_tr_data)

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
                                                                                                    # [pandas DataFrame 형식]
                                                                                                    # date = ['16.02.29', '16.02.26', '16.02.25', '16.02.24', '16.02.23']
                                                                                                    # daeshin_day = DataFrame(daeshin, columns=['open', 'high', 'low', 'close'], index=date)
                                                                                                    # 새롭게 생성된 DataFrame 객체의 출력 값을 확인해 봅시다. 이번에는 그림 13.9와 일자도 일치하는 것을 확인할 수 있습니다.
                                                                                                    #
                                                                                                    #            open   high    low  close
                                                                                                    # 16.02.29  11650  12100  11600  11900
                                                                                                    # 16.02.26  11100  11800  11050  11600
                                                                                                    # 16.02.25  11200  11200  10900  11000
                                                                                                    # 16.02.24  11100  11100  10950  11100
                                                                                                    # 16.02.23  11000  11150  10900  11050
        return df[::-1]

    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2,unused3, unused4):  # TOnReceiveTrData 이벤트가 반환한 값 형식을 구현
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
        time.sleep(0.5)
import time

import pandas as pd
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from util.const import *


class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        self._make_kiwoom_instance()
        self._set_signal_slots()
        self._comm_connect()
        self.account_number = self.get_account_number()

        self.tr_event_loop = QEventLoop()

        ## 변수 정의
        self.order = {}                                                                             # 주문정보 (종목 코드, 주문정보)
        self.balance = {}                                                                           # 매수정보 (종목 코드, 매수정보)
        self.universe_realtime_transaction_info = {}                                                # 실시간 체결 정보


        # 레지스트리에서 API 정보 가지고 옴
    def _make_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")


    # 슬롯 생성 ############################################################
    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._login_slot)
        self.OnReceiveTrData.connect(self._on_receive_tr_data)                                      # TR 수신 데이터 처리

        self.OnReceiveMsg.connect(self._on_receive_msg)                                             # 주문 메시지를 _on_receive_msg로 받도록 설정
        self.OnReceiveChejanData.connect(self._on_chejan_slot)                                      # 주문 접수/체결 결과를 _on_chejan_slot으로 받도록 설정

        self.OnReceiveRealData.connect(self._on_receive_real_data)                                  # 실시간 체결 데이터를 _on_receive_real_data로 받도록 설정



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


    # 계좌번호 가져오기
    def get_account_number(self, tag="ACCNO"):
        account_list = self.dynamicCall("GetLoginInfo(QString)", tag)                               # 키움 API : GetLoginInfo
        account_number = account_list.split(';')[0]
        print("계좌번호: " , account_number)
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
    # 종목코드별 TR요청 처리 : 600행씩 ohlcv에 누적 후, self.tr_data에 저장
    def get_price_data(self, code):
        # 첫 TR처리. 600개 처리
        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 0, "0001")   # 서버로 TR 요청 (TR요청 때는 인자 4개), TR 반환때는 (OnReceiveTrData)는 인자 9개
        self.tr_event_loop.exec_()                                                                  # loop 시작  >> _on_receive_tr_data에서 self.tr_event_loop.exit() loop 종료

        ohlcv = self.tr_data


        # 2회차 TR 반복 처리. TR 1건 마다 600행 포함
        # self.has_next_tr_data = True
        while self.has_next_tr_data:
            self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
            self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
            self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10081_req", "opt10081", 2, "0001")
            self.tr_event_loop.exec_()                                                              # loop 시작  >> _on_receive_tr_data에서 self.tr_event_loop.exit() loop 종료

            for key, val in self.tr_data.items():
                ohlcv[key][-1:] = val                                                               # 기존 딕셔너리 마지막에 추가. 각 컬럼(6) * 600건씩 처리

        df = pd.DataFrame(ohlcv, columns=['open', 'high', 'low', 'close', 'volume'], index=ohlcv['date'])

        return df[::-1]                                                                             # 1개 종목 처리끝



    # OnReceiveTrData 시그널에 의한 슬롯 처리
    def _on_receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2,unused3, unused4):
        # 수신된 TR 정보 출력
        print("[Kiwoom TR처리] _on_receive_tr_data is called {} / {} / {}".format(screen_no, rqname, trcode))
        tr_data_cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)            # GetRepeatCnt : 수신된 TR의 Row Count

        # TR 다음 데이터가 추가로 있는지 검사
        if next == '2':
            self.has_next_tr_data = True
        else:
            self.has_next_tr_data = False

        # TR : opt10081 (주식일봉차트조회요청) : (시그널)OnReceiveTrData > (슬롯)_on_receive_tr_data 호출 > (슬롯매개변수)rqname=opt10081_req
        # TR(600행)을 (딕셔너리)ohlcv에 누적했다가 (객체)self.tr_data에 저장
        if rqname == "opt10081_req":
            ohlcv = {'date': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}      # 딕셔너리 생성 > 임시 보관용

            # TR 1건 처리(주식일봉차트조회요청는 TR 1건이 600행)
            for i in range(tr_data_cnt):
                # 1) TR로부터 항목별 값을 받아와서 임시 변수에 저장

                #print("i : %s " % i)
                date = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "일자")
                open = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "시가")
                high = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "고가")
                low = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "저가")
                close = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                volume = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "거래량")

                # 2) 딕셔너리에 저장(ohlcv) > 600행 누적
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


        # 주문 정보 확인 (opt10075)
        elif rqname == "opt10075_req":
            for i in range(tr_data_cnt):                                                            # 당일 주문정보가 여러 개
                code = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "종목코드")
                code_name = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "종목명")
                order_number = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문번호")
                order_status = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문상태")
                order_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문수량")
                order_price = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문가격")
                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                order_type = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "주문구분")
                left_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "미체결수량")
                executed_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "체결량")
                ordered_at = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "시간")
                fee = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "당일매매수수료")
                tax = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "당일매매세금")

                # 데이터 정리
                code = code.strip()
                code_name = code_name.strip()
                order_number = str(int(order_number.strip()))
                order_status = order_status.strip()
                order_quantity = int(order_quantity.strip())
                order_price = int(order_price.strip())
                current_price = int(current_price.strip().lstrip('+').lstrip('-'))
                order_type = order_type.strip().lstrip('+').lstrip('-')                             # +매수, -매도처럼 +, - 제거
                left_quantity = int(left_quantity.strip())
                executed_quantity = int(executed_quantity.strip())
                ordered_at = ordered_at.strip()

                # 세금 및 수수료 정리
                fee = int(fee)
                tax = int(tax)

                # 딕셔너리 추가
                self.order[code] = {
                    '종목코드': code,
                    '종목명': code_name,
                    '주문번호': order_number,
                    '주문상태': order_status,
                    '주문수량': order_quantity,
                    '주문가격': order_price,
                    '현재가': current_price,
                    '주문구분': order_type,
                    '미체결수량': left_quantity,
                    '체결량': executed_quantity,
                    '주문시간': ordered_at,
                    '당일매매수수료': fee,
                    '당일매매세금': tax
                }

            self.tr_data = self.order


        # 보유 종목 정보(잔고 정보)
        elif rqname == "opw00018_req":
            for i in range(tr_data_cnt):
                code                = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "종목번호")
                code_name           = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "종목명")
                quantity            = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "보유수량")
                purchase_price      = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "매입가")
                return_rate         = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "수익률(%)")
                current_price       = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "현재가")
                total_purchase_price= self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "매입금액")
                available_quantity  = self.dynamicCall("GetCommData(QString, QString, int, QString", trcode, rqname, i, "매매가능수량")

                code = code.strip()[1:]  # 데이터 형변환 및 가공
                code_name = code_name.strip()
                quantity = int(quantity)
                purchase_price = int(purchase_price)
                return_rate = float(return_rate)
                current_price = int(current_price)
                total_purchase_price = int(total_purchase_price)
                available_quantity = int(available_quantity)

                self.balance[code] = {
                    '종목명': code_name,
                    '보유수량': quantity,
                    '매입가': purchase_price,
                    '수익률': return_rate,
                    '현재가': current_price,
                    '매입금액': total_purchase_price,
                    '매매가능수량': available_quantity
                }

                self.tr_data = self.balance

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



    # 주문접수 - (1)주문 발생
    def send_order(self, rqname, screen_no, order_type, code, order_quantity, order_price, order_classification, origin_order_number=""):
        order_result = self.dynamicCall(
            "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
            [rqname, screen_no, self.account_number, order_type, code, order_quantity,
             order_price, order_classification, origin_order_number])
        return order_result

    # 주문 확인 메세지
    def _on_receive_msg(self, screen_no, rqname, trcode, msg):
        print("[Kiwoom] _on_receive_msg is called {} / {} / {} / {}".format(screen_no, rqname, trcode, msg))


    # 체결 및 잔고
    def _on_chejan_slot(self, s_gubun, n_item_cnt, s_fid_list):
        print("[Kiwoom] _on_chejan_slot is called {} / {} / {}".format(s_gubun, n_item_cnt, s_fid_list))

        for fid in s_fid_list.split(";"):                                                           # fid 리스트를 ‘;’ 기준으로 분리
            if fid in FID_CODES:                                                                    # FID_CODES <== const.py에 딕셔너리로 정의되어 있음. fid가 FID_CODES에 있는지 검사
                code = self.dynamicCall("GetChejanData(int)", '9001')[1:]                           # 종목 코드를 얻어 와 앞자리 문자 제거[1:] 후 종목코드 변수에 저장

                data = self.dynamicCall("GetChejanData(int)",fid)                                   # fid를 사용하여 데이터 얻어 오기(예 fid:9203을 전달하면 주문 번호를 수신하여 data에 저장)
                data = data.strip().lstrip('+').lstrip('-')                                         # 데이터에 공백, +, -가 붙어 있으면( +매수, -매도) 제거 <== trim

                if data.isdigit():                                                                  # data 값이 숫자형식이면 정수형 변환 처리
                    data = int(data)

                item_name = FID_CODES[fid]                                                          # fid 코드에 해당하는 항목(item_name)을 찾음(예 fid=9201 > item_name=계좌번호)
                print("주문내역 = {} : {}".format(item_name, data))                                       # 얻어 온 데이터 출력(예 주문 가격: 37600)

                if int(s_gubun) == 0:                                                               # 접수/체결(s_gubun=0)이면 self.order,

                    if code not in self.order.keys():                                               # 아직 order에 종목 코드가 없다면 신규 생성하는 과정
                        self.order[code] = {}
                    self.order[code].update({item_name: data})                                      # order 딕셔너리에 데이터 저장

                elif int(s_gubun) == 1:                                                             # 잔고 이동이면 self.balance에 값 저장
                    if code not in self.balance.keys():                                             # 아직 balance에 종목 코드가 없다면 신규 생성하는 과정
                        self.balance[code] = {}
                    self.balance[code].update({item_name: data})                                    # order 딕셔너리에 데이터 저장

        if int(s_gubun) == 0:                                                                       # s_gubun 값에 따라 저장한 결과 출력
            print("* 주문 출력(self.order)")
            print(self.order)
        elif int(s_gubun) == 1:
            print("* 잔고 출력(self.balance)")
            print(self.balance)



    # 주문 정보 확인
    def get_order(self):
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_number)
        self.dynamicCall("SetInputValue(QString, QString)", "전체종목구분", "0")
        self.dynamicCall("SetInputValue(QString, QString)", "체결구분", "0")                          # 0:전체, 1:미체결, 2:체결
        self.dynamicCall("SetInputValue(QString, QString)", "매매구분", "0")                          # 0:전체, 1:매도, 2:매수
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opt10075_req", "opt10075", 0, "0002")

        self.tr_event_loop.exec_()
        return self.tr_data



    # 계좌 잔고 현황 (잔고: 체결 주식 현황)
    def get_balance(self):
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_number)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "opw00018_req", "opw00018", 0, "0002")

        self.tr_event_loop.exec_()
        return self.tr_data



    # 실시간 현황 조회
    def set_real_reg(self, str_screen_no, str_code_list, str_fid_list, str_opt_type):
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                         str_screen_no, str_code_list, str_fid_list, str_opt_type)
                                                                                                    # str_code_list 종목코드는 여러종목을 리스트 형식으로 가지고 옴
                                                                                                    # str_opt_type : 최초 등록, 추가 등록
        time.sleep(0.5)

    # 실시간 데이터 수신
    def _on_receive_real_data(self, s_code, real_type, real_data):                                  # real_type : 장 시작 시간 / 체결 정보
        if real_type == "장시작시간":
            pass

        elif real_type == "주식체결":
            signed_at = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("체결시간"))

            close = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid("현재가"))
            close = abs(int(close))

            high = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid('고가'))
            high = abs(int(high))

            open = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid('시가'))
            open = abs(int(open))

            low = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid('저가'))
            low = abs(int(low))

            top_priority_ask = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid('(최우선)매도호가'))
            top_priority_ask = abs(int(top_priority_ask))

            top_priority_bid = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid('(최우선)매수호가'))
            top_priority_bid = abs(int(top_priority_bid))

            accum_volume = self.dynamicCall("GetCommRealData(QString, int)", s_code, get_fid('누적거래량'))
            accum_volume = abs(int(accum_volume))

            print(s_code, signed_at, close, high, open, low, top_priority_ask, top_priority_bid,    # 5장에서는 삭제할 코드(출력부에 너무 많은 데이터가 나오기 때문에 여기서만 사용)
                  accum_volume)

            if s_code not in self.universe_realtime_transaction_info:                               # universe_realtime_transaction_info 딕셔너리에 종목 코드가 키 값으로 존재하지 않으면 생성(해당 종목 실시간 데이터를 최초로 수신할 때)
                self.universe_realtime_transaction_info.update({s_code: {}})

            self.universe_realtime_transaction_info[s_code].update(                                 # 최초 수신 이후 계속 수신되는 데이터는 update를 이용해서 값 갱신
                {
                    "체결시간": signed_at,
                    "시가": open,
                    "고가": high,
                    "저가": low,
                    "현재가": close,
                    "(최우선)매도호가": top_priority_ask,
                    "(최우선)매수호가": top_priority_bid,
                    "누적거래량": accum_volume
                })
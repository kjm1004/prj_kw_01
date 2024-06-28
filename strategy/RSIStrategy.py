from api.Kiwoom import *
from util.make_up_universe import *
from util.db_helper import *
from util.time_helper import *
import math
import traceback

class RSIStrategy(QThread):
    def __init__(self):
        QThread.__init__(self)
        self.strategy_name = "RSIStrategy"
        self.kiwoom = Kiwoom()
        self.universe ={}

        self.deposit = 0                                                                            # 계좌 예수금
        self.is_init_success = False                                                                # 초기화 함수 성공 여부 확인 변수

        self.init_strategy()

    def init_strategy(self):                                                                        # 전략 초기화 기능을 수행하는 함수
        try:
            self.check_and_get_universe()                                                           # 네이버 크롤링 > 유니버스 생성(종목명) > API와 조합 : 유니버스 내용 추가 생성(종목코드,종목명)
            self.check_and_get_price_data()                                                         # (테이블)유니버스에 최신 일봉테이터 처리
            self.kiwoom.get_order()                                                                 # 주문 정보 확인
            self.kiwoom.get_balance()                                                               # 잔고 확인
            self.deposit = self.kiwoom.get_deposit()                                                # 예수금 확인
            self.set_universe_real_time()                                                           # 유니버스 실시간 체결 정보 등록
            self.is_init_success = true

        except Exception as e:
            print(traceback.format_exc())

    def check_and_get_universe(self):

        # DB에 (테이블)universe 내용 검사
        #   1. 크롤링 목록에서 종목명을 이용해서 종목코드 추출
        #   2. 종목코드, 종목명, 추출일 > (테이블)universe 생성
        if not check_table_exist(self.strategy_name, 'universe'):

            # 네이버 크롤링 결과를 dataFrame('종목명')으로 가지고 옴 > list에 저장 (200개)
            # 크롤링 목록에는 종목코드가 없음
            universe_list = get_universe()                                                          # get_universe() <== 네이버 증권 크롤링 결과에 필터 후 200개 선정 > 리스트 반환
            print(universe_list)

            universe = {}
            now = datetime.now().strftime("%Y%m%d")                                                 # 오늘 날짜를 20210101 형태로 지정

            # API로부터 KOSPI(0)/KOSDAQ(10)에 상장된 모든 종목 코드를 가져와 kospi_code_list에 저장
            kospi_code_list = self.kiwoom.get_code_list_by_market("0")
            kosdaq_code_list = self.kiwoom.get_code_list_by_market("10")

            # 모든 종목 코드를 대상으로 처리
            # 유니버스 크롤링 목록의 종목명을 이용해서 종목코드 추출
            for code in kospi_code_list + kosdaq_code_list:
                code_name = self.kiwoom.get_master_code_name(code)                                  # 모든 상장사의 종목 코드에서 종목명을 얻어 옴

                if code_name in universe_list:                                                      # 해당 상장자의 종목명이 유니버스에 포함되어 있다면 (딕셔너리)universe에 추가
                    universe[code] = code_name

                universe_df = pd.DataFrame({                                                        # 코드, 종목명, 생성 일자를 열로 가지는 DataFrame 생성
                    'code': universe.keys(),
                    'code_name': universe.values(),
                    'created_at': [now] * len(universe.keys())
                })

                insert_df_to_db(self.strategy_name, 'universe', universe_df)            # DB에 (테이블)universe에 Dataframe 저장



        # (테이블)universe에서 레코드셋 생성 후 (리스트)universe_list 저장
        # universe_list = {'000270':{'code_name':'기아'}}
        sql = "select * from universe"
        cur = execute_sql(self.strategy_name, sql)
        universe_list = cur.fetchall()


        # self.universe[code] = {(0,'000270','기아','20240626')}
        for item in universe_list:
            idx, code, code_name, created_at = item
            self.universe[code] = {                                                                 # self.universe = {'000270':{'code_name':'기아'}}
                'code_name': code_name
            }
        print(self.universe)


    # (테이블)universe 종목코드별로 일봉데이터 확인 후 종목코드별 테이블 생성
    def check_and_get_price_data(self):
        for idx, code in enumerate(self.universe.keys()):                                           # self.universe.keys() : 종목코드
            print("({}/{}) {}".format(idx + 1, len(self.universe), code))                    # 유니버스에 등록된 코드 모두 출력 ==> (1/200) 000270

            if check_transaction_closed() and not check_table_exist(self.strategy_name, code):      # 사례 ➊: 장 종료이며, 테이블이 없다면
                price_df = self.kiwoom.get_price_data(code)                                         # 종목코드별 TR 요청(주식일봉차트조회요청)
                insert_df_to_db(self.strategy_name, code, price_df)                                 # 코드를 테이블 이름으로 해서 데이터베이스에 저장

            else:

                if check_transaction_closed():                                                      # 사례 ➋: 장이 종료되었다면
                    sql = "select max(`{}`) from `{}`".format('index', code)                 # 저장된 데이터의 가장 최근 일자 조회
                    cur = execute_sql(self.strategy_name, sql)
                    last_date = cur.fetchone()                                                      # 일봉 데이터를 저장한 가장 최근 일자 조회
                    now = datetime.now().strftime("%Y%m%d")                                         # 오늘 날짜 지정

                    if last_date[0] != now:                                                         # 최근 저장 일자가 오늘이 아니면, 오늘 일봉 데이터 생성
                        price_df = self.kiwoom.get_price_data(code)                                 # 종목코드별 TR 요청(주식일봉차트조회요청)
                        insert_df_to_db(self.strategy_name, code, price_df)                         # 종목코드별 일봉 데이터를 DB에 저장


                else:                                                                               # 사례 ➌~➍: 장 시작 전이거나 장 중인 경우 (테이블)종별코드에서 RS 반환
                    sql = "select * from `{}`".format(code)
                    cur = execute_sql(self.strategy_name, sql)
                    cols = [column[0] for column in cur.description]                                # cur.description의 행렬에서 0번째 컬럼들 추출
                    price_df = pd.DataFrame.from_records(data=cur.fetchall(), columns=cols)         # 데이터베이스에서 조회한 데이터를 DataFrame으로 변환해서 저장
                    price_df = price_df.set_index('index')
                    self.universe[code]['price_df'] = price_df                                      # 가격 데이터를 self.universe에서 접근할 수 있도록 저장                                                                                # 사례 ➋~➍: 일봉 데이터가 있는 경우


                                                                                                    # 쿼리 실행 후 cur.description 행렬
                                                                                                    #[
                                                                                                    #    ('index', None, None, None, None, None, None),
                                                                                                    #    ('open', None, None, None, None, None, None),
                                                                                                    #    ('high', None, None, None, None, None, None),
                                                                                                    #    ('low', None, None, None, None, None, None),
                                                                                                    #    ('close', None, None, None, None, None, None),
                                                                                                    #    ('volume', None, None, None, None, None, None)
                                                                                                    #]


    def run(self):
        while self.is_init_success:
            try:
                if not check_transaction_open():
                    print("장시간이 아니므로 5분간 대기합니다.")
                    time.sleep(5 * 60)
                    continue

                for idx, code in enumerate(self.universe.keys()):
                    print('[{}/{}_{}]'.format(idx + 1, len(self.universe), self.universe[code]
                    ['code_name']))
                    time.sleep(0.5)

                    if code in self.kiwoom.order.keys():
                        print('접수 주문', self.kiwoom.order[code])

                        if self.kiwoom.order[code]['미체결수량'] > 0:
                            pass

                    elif code in self.kiwoom.balance.keys():  # 보유 종목인지 확인
                        print('보유 종목', self.kiwoom.balance[code])

                        if self.check_sell_signal(code):  # 매도 대상 확인
                            self.order_sell(code)                                                   # 매도 대상이면 매도 주문 접수

                    else:
                    self.check_buy_signal_and_order(code)                                           # 접수한 종목 및 보유 종목이 아니라면 매수 대상인지 확인 후 주문 접수

            except Exception as e:
                print(traceback.format_exc())

        def check_sell_signal(self, code):
            universe_item = self.universe[code]
            print(universe_item)
            print(universe_item.keys())

    def set_universe_real_time(self):                                                               # 유니버스의 실시간 체결 정보 수신을 등록하는 함수
        fids = get_fid("체결시간")                                                                       # 임의의 fid를 하나 전달하는 코드(아무 값의 fid라도 하나 이상 전달해야 정보를 얻어 올 수 있음)
        # self.kiwoom.set_real_reg("1000", "", get_fid("장운영구분"), "0")                                   # 장 운영 구분을 확인하는 데 사용할 코드

        codes = self.universe.keys()                                                                # universe 딕셔너리의 키 값들은 종목 코드들을 의미
        codes = ";".join(map(str, codes))                                                           # 종목 코드들을 ‘;’을 기준으로 연결

        self.kiwoom.set_real_reg("9999", codes, fids, "0")                                              # 화면 번호 9999에 종목 코드들의 실시간 체결 정보 수신 요청

    def check_sell_signal(self, code):
        universe_item = self.universe[code]
        print(universe_item)
        print(universe_item.keys())

        if code not in self.kiwoom.universe_realtime_transaction_info.keys():                       # 현재 체결 정보가 존재하는지 확인
            print("매도대상 확인 과정에서 아직 체결정보가 없습니다.")                                     # 체결 정보가 없으면 더 이상 진행하지 않고 함수 종료
            return
        open = self.kiwoom.universe_realtime_transaction_info[code]['시가']
        high = self.kiwoom.universe_realtime_transaction_info[code]['고가']
        low = self.kiwoom.universe_realtime_transaction_info[code]['저가']
        close = self.kiwoom.universe_realtime_transaction_info[code]['현재가']
        volume = self.kiwoom.universe_realtime_transaction_info[code]['누적거래량']
        # -----실시간 체결 정보가 존재하면 현시점의 시가 / 고가 / 저가 / 현재가 / 누적 거래량 저장

        today_price_data = [open, high, low, close, volume]                                         # 오늘 가격 데이터를 과거 가격 데이터(DataFrame)의 행으로 추가하고자 리스트로 만듦

        df = universe_item['price_df'].copy()

        df.loc[datetime.now().strftime('%Y%m%d')] = today_price_data                                # 과거 가격 데이터에 금일 날짜로 데이터 추가

        print(df)

        period = 2                                                                                  # 기준일 N 설정
        date_index = df.index.astype('str')
        U = np.where(df['close'].diff(1) > 0, df['close'].diff(1), 0)                               # df.diff로 ‘기준일 종가 - 기준일 전일 종가’를 계산하여 0보다 작으면 감소분을 넣고, 증가했으면 0을 넣음
        D = np.where(df['close'].diff(1) < 0, df['close'].diff(1) * (-1), 0)                        # df.diff로 ‘기준일 종가 - 기준일 전일 종가’를 계산하여 0보다 크면 증가분을 넣고, 감소했으면 0을 넣음
        AU = pd.DataFrame(U, index=date_index).rolling(window=period).mean()                        # AU, period = 2일 동안 U의 평균
        AD = pd.DataFrame(D, index=date_index).rolling(window=period).mean()                        # AD, period = 2일 동안 D의 평균
        RSI = AU / (AD + AU) * 100                                                                  # RSI(N) 계산, 0부터 1로 표현되는 RSI에 100을 곱함
        df['RSI(2)'] = RSI

        purchase_price = self.kiwoom.balance[code]['매입가']                                         # 보유 종목의 매입 가격 조회
        rsi = df[-1:]['RSI(2)'].values[0]                                                           # 금일의 RSI(2) 구하기

        if rsi > 80 and close > purchase_price:
            return True
        else:
            return False

    def order_sell(self, code):                                                                     # 매도 주문 접수 함수
        quantity = self.kiwoom.balance[code]['보유수량']                                             # 보유 수량 확인(전량 매도 방식으로 보유한 수량을 모두 매도함)

        ask = self.kiwoom.universe_realtime_transaction_info[code]['(최우선)매도호가']                 # 최우선 매도 호가 확인

        order_result = self.kiwoom.send_order('send_sell_order', '1001', 2, code, quantity, ask,
                                              '00')

    def check_buy_signal_and_order(self, code):                                                     # 매수 대상인지 확인하고 주문을 접수하는 함수
        if not check_adjacent_transaction_closed_for_buying():                                      # 매수 가능 시간 확인
            return False

        universe_item = self.universe[code]

        if code not in self.kiwoom.universe_realtime_transaction_info.keys():
            print("매수대상 확인 과정에서 아직 체결정보가 없습니다.")
            return

        open = self.kiwoom.universe_realtime_transaction_info[code]['시가']
        high = self.kiwoom.universe_realtime_transaction_info[code]['고가']
        low = self.kiwoom.universe_realtime_transaction_info[code]['저가']
        close = self.kiwoom.universe_realtime_transaction_info[code]['현재가']
        volume = self.kiwoom.universe_realtime_transaction_info[code]['누적거래량']

        today_price_data = [open, high, low, close, volume]

        df = universe_item['price_df'].copy()

        df.loc[datetime.now().strftime('%Y%m%d')] = today_price_data

        period = 2  # 기준일 N 설정
        date_index = df.index.astype('str')
        U = np.where(df['close'].diff(1) > 0, df['close'].diff(1), 0)
        D = np.where(df['close'].diff(1) < 0, df['close'].diff(1) * (-1), 0)
        AU = pd.DataFrame(U, index=date_index).rolling(window=period).mean()
        AD = pd.DataFrame(D, index=date_index).rolling(window=period).mean()
        RSI = AU / (AD + AU) * 100  # RSI(N) 계산, 0부터 1로 표현되는 RSI에 100을 곱함
        df['RSI(2)'] = RSI
        # check_buy_signal_and_order 함수에서 사용한 실시간 체결 정보 조회 및 RSI(2) 계산 코드와 같은 코드

        df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['ma60'] = df['close'].rolling(window=60, min_periods=1).mean()

        rsi = df[-1:]['RSI(2)'].values[0]
        ma20 = df[-1:]['ma20'].values[0]
        ma60 = df[-1:]['ma60'].values[0]

        idx = df.index.get_loc(datetime.now().strftime('%Y%m%d')) – 2                               # 2 거래일 전 날짜(index)를 구함
        close_2days_ago = df.iloc[idx]['close']                                                     # 위 index부터 2 거래일 전 종가를 얻어 옴
        price_diff = (close - close_2days_ago) / close_2days_ago * 100                              # 2 거래일 전 종가와 현재가를 비교

        if ma20 > ma60 and rsi < 5 and diff_days_ago < -2:
            if (self.get_position_count() + self.get_buy_order_count()) >= 10:                      # 이미 보유한 종목, 매수 주문 접수한 종목의 합이 보유 가능 최대치(열 개)라면 더 이상 매수 불가능하므로 종료
                return

            budget = self.deposit / (10 - (self.get_position_count() + self.get_buy_order_count())) # 주문에 사용할 금액 계산(10은 최대 보유 종목 수로 const.py 파일에 상수로 만들어 관리하는 것도 좋음)

            bid = self.kiwoom.universe_realtime_transaction_info[code]['(최우선)매수호가']             # 최우선 매수 호가 확인

            quantity = math.floor(budget / bid)  # 주문 수량 계산(소수점은 제거하기 위해 버림)

            if quantity < 1:  # 주문 주식 수량이 1 미만이라면 매수 불가능하므로 체크
                return

            amount = quantity * bid  # 현재 예수금에서 수수료를 곱한 실제 투입 금액(주문 수량 * 주문 가격)을 제외해서 계산
            self.deposit = math.floor(self.deposit - amount * 1.00015)

            if self.deposit < 0:  # 예수금이 0보다 작아질 정도로 주문할 수는 없으므로 체크
                return

            order_result = self.kiwoom.send_order('send_buy_order', '1001', 1, code, quantity, bid,
                                                  '00')  # 계산을 바탕으로 지정가 매수 주문 접수

            self.kiwoom.order[code] = {'주문구분': '매수', '미체결수량': quantity}  # _on_chejan_slot이 늦게 동작할 수도 있기 때문에 미리 약간의 정보를 넣어 둠
        else:
            return

    def get_balance_count(self):  # 매도 주문이 접수되지 않은 보유 종목 수를 계산하는 함수
        balance_count = len(self.kiwoom.balance)
        for code in self.kiwoom.order.keys():  # kiwoom balance에 존재하는 종목이 매도 주문 접수되었다면 보유 종목에서 제외시킴
            if code in self.kiwoom.balance and self.kiwoom.order[code]['주문구분'] == "매도" and self.kiwoom.order[code]['미체결수량'] == 0:
            balance_count = balance_count - 1
        return balance_count

    def get_buy_order_count(self):  # 매수 주문 종목 수를 계산하는 함수
        buy_order_count = 0
        for code in self.kiwoom.order.keys():  # 아직 체결이 완료되지 않은 매수 주문
            if code not in self.kiwoom.balance and self.kiwoom.order[code]['주문구분'] == "매수":
                buy_order_count = buy_order_count + 1
        return buy_order_count
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
            self.is_init_success = True

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


    # universe테이블의 종목코드별로 최신 일봉데이터가 있는지 확인하고 없다면 생성하는 함수
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
                            pass  # 매도 대상이면 매도 주문 접수

            except Exception as e:
                print(traceback.format_exc())

        def check_sell_signal(self, code):
            universe_item = self.universe[code]
            print(universe_item)
            print(universe_item.keys())

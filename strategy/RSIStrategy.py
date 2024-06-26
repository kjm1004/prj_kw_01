from api.Kiwoom import *
from util.make_up_universe import *
from util.db_helper import *
import math


class RSIStrategy(QThread):
    def __init__(self):
        QThread.__init__(self)
        self.strategy_name = "RSIStrategy"
        self.kiwoom = Kiwoom()
        self.init_strategy()

    def init_strategy(self):                                                                        # 전략 초기화 기능을 수행하는 함수
        self.check_and_get_universe()

    def check_and_get_universe(self):                                                               # 유니버스가 있는지 확인하고 없으면 생성하는 함수
        if not check_table_exist(self.strategy_name, 'universe'):
            universe_list = get_universe()
            print(universe_list)

            universe = {}
            now = datetime.now().strftime("%Y%m%d")                                                 # 오늘 날짜를 20210101 형태로 지정
            kospi_code_list = self.kiwoom.get_code_list_by_market("0")                              # KOSPI(0)에 상장된 모든 종목 코드를 가져와 kospi_code_list에 저장
            kosdaq_code_list = self.kiwoom.get_code_list_by_market("10")                            # KOSDAQ(10)에 상장된 모든 종목 코드를 가져와 kosdaq_code_list에 저장

            for code in kospi_code_list + kosdaq_code_list:                                         # 모든 종목 코드를 바탕으로 반복문 수행
                code_name = self.kiwoom.get_master_code_name(code)                                  # 종목 코드에서 종목명을 얻어 옴

                if code_name in universe_list:                                                      # 얻어 온 종목명이 유니버스에 포함되어 있다면 딕셔너리에 추가
                    universe[code] = code_name

                universe_df = pd.DataFrame({                                                        # 코드, 종목명, 생성 일자를 열로 가지는 DataFrame 생성
                    'code': universe.keys(),
                    'code_name': universe.values(),
                    'created_at': [now] * len(universe.keys())
                })

                insert_df_to_db(self.strategy_name, 'universe', universe_df)                        # universe라는 테이블 이름으로 Dataframe을 DB에 저장

    def run(self):                                                                                  # 실질적 수행 역할을 하는 함수
        pass
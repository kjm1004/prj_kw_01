import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
from datetime import datetime

BASE_URL = 'https://finance.naver.com/sise/sise_market_sum.nhn?sosok='
CODES = [0, 1]
START_PAGE = 1
fields = []

now = datetime.now()
formattedDate = now.strftime("%Y%m%d")

def execute_crawler():
    df_total = []                                                                                   # KOSPI, KOSDAQ 종목을 하나로 합치는 데 사용할 변수

    for code in CODES:                                                                              # CODES에 담긴 KOSPI, KOSDAQ 종목 모두를 크롤링하려고 for 문 사용

        # 전체 페이지 수 확인
        res = requests.get(BASE_URL + str(code))                                                    # 전체 페이지 수를 가져오는 코드
        page_soup = BeautifulSoup(res.text, 'lxml')                                        # Python 라이브러리로, 웹 스크래핑(Web Scraping) 용도(HTML과 XML 파일에서 데이터를 추출)
                                                                                                    # 소스 코드에서 필요한 데이터를 구조적으로 쉽게 추출
                                                                                                    # 웹페이지 내용을 트리구조로 변환
        # 각 페이지별 페이지 번호 추출: td > a > href
        total_page_num = page_soup.select_one('td.pgRR > a')                                        # >: 자식 요소를 선택하는 데 사용되는 연산자
        total_page_num = int(total_page_num.get('href').split('=')[-1])                             #  /page?page=10 => ['/page?page', '10'] => total_page_num=10

        # 각 페이지별 문서 요소 확인: div > input >
        ipt_html = page_soup.select_one('div.subcnt_sise_item_top')                                 # div.subcnt_sise_item_top  <== div 클래스가 subcnt_sise_item_top
        global fields                                                                               # 전역 변수 fields 선언

        # 각 페이지별로 클롤링(crawler(code, page) 함수 사용)해서 > df(데이터프레임)에 누적
        fields = [item.get('value') for item in ipt_html.select('input')]
        result = [crawler(code, str(page)) for page in range(1, total_page_num + 1)]                # 페이지마다 존재하는 모든 종목의 항목 정보를 크롤링해서 result에 저장(여기서 crawler 함수가 한 페이지씩 크롤링해 오는 역할 담당)
        df = pd.concat(result, axis=0, ignore_index=True)                                           # axis=0 : 행방향 누적. ignore_index=True: 인덱스 재설정 (크롤링한 데이터를 하나의 데이터프레임으로 통합하기 위해)
        df_total.append(df)                                                                         # df 변수는 KOSPI, KOSDAQ별로 크롤링한 종목 정보고, 이를 하나로 합치고자 df_total에 추가

    df_total = pd.concat(df_total)                                                                  # df_total을 하나의 데이터프레임으로 만듦
    df_total.reset_index(inplace=True, drop=True)                                                   # 합친 데이터 프레임의 index 번호를 새로 매김
    filename = f'NaverFinance_{formattedDate}.xlsx'                                                 # f-string 포맷팅
    df_total.to_excel(filename)                                                                     # 전체 크롤링 결과를 엑셀로 출력

    return df_total  # 크롤링 결과를 반환


def crawler(code, page):
    global fields

    # 네이버 파인넨스에 각 페이지 요청 : 요청 시 매개변수 menu, fieldIds, returnUrl
    data = {'menu': 'market_sum',
            'fieldIds': fields,
            'returnUrl': BASE_URL + str(code) + "&page=" + str(page)}
    res = requests.post('https://finance.naver.com/sise/field_submit.nhn', data=data)           # 네이버로 요청을 전달(post 방식)

    #요청 후 반환 페이지 분석
    page_soup = BeautifulSoup(res.text, 'lxml')
    table_html = page_soup.select_one('div.box_type_l')                                             # div 추출
    header_data = [item.get_text().strip() for item in table_html.select('thead th')][1: -1]        # 전체 head 행 추출 : thead > th > 텍스트 추출(get_text), [1: -1] > 처음과 마지막 요소 제외


    inner_data = [item.get_text().strip()                                                           # 대상 데이터를 리스트로 생성 > lambda : 조건에 맞는 태그만 추출
                  for item in table_html.find_all(                                                  # 조건 : title 클래스인 <a>, number 클래스인 <td>
                        lambda x: (x.name == 'a' and 'tltle' in x.get('class', []))
                        or
                        (x.name == 'td' and 'number' in x.get('class', []))
                  )
                 ]

    no_data = [item.get_text().strip() for item in table_html.select('td.no')]                      # 페이지마다 있는 종목의 순번 가져와서 리스트 생성
    number_data = np.array(inner_data)                                                              #
                                                                                                    # np 배열로 변환
                                                                                                    # ***** 코드 예시 *****
                                                                                                    # <table>
                                                                                                    #   <tr>
                                                                                                    #     <td class="no">1</td>
                                                                                                    #     <td class="number">1234</td>
                                                                                                    #     <td class="number">5678</td>
                                                                                                    #     <td><a class="tltle" href="#">종목1</a></td>
                                                                                                    #   </tr>
                                                                                                    #   <tr>
                                                                                                    #     <td class="no">2</td>
                                                                                                    #     <td class="number">9101</td>
                                                                                                    #     <td class="number">1121</td>
                                                                                                    #     <td><a class="tltle" href="#">종목2</a></td>
                                                                                                    #   </tr>
                                                                                                    # </table>
                                                                                                    # 결과
                                                                                                    # inner_data:  ['1234', '5678', '종목1', '9101', '1121', '종목2']
                                                                                                    # no_data: ['1', '2']
                                                                                                    # number_data: np.array(inner_data)

    number_data.resize(len(no_data), len(header_data))                                              # 가로×세로 크기에 맞게 행렬화

    df = pd.DataFrame(data=number_data, columns=header_data)                                        # 한 페이지에서 얻은 정보를 모아 데이터프레임으로 만들어 반환
    return df

# 1. 네이버 증권에서 크롤링
# 2. 조건 필터링 후 200개 추출해서 엑셀파일로 저장
# 3. dataFrame(종목명) 반환
def get_universe():
    df = execute_crawler()                                                                          # 크롤링 결과를 얻어 옴
    mapping = {',': '', 'N/A': '0'}
    df.replace(mapping, regex=True, inplace=True)                                                   # mapping 형식으로 replace
    cols = ['거래량', '매출액', '매출액증가율', 'ROE', 'PER']                                           # 사용할 column들 설정
    df[cols] = df[cols].astype(float)                                                               # 크롤링해 온 데이터는 str > float으로 변환

    # 유니버스 필터링
    df = df[      (df['거래량'] > 0) & (df['매출액'] > 0)                                             # 거래 중지 종목 및 우선주, ETF를 제외
                & (df['매출액증가율'] > 0) & (df['ROE'] > 0)                                          # 그대로 매출액 증가율과 ROE가 0보다 큰 종목
                & (df['PER'] > 0)                                                                   # PER이 낮을수록 좋지만, 마이너스 값은 제외 (per가 낮으면 저위험 투자)
                & (~df.종목명.str.contains("지주")) & (~df.종목명.str.contains("홀딩스"))               # 종목명에 ‘지주’이거나 ‘홀딩스’인 데이터를 제외. ~ : not
           ]
    df['1/PER'] = 1 / df['PER']                                                                     # PER에 대해 내림차순 정렬을 위해서
    df['RANK_ROE'] = df['ROE'].rank(method='max', ascending=False)                                  # ROE의 순위 계산
    df['RANK_1/PER'] = df['1/PER'].rank(method='max', ascending=False)                              # 1/PER의 순위 계산
    df['RANK_VALUE'] = (df['RANK_ROE'] + df['RANK_1/PER']) / 2                                      # ROE 순위, 1/PER 순위를 합산한 랭킹
    df = df.sort_values(by=['RANK_VALUE'])                                                          # RANK_VALUE를 기준으로 정렬
    df.reset_index(inplace=True, drop=True)                                                         # 필터링한 데이터프레임의 index 번호를 새로 매김

    # 상위 200개만 추출
    df = df.loc[:199]

    filename = f'universe{formattedDate}.xlsx'
    df.to_excel(filename)                                                                           # 유니버스 생성 결과를 엑셀로 출력
    return df ['종목명'].tolist()                                                                    # dataFrame 내용 중 '종목명' 컬럼을 추출해서 반환


if __name__ == "__main__":
    print('Start!')
    get_universe()
    print('End')
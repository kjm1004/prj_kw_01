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
    df_total.to_excel('NaverFinance.xlsx')                                                          # 전체 크롤링 결과를 엑셀로 출력

    return df_total  # 크롤링 결과를 반환


def crawler(code, page):
    global fields

    data = {'menu': 'market_sum',
            'fieldIds': fields,
            'returnUrl': BASE_URL + str(code) + "&page=" + str(page)}                               # Naver Finance에 전달할 값들 세팅(요청을 보낼 때는 menu, fieldIds, returnUrl을 지정해서 보내야 함)

    res = requests.post('https://finance.naver.com/sise/field_submit.nhn', data=data)           # 네이버로 요청을 전달(post 방식)
    page_soup = BeautifulSoup(res.text, 'lxml')

    table_html = page_soup.select_one('div.box_type_l')                                             # 크롤링할 table의 html을 가져오는 코드(크롤링 대상 요소의 클래스는 웹 브라우저에서 확인)
    header_data = [item.get_text().strip() for item in table_html.select('thead th')][1: -1]        # column 이름을 가공

    inner_data = [item.get_text().strip()                                                           # 종목명 + 수치 추출(a.title = 종목명, td.number = 기타 수치)
                  for item in table_html.find_all(lambda x: (x.name == 'a' and 'tltle' in x.get('class', [])) or (x.name == 'td' and 'number' in x.get('class', [])))]

    no_data = [item.get_text().strip() for item in table_html.select('td.no')]  # 페이지마다 있는 종목의 순번 가져오기
    number_data = np.array(inner_data)

    number_data.resize(len(no_data), len(header_data))  # 가로×세로 크기에 맞게 행렬화

    df = pd.DataFrame(data=number_data, columns=header_data)  # 한 페이지에서 얻은 정보를 모아 데이터프레임으로 만들어 반환
    return df


if __name__ == "__main__":
    print('Start!')
    execute_crawler()
    print('End')

from PyQt5.QtWidgets import QApplication
from api.Kiwoom import *
import sys

from api.Kiwoom import *

# app = QApplication(sys.argv)          <== 이벤트 루프 : OS의 이벤트, PyQt의 이벤트를 받아들임
#   window = MyWindow()
#   window.show()
# app.exec_()     # main event loop     <== 루프 실행

app = QApplication(sys.argv)

kiwoom = Kiwoom()
# df = kiwoom.get_price_data("005930")
# print(df)

#deposit = kiwoom.get_deposit()

# 주식 주문
# order_result = kiwoom.send_order('send_buy_order', '1001', 1, '007700', 100, 15090, '00')
# print("주문결과 : %s" % order_result)

# 주식 체결 결과 보기
# orders = kiwoom.get_order()
# print(orders)

# 주식 체결 잔고 현황 보기
position = kiwoom.get_balance()
print(position)

# 주식 실시간 체결현황 보기
# 예시: kiwoom.set_real_reg("1000", "", get_fid("장운영구분"), "0")
fids = get_fid("체결시간")
codes = '005930;007700;000660;'
kiwoom.set_real_reg("1000", codes, fids, "0")

app.exec_()



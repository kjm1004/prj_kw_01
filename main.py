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

order_result = kiwoom.send_order('send_buy_order', '1001', 1, '007700', 1, 15300, '00')
print("주문결과 : %s" % order_result)


app.exec_()



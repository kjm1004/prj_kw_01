from PyQt5.QtWidgets import QApplication
from api.Kiwoom import *
import sys

from api.Kiwoom import Kiwoom

# app = QApplication(sys.argv)          <== 이벤트 루프 : OS의 이벤트, PyQt의 이벤트를 받아들임
#   window = MyWindow()
#   window.show()
# app.exec_()     # main event loop     <== 루프 실행

app = QApplication(sys.argv)

kiwoom = Kiwoom()
df = kiwoom.get_price_data("005930")
print(df)

app.exec_()



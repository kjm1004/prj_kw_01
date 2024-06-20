import sys

from PyQt5.QtWidgets import QApplication

from api.test_Loop import Example

app = QApplication(sys.argv)

example = Example()
example.process()
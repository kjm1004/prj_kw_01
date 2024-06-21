from PyQt5.QtCore import QEventLoop, QObject, QTimer

class Example(QObject):
    def __init__(self):
        super().__init__()
        self.event_loop = QEventLoop()

    def process(self):
        print("Starting process")
        QTimer.singleShot(2000, self.handle_event)  # 2초 후 handle_event 호출
        self.event_loop.exec_()  # 이벤트 루프 시작
        print("Process resumed")  # 이벤트 루프 종료 후 여기로 복귀

    def handle_event(self):
        print("Event handled")
        self.event_loop.exit()  # 이벤트 루프 종료


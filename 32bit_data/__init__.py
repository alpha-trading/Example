import sys # 시스템 제어, 위치

from kiwoom.kiwoom import *
from PyQt5.QtWidgets import *

class Main():
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.kiwoom = Kiwoom() # 키움 클래스 객체화 - 객체화 하자마자 실행되는 구조 '()'기호 때문에
        self.app.exec_() # 이벤트 루프실행 - 끄기 전까지 안꺼짐

if __name__ == "__main__":
    Main()
import sys # 시스템 제어, 위치
sys.path.append("C:/Users/82106/Desktop/손하나 클론-이해") # bat 파일로 실행하기위해 init파일 실행했을떄 모든거 다 대입

from kiwoom.clone import *
from kiwoom.kiwoom import *
from PyQt5.QtWidgets import *

class Main():
    def __init__(self):
        """
        QApplication은 앱처럼 실행하고, 파라미터로 파일위치를 받는다.
        sys.argv 는 맨처음 실행 시킨 파일위치를 반환한다.       
        """
        self.app = QApplication(sys.argv)
        # self.kiwoom = Kiwoom() # 키움 클래스 객체화 - 객체화 하자마자 실행되는 구조 '()'기호 때문에
        self._test = test() # 클래스 분리 전 실행파일(clone 파일)
        self.app.exec_() # 이벤트 루프실행 - 끄기 전까지 안꺼짐

if __name__ == "__main__":
    Main()
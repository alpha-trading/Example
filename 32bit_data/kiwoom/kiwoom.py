from PyQt5.QAxContainer import * # QAxWidget 사용하기 위해
from PyQt5.QtCore import * # QEventLopp 사용하기 위해서
from PyQt5.QtTest import * # QTest 사용하기위해서
from config.errorCode import *
from config.kiwoomType import *
import os
import sys

"""
일단 csv파일 기준으로 만들고 확장자나 가져오는 목록은 추후에 변경(else파트에서 저장하는 부분도 변경)

데이터만 가져와도 해야할목록
로그인 + 데이터멀티조회(시그널,이벤트,슬롯) + 스크린번호 + 파일저장
"""

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        print("Start Program")

        "event loop 쓸때 사용할 변수들 모음"
        self.login_event_loop = QEventLoop()
        self.detail_account_info_event_loop = QEventLoop()  # 예수금 요청용 이벤트 루프
        self.get_information_stock_event_loop = QEventLoop() # 차트정보 요청할때 사용

        "데이터 입출력 관련된 변수들"
        self.account_stock_dict = {} # 보유종목 불러올때 사용
        self.account_num = None # 계좌번호
        self.calcul_data = [] # 종목데이터 배열(저장용)
        self.total_cnt = 0 # 테스트용 자료수

        "요청 스크린 번호 모음"
        self.screen_my_info = "2000"  # 계좌 관련 스크린 번호
        self.screen_information_stock = "4000"  # 계산용 스크린 번호
        self.screen_real_stock = "5000"  # 종목별 실시간 정보를 가져올때 사용
        self.screen_meme_stock = "6000"  # 종목별 주문할때 사용
        self.screen_start_stop_real = "1000"  # 장 시작/ 종료 실시간 스크린 번호

        "시작할때 바로 실행하는 함수들"
        self.get_ocx_instance() # 레지스트리 실행
        self.event_slots()  # 일반 이벤트함수로(시그널-슬롯 연결)
        self.signal_login_commConnect() # 로그인 요청함시그널

        self.get_information_stock_30min() # 30분봉 차트 저장하기
        # self.get_information_stock() # 일봉저장하기


    def get_ocx_instance(self): # 키움 API 레지스트리 실행
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def event_slots(self): # 키움과 연걸하기 위한 시그널 / 슬롯 모음
        self.OnEventConnect.connect(self.login_slot) # 로그인 이벤트함수
        self.OnReceiveTrData.connect(self.trdata_slot)  # TR 요청 관련

    def signal_login_commConnect(self):
        self.dynamicCall("CommConnect()") # 로그인

        self.login_event_loop.exec_() # 로그인 이벤트루프 실행

    def login_slot(self, err_code):  # 로그인을 받는 슬롯 만들기
        print(errors(err_code)[1])

        self.login_event_loop.exit()  # 로그인 이벤트 루프 종료

    def stop_screen_cancel(self, sScrNo=None):  # 요청 안끊으면 뒤에입력 못받음 나중에 추가설명 하기
        self.dynamicCall("DisconnectRealData(QString)", sScrNo)

    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):  # TR 데이터 받을 슬롯
        if sRQName == "주식일봉차트조회":
            code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "종목코드")
            code = code.strip()
            # data = self.dynamicCall("GetCommDataEx(QString, QString)", sTrCode, sRQName)
            # [[‘’, ‘현재가’, ‘거래량’, ‘거래대금’, ‘날짜’, ‘시가’, ‘고가’, ‘저가’. ‘’], [‘’, ‘현재가’, ’거래량’, ‘거래대금’, ‘날짜’, ‘시가’, ‘고가’, ‘저가’, ‘’]. […]]
            """
            GetCommDataEx 함수 - 600일치 데이터 가져오기
            아니면 GetCommData 함수 사용해서 이상의 데이터를 가져오기
            """

            cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)  # 멀티데이터조회할때 개수받아오는 함수
            print("일봉")

            # 0 대입하면 오늘자 하루 데이터만 가져오는것
            for i in range(cnt):  # 여기서는 종목의 개수가아니라 한종목의 "일수"
                data = []  # GetCommDataEx 로 데이터 가져올때 나오는 이중 리스트 형태와 똑같이 만들기위해

                name = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                 "종목코드")  # 출력 : 종목이름
                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                 "현재가")  # 출력 : 000070
                value = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                         "거래량")  # 출력 : 000070
                trading_value = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                 "거래대금")  # 출력 : 000070
                date = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                        "일자")  # 출력 : 000070
                start_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                               "시가")  # 출력 : 000070
                high_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                              "고가")  # 출력 : 000070
                low_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                             "저가")  # 출력 : 000070

                data.append(current_price.strip())
                data.append(value.strip())
                data.append(trading_value.strip())
                data.append(date.strip())
                data.append(start_price.strip())
                data.append(high_price.strip())
                data.append(low_price.strip())
                data.append(name.strip())

                # 데이터 최근것부터 저장됨 - 나중에 뒤집기
                self.calcul_data.append(data.copy())  # 리스트는 주소값을 이기때문에 복사본으로 값만 넘겨야함

            if sPrevNext == "2":  # 과거 데이터가 존재하면 2로 바뀐다.
                self.day_kiwoom_db(code=code, sPrevNext=sPrevNext)  # 재귀적인 성질때문에 뒤에 데이터가 더존재하면 600개씩 가져옴
            else:  # 없으면 더이상 존재하지않으니 저장후, 저장용배열지우고, 이벤트 종료
                self.calcul_data.reverse() # 예전데이터가 앞으로오게 뒤집기

                print("저장시작")
                f = open("C:/Users/82106/Desktop/trading_example/32bit_data/data/KOSPI/" + code + ".csv", "w", encoding="utf8")
                for i in range(len(self.calcul_data)):
                    f.write(self.calcul_data[i][0])
                    f.write(",")
                    f.write(self.calcul_data[i][1])
                    f.write(",")
                    f.write(self.calcul_data[i][2])
                    f.write(",")
                    f.write(self.calcul_data[i][3])
                    f.write("\n")
                f.close()

                self.calcul_data.clear()
                self.get_information_stock_event_loop.exit()

        if sRQName == "주식분봉차트조회":
            code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "종목코드")
            code = code.strip()

            cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)  # 멀티데이터조회할때 개수받아오는 함수
            print("분봉")

            for i in range(cnt):  # 여기서는 종목의 개수가아니라 한종목의 "일수"
                data = []  # GetCommDataEx 로 데이터 가져올때 나오는 이중 리스트 형태와 똑같이 만들기위해

                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                 "현재가")  # 출력 : 000070
                volume = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                         "거래량")  # 출력 : 000070
                start_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                               "시가")  # 출력 : 000070
                high_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                              "고가")  # 출력 : 000070
                low_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                             "저가")  # 출력 : 000070

                data.append(int(start_price))
                data.append(int(high_price))
                data.append(int(low_price))
                data.append(int(current_price))
                data.append(int(volume))

                # 데이터 최근것부터 저장됨 - 나중에 뒤집기
                self.calcul_data.append(data.copy())  # 리스트는 주소값을 이기때문에 복사본으로 값만 넘겨야함

            if sPrevNext == "2":  # 과거 데이터가 존재하면 2로 바뀐다.
                self.chart_data_30min(code=code, sPrevNext=sPrevNext)  # 재귀적인 성질때문에 뒤에 데이터가 더존재하면 600개씩 가져옴
            else:  # 없으면 더이상 존재하지않으니 저장후, 저장용배열지우고, 이벤트 종료
                self.calcul_data.reverse()  # 예전데이터가 앞으로오게 뒤집기

                print("저장시작")
                f = open("C:/Users/82106/Desktop/trading_example/32bit_data/data/KOSPI/" + code + ".csv", "w",
                         encoding="utf8")
                for i in range(len(self.calcul_data)):
                    f.write(str(self.calcul_data[i][0]))
                    f.write(",")
                    f.write(str(self.calcul_data[i][1]))
                    f.write(",")
                    f.write(str(self.calcul_data[i][2]))
                    f.write(",")
                    f.write(str(self.calcul_data[i][3]))
                    f.write(",")
                    f.write(str(self.calcul_data[i][4]))
                    f.write("\n")
                f.close()

                self.calcul_data.clear()
                self.get_information_stock_event_loop.exit()


    def get_code_list_by_market(self, market_code): # 이미 저장해서 사용안하기
        '''
        종목코드 리스트 받기
        #0:KOSPI, 10:코스닥
        :param market_code: 시장코드 입력
        GetCodeListByMarket(QString) - market_code 매개변수로 넘기면
        :return: 종목 코드들이 ;기준으로 넘어옴 ex) 156184;854612;
        '''
        """
        코드 리스트를 따로 저장해두고, 순서대로넣고 멈추면 그자리에서(?)
        """
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_code)
        code_list = code_list.split(';')[:-1] # 맨마지막에 '' 처럼 빈칸이 오기때문에 마지막은 제외하고 자른다.
        return code_list

    def get_information_stock(self):
        '''
        get_code_list_by_market 함수를 이용해서 가져온 데이터를 통해서 분석하는 함수

        가져온 데이터가 종목 코드이니 이 코드를 이용해서 TR보내면, 그 종목에대한 정보를 가져오는 형식
        '''
        " 내가저장해둔 리스트에서 사용"
        f = open("C:/Users/82106/Desktop/trading_example/32bit_data/stock_list/" + "KOSPI" + ".csv", "r", encoding="utf8")
        kospi_list = f.readlines()

        " 코스피 부터 데이터 불러오기"
        for idx in range(0, len(kospi_list)):
            code = kospi_list[idx]
            code = code.strip()

            self.dynamicCall("DisconnectRealData(QString)", self.screen_information_stock)  # 스크린 연결 끊기
            # 연결을 끊음으로써 키움서버에 요청한 내용을 지운다.
            # 스크린을 끊는 이유는 한정된 공간에 너무많은 데이터를 넣으면 데이터 오버플로우발생하니 끊기

            " 각종목의 데이터를 요구하는 함수 실행"
            self.day_kiwoom_db(code=code) # 일봉

    def get_information_stock_30min(self):
        '''
        get_code_list_by_market 함수를 이용해서 가져온 데이터를 통해서 분석하는 함수

        가져온 데이터가 종목 코드이니 이 코드를 이용해서 TR보내면, 그 종목에대한 정보를 가져오는 형식
        '''
        " 내가저장해둔 리스트에서 사용"
        f = open("C:/Users/82106/Desktop/trading_example/32bit_data/stock_list/" + "KOSPI" + ".csv", "r", encoding="utf8")
        kospi_list = f.readlines()

        " 코스피 부터 데이터 불러오기"
        for idx in range(26, len(kospi_list)):
            code = kospi_list[idx]
            code = code.strip()

            self.dynamicCall("DisconnectRealData(QString)", self.screen_information_stock)  # 스크린 연결 끊기
            # 연결을 끊음으로써 키움서버에 요청한 내용을 지운다.
            # 스크린을 끊는 이유는 한정된 공간에 너무많은 데이터를 넣으면 데이터 오버플로우발생하니 끊기

            " 각종목의 데이터를 요구하는 함수 실행"
            self.chart_data_30min(code=code) #30분봉


    def day_kiwoom_db(self, code=None, date=None, sPrevNext="0"):  # 특정종목의 일봉 데이터 TR요청하기
        QTest.qWait(3600)  # 3.6초마다 딜레이를 준다.
        """
        여기서 sleep() 이나 timer() 함수를 사용하지 않은 이유는 이벤트 처리떄문이다.
        두개는 멈추는동안 이벤트역시 멈추기때문에 중간에 이벤트가 끊겨서 에러가 발생한다.

        QTest.qWait 은 서버에 요청한 이벤트와 이벤트 루프의 동작은 유지하면서, 타이머를 건다.
        """

        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        # 수정주가구분은 회사가 액면가분할처럼 시가총액은 같은데 주식수를 늘린것을 반영하면 1, 이전값은 0
        if date != None:  # 특정 날짜부터 사용할예정이면 이함수 사용
            self.dynamicCall("SetInputValue(QString, QString)", "기준일자", date)  # data 양식은 YYYYMMDD

        self.dynamicCall("CommRqData(QString, QString, int, QString)", "주식일봉차트조회", "opt10081", sPrevNext,
                         self.screen_information_stock)  # Tr서버로 전송 -Transaction

        self.get_information_stock_event_loop.exec_()

    def chart_data_30min(self, code=None, date=None, sPrevNext="0"): # 30분봉 데이터 가져오기
        QTest.qWait(3600)

        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "기준일자", "30")
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "0")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "주식분봉차트조회", "opt10080", sPrevNext,
                         self.screen_information_stock)  # Tr서버로 전송 -Transaction

        self.get_information_stock_event_loop.exec_()
"""
용도만 적어두고, 사용법은 clone에서 확인하기
5장부터 만들어야함(데이터가져오기)
"""

from PyQt5.QAxContainer import * # QAxWidget 사용하기 위해
from PyQt5.QtCore import * # QEventLopp 사용하기 위해서
from PyQt5.QtTest import * # QTest 사용하기위해서
from config.errorCode import *

import sys


class alpha(QAxWidget):
    def __init__(self):
        super().__init__()
        print("Start Program")

        "event loop 쓸때 사용할 변수들 모음"
        self.login_event_loop = QEventLoop()
        self.detail_account_info_event_loop = QEventLoop()  # 예수금 요청용 이벤트 루프

        "계좌 관련된 변수들"
        self.account_stock_dict = {} # 보유종목 불러올때 사용
        self.not_concluded_account = {} # 미체결 종목들
        self.account_num = None # 계좌번호
        self.deposit = 0 # 예수금
        self.order_money =0 # 주문할 금액
        self.able_money = 0 #주문가능 현금
        self.total_profit_loss_money = 0 # 총평가손익금액
        self.total_profit_loss_rate = 0.0 # 총수익률(%)

        "요청 스크린 번호 모음"
        self.screen_my_info = "2000"  # 계좌 관련 스크린 번호
        self.screen_calculation_stock = "4000"  # 계산용 스크린 번호
        self.screen_real_stock = "5000"  # 종목별 실시간 정보를 가져올때 사용
        self.screen_meme_stock = "6000"  # 종목별 주문할때 사용
        self.screen_start_stop_real = "1000"  # 장 시작/ 종료 실시간 스크린 번호

        "시작할때 바로 실행하는 함수들"
        self.get_ocx_instance() # 레지스트리 실행
        self.event_slots()  # 일반 이벤트함수로(시그널-슬롯 연결)
        self.signal_login_commConnect() # 로그인 요청함시그널
        self.get_account_num() # 계좌번호 가져오기
        self.get_account_deposit() # 예수금 요청시그널
        self.get_account_stock() # 보유종목 가져오기
        QTimer.singleShot(5000, self.not_concluded_account)  # 5초뒤에 not 함수 실행하라는 뜻

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

    def get_account_num(self): # 계좌번호 반환
        account_list = self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
        # QString은 pyqt5에서 제공하는 공용 문자열
        account_num = account_list.split(';')[0]

        self.account_num = account_num
        print("계좌번호 : %s" % account_num )

    def get_account_deposit(self, sPrevNext="0"):  # 예수금 요청 시그널
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "체결잔고요청",
                         "opw00005", sPrevNext, self.screen_my_info)
        self.detail_account_info_event_loop.exec_()

    def get_account_stock(self, sPrevNext="0"):
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "")
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", "1")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "계좌평가잔고내역요청", "opw00018", sPrevNext,
                         self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def not_concluded_account(self, sPrevNext="0"): # 미체결 사용하는 이유가 - 중간에 꺼질경우 사용하기위해서
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "체결구분", "1")
        self.dynamicCall("SetInputValue(QString, QString)", "매매구분", "0")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "실시간미체결요청", "opt10075", sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def stop_screen_cancel(self, sScrNo=None):  # 요청 안끊으면 뒤에입력 못받음 나중에 추가설명 하기
        self.dynamicCall("DisconnectRealData(QString)", sScrNo)

    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):  # TR 데이터 받을 슬롯
        if sRQName == "체결잔고요청":
            deposit = self.dynamicCall("GetCommData(QString, QString, int, QString)"
                                       , sTrCode, sRQName, 0, "예수금")
            self.deposit = int(deposit)  # 앞에 0000... 뺴기
            print("예수금 : %s" % self.deposit)

            able = self.dynamicCall("GetCommData(QString, QString, int, QString)"
                                              , sTrCode, sRQName, 0, "주문가능현금")
            self.able_money = int(able)
            print("주문가능금액 : %s" % self.able_money)

            self.stop_screen_cancel(self.screen_my_info)

            self.detail_account_info_event_loop.exit()

        if sRQName == "계좌평가잔고내역요청":
            total_buy_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "추정예탁자산")
            self.total_buy_money = int(total_buy_money)

            total_profit_loss_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                                   "총평가손익금액")
            self.total_profit_loss_money = int(total_profit_loss_money)

            print("추정계좌평가금액: %s  총손익: %s " % (int(total_buy_money), int(total_profit_loss_money)))


            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)

            for i in range(rows):
                code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목번호")
                code = code.strip()[1:] #앞에있는 영어 빼기

                code_nm = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                           "종목명")  # 출럭 : 한국기업평가
                stock_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                  "보유수량")  # 보유수량 : 000000000000010
                buy_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                             "매입가")  # 매입가 : 000000000054100
                learn_rate = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                              "수익률(%)")  # 수익률 : -000000001.94
                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                 "현재가")  # 현재가 : 000000003450
                total_chegual_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName,
                                                       i, "매입금액")
                possible_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                     "매매가능수량")

                # 여기서 code는 종목번호로 key - int, value - list이다. 그래서 각원소에 각각 하나씩
                if code in self.account_stock_dict:  # dictionary 에 해당 종목이 있나 확인
                    pass
                else:
                    self.account_stock_dict[code] = {} # 없으면 추가

                code_nm = code_nm.strip()
                stock_quantity = int(stock_quantity.strip())
                buy_price = int(buy_price.strip())
                learn_rate = float(learn_rate.strip()) / 100
                current_price = int(current_price.strip())
                total_chegual_price = int(total_chegual_price.strip())
                possible_quantity = int(possible_quantity.strip())

                # int인 code 한개당 - 밑에 7가지 항목 같고있음 (2차원배열)
                self.account_stock_dict[code].update({"종목명": code_nm})
                self.account_stock_dict[code].update({"보유수량": stock_quantity})
                self.account_stock_dict[code].update({"매입가": buy_price})
                self.account_stock_dict[code].update({"세전수익률(%)": learn_rate})
                self.account_stock_dict[code].update({"현재가": current_price})
                self.account_stock_dict[code].update({"매입금액": total_chegual_price})
                self.account_stock_dict[code].update({'매매가능수량': possible_quantity})

                print("종목코드: %s - 종목명: %s - 보유수량: %s - 매입가: %s - 수익률: %s - 현재가: %s" % (
                    code, code_nm, stock_quantity, buy_price, learn_rate, current_price))

            print("계좌에 가지고 있는 종목은 %s " % rows)

            if sPrevNext == "2": # 다음이 존재하면 sPrevNext를 2로 설정해서 한번더 요청
                self.get_account_stock(sPrevNext="2")
            else: # 없으면 끄기
                self.detail_account_info_event_loop.exit()

        elif sRQName == "실시간미체결요청": # 계좌평가잔고내역(멀티데이터)와 가져오는 방법이 같음
            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName) # 개수

            for i in range(rows):
                code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목코드")
                code_nm = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명")
                order_no = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문번호")
                order_status = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                "주문상태")  # 접수,확인,체결
                order_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                  "주문수량")
                order_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                               "주문가격")
                order_gubun = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                               "주문구분")  # -매도, +매수, -매도정정, +매수정정
                not_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                                "미체결수량")
                ok_quantity = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i,
                                               "체결량")


                code = code.strip()
                code_nm = code_nm.strip()
                order_no = int(order_no.strip())
                order_status = order_status.strip()
                order_quantity = int(order_quantity.strip())
                order_price = int(order_price.strip())
                order_gubun = order_gubun.strip().lstrip('+').lstrip('-')
                not_quantity = int(not_quantity.strip())
                ok_quantity = int(ok_quantity.strip())

                # 같은 종목내에서 여러번의 주문이 있을수있으니 고유값인 주문번호로 key 값설정
                if order_no in self.not_account_stock_dict:
                    pass
                else:
                    self.not_account_stock_dict[order_no] = {}

                self.not_account_stock_dict[order_no].update({'종목코드': code})
                self.not_account_stock_dict[order_no].update({'종목명': code_nm})
                self.not_account_stock_dict[order_no].update({'주문번호': order_no})
                self.not_account_stock_dict[order_no].update({'주문상태': order_status})
                self.not_account_stock_dict[order_no].update({'주문수량': order_quantity})
                self.not_account_stock_dict[order_no].update({'주문가격': order_price})
                self.not_account_stock_dict[order_no].update({'주문구분': order_gubun})
                self.not_account_stock_dict[order_no].update({'미체결수량': not_quantity})
                self.not_account_stock_dict[order_no].update({'체결량': ok_quantity})

                print("미체결 종목 : %s "  % self.not_account_stock_dict[order_no])

            self.detail_account_info_event_loop.exit()

from PyQt5.QAxContainer import * # QAxWidget 사용하기 위해
from PyQt5.QtCore import * # QEventLopp 사용하기 위해서
from config.errorCode import *
from PyQt5.QtTest import * # QTest 사용하기위해서
from config.kiwoomType import *
from config.log_class import * # 로그 기록용
from config.slack import * # 슬랙 사용용
import os
import sys

class test(QAxWidget):  #setControl 사용하기위해 상속
    def __init__(self):
        super().__init__()
        self.logging = Logging() # 로그 인스턴스, print-debbug로 바꾸기
        self.slack = Slack() # 슬랙 인스턴스화
        self.logging.logger.debug("test Start")

        ####### event loop를 실행하기 위한 변수 모음
        self.login_event_loop = QEventLoop()
        self.detail_account_info_event_loop = QEventLoop() # 예수금 요청용 이벤트 루프
        self.calculator_event_loop = QEventLoop()

        ####### 종목정보 가져오기
        self.portfolio_stock_dict = {}
        self.jango_dict = {} # 체결잔고 반환

        ########## 종목 분석용
        self.calcul_data = []

        #### 계좌 관련 변수
        self.account_stock_dict = {} # 다중데이터일때 정보가져오면 배열로 저장해두기
        self.not_account_stock_dict = {} # 미체결종목 저장하는 딕셔너리
        self.account_num = None # 계좌번호
        self.deposit = 0 # 예수금
        self.use_money = 0 # 실제 투자할 금액
        self.use_money_percent = 0.5 # 예수금에서 실제 사용할 비율
        self.output_deposit = 0 # 출금가능 금액
        self.total_profit_loss_money = 0 # 총평가손익금액
        self.total_profit_loss_rate = 0.0 # 총수익율(%)

        ############# 요청 스크린 번호 - 장바구니에 담는 개념
        self.screen_my_info = "2000" # 계좌 관련 스크린 번호
        self.screen_calculation_stock = "4000" # 계산용 스크린 번호
        self.screen_real_stock = "5000" # 종목별 실시간 정보를 가져올때 사용
        self.screen_meme_stock = "6000" # 종목별 주문할때 사용
        self.screen_start_stop_real = "1000" # 장 시작/ 종료 실시간 스크린 번호


        ############# 초기 셋팅 함수들 바로실행
        self.get_ocx_instance()
        self.event_slots() # 키움과 연결하기위한 시그널 슬롯 모음
        self.real_event_slot() # 실시간 이벤트 시그널 / 슬롯 모음
        self.signal_login_commConnect() # 로그인 요청함수 포함
        self.get_account_info() # 계좌번호 가져오기
        self.detail_account_info() # 예수금 요청 시그널 포함
        self.detail_account_mystock() # 계좌평가잔고내역 가져오기
        QTimer.singleShot(5000, self.not_concluded_account) # 5초뒤에 not 함수 실행하라는 뜻
        """
        한번에 너무많이 tr요청하면 규제당해서 5초 타이머설정
        여기서 타이머를 설정하는 2가지방법이 존재 Qtime.singleShot(ms, 함수) vs QTest.qWait(ms)
        전자는 동시성 처리를 지원하면서 몇초뒤에 함수실행
        후자는 동시성 처리를 지원하지않지만, 기존에 동작중인 이벤트는 유지
        동시성 처리를 지원하면 뒤에코드를 실행하지만, 동시성처리를 지원하지않으면 그자리에서 코드가 멈춘다.
        """
        ##################################################################

        QTest.qWait(10000)
        self.read_code() # 기다렸다가 분석해놓은 코드 읽어오기
        self.screen_number_setting() #스크린 번호를 할당하는 코드를 관리

        # 실시간 수신 관련 함수
        QTest.qWait(5000) # 트래픽떄문에 기달리기
        self.realType = RealType() # realtype 인스턴스화
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", self.screen_start_stop_real, '',
                         self.realType.REALTYPE['장시작시간']['장운영구분'], "0")

        """
        1번쨰 인수로 스크린 번호
        2번째 string변수로 종목코드를 보내지만, 아무것도 보내지않으면 주식시장의 시간상태를 실시간으로 체크해서 슬롯으로 받겠다라는 의미
        3번째 인수로 FID번호 보냄 ex) 주식체결 이것만보내면 그에해당하는 하위변수들이 다 나타남
        4번째 실시간 정보등록 0: 이전 다지우고 새로, 1: 원래있던거에 추가
        """

        "스크린 번호를 등록하는 코드"
        for code in self.portfolio_stock_dict.keys():
            screen_num = self.portfolio_stock_dict[code]['스크린번호']
            fids = self.realType.REALTYPE['주식체결']['체결시간']
            self.dynamicCall("SetRealReg(QString, QString, QString, QString)", screen_num, code, fids, "1")
            # 해당스크린번호에 추가가

        self.slack.notification(
            pretext="주식자동화 프로그램 동작",
            title="주식자동화 프로그램 동작",
            fallback="주식자동화 프로그램 동작",
            text="주식자동화 프로그램 동작 되었습니다."
        )

        ####### 전체 종목을 한번에 관리할때
        self.all_stock_dict = {}
        ######################################



    def get_ocx_instance(self): # 키움 API 레지스트리 실행
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        # setControl() : ocx 확장자 사용가능하게해주고 API모듈을 파이썬에서 사용할수있게 해준다.
        # COM객체를 인스턴트화 해주는 함수

    def event_slots(self): # 키움과 연걸하기 위한 시그널 / 슬롯 모음
        """
        이벤트.연결(슬롯) : 결과값을 받을 슬롯을 연결 - 이벤트 함수의 역할
        여기있는 이벤트들은 stduio에 이벤트 함수들을 그대로 사용(조회와 실시간 데이터처리 에 존재)
        """
        self.OnEventConnect.connect(self.login_slot) # 로그인 이벤트함수
        self.OnReceiveTrData.connect(self.trdata_slot) # TR 요청 관련, GetCommData 함수로 데이터 얻어옴
        # 조회요청 응답을 받거나 조회데이터를 받았을때 자동으로 호출됌
        self.OnReceiveMsg.connect(self.msg_slot) # 키움으로 부터 메세지 받아오기

    def real_event_slot(self):
        self.OnReceiveRealData.connect(self.realdata_slot)  # 실시간 이벤트 연결
        self.OnReceiveChejanData.connect(self.chejan_slot) # 체결 장고 관련 이벤트 연결

    def signal_login_commConnect(self):
        self.dynamicCall("CommConnect()") # 로그인 시그널
        # dynamicall() 은 PyQt5에서 제공하는 함수로 서버에 데이터를 송수신하는 기능
        # 매개변수로 시그널을 보냄
        # 시그널함수 : 말그대로 요청을 보내는 함수
        self.login_event_loop.exec_() # 로그인 이벤트루프 실행

    def login_slot(self, err_code): # 로그인을 받는 슬롯 만들기
        self.logging.logger.debug(errors(err_code)[1])

        self.login_event_loop.exit() # 로그인 이벤트 루프 종료

    def get_account_info(self): # 로그인 되어있기때문에 이벤트루프 필요없다.
        account_list = self.dynamicCall("GetLoginInfo(QString)", "ACCNO")
        # QString은 pyqt5에서 제공하는 공용 문자열
        account_num = account_list.split(';')[0]

        self.account_num = account_num
        self.logging.logger.debug("계좌번호 : %s" % account_num )

    def detail_account_info(self, sPrevNext="0"): # 예수금 요청 시그널
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "0000")
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(QString, QString)", "조회구분", 1)
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "예수금상세현황요청",
                         "opw00001", sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

        """
        sPrevNext : 0 첫페이지, 2 다음페이지
        SetInputValue : opw00001조회하면 이함수가 매개변수 2개를 이용해서 4개로 입력값을 설정하는걸 그대로 옮김
        CommRqData : 서버로 전송하는 함수 api studio에 나타나있음 
        위에 두함수로 서버에 원하는 시그널 전송
        
        dynamicall 함수로 시그널을 보낼때 정해진 함수를 사용해서 보낸다.
        정해진함수를 사용할때는 매개변수를 포함한 함수를 쓰고, 그뒤에 ','로 값들 같이 보내기
        이걸로 조회요청을 했기떄문에 OnReceiveTrData 함수가 호출됌
        "예수금상세현황요청"은 정해진게아니라 내가원하는걸로 - 뒤에 sRQName에서 사용하기위한것
        """

    def detail_account_mystock(self, sPrevNext="0"):
        """
        info와 다른점은 opw00018로 tr번호만다르지만, 다르게받을걸 활용하기위해 "계좌평가잔고내역요청"이름만 다르게받는다
        물론 SetInputValue 인자가 같은이유는 studio 오른쪽 상단 요구인자가 같기떄문

        이벤트루프가 없으면 꼬이기 떄문에 보낼떄 이벤트 루프 실행 - 받을때 끄기
        """
        self.dynamicCall("SetInputValue(QString, QString)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)", "비밀번호", "0000")
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



    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext): # TR 데이터 받을 슬롯, 매개변수는 studio순서 맞춰서
        if sRQName == "예수금상세현황요청": # if로 나누는 이유는 TR데이터를 많이 받는데 구분하기 위해서이다.
            """ 
            OnReceiveTrData 함수를 사용할때 이 이벤트안에서 GetCommData() 를 이용해서 내용 가져올수있음
            위의 함수안에 Get함수가 존재, 원하는 부분만 가져올때 사용가능
            
            GetCommData를 이용해서 전달받은 opw의 모든 데이터로부터 원하는것만 매개변수를 이용해서 가져온다.
            조회할수있는 종목은 studio 싱글데이터 목록에 한글로 되어있는것 입력
            studio 사용할때 조회눌러서 전문출력했을때 나오는 항목들이 다 싱글데이터
            """
            deposit = self.dynamicCall("GetCommData(QString, QString, int, QString)"
                                       ,sTrCode, sRQName, 0, "예수금")
            self.deposit = int(deposit) # 앞에 0000... 뺴기

            use_money = float(self.deposit) * self.use_money_percent
            self.use_money = int(use_money) / 4

            output_deposit = self.dynamicCall("GetCommData(QString, QString, int, QString)"
                                       ,sTrCode, sRQName, 0, "출금가능금액")
            self.output_deposit = int(output_deposit)

            self.logging.logger.debug("예수금 : %s" % self.output_deposit)

            self.stop_screen_cancel(self.screen_my_info)

            self.detail_account_info_event_loop.exit()

        if sRQName == "계좌평가잔고내역요청":
            """
            여기서 그냥 사용하면 답변이 오기전에 코드가 꼬이기 때문에 이벤트 루프를 통해서 받을필요가 생김
            방식은 요청-루프실행, 받을때-루프종료
            """
            total_buy_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "총매입금액")
            self.total_buy_money = int(total_buy_money)
            total_profit_loss_money = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                                   "총평가손익금액")
            self.total_profit_loss_money = int(total_profit_loss_money)
            total_profit_loss_rate = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0,
                                                  "총수익률(%)")
            self.total_profit_loss_rate = float(total_profit_loss_rate)

            self.logging.logger.debug("계좌평가잔고내역요청 싱글데이터 : %s - %s - %s" % (total_buy_money, total_profit_loss_money, total_profit_loss_rate))

            """
            보유중인 종목이 몇개인지 카운트 하는것
            GetRepeatCnt함수는 개발가이드 로그인처리 항목에 있음 이렇게 존재하는함수 dynamicCall해서 사용
            그리고 이함수는 OnRecieve에서만 사용가능함
            """
            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)

            for i in range(rows):
                # 그전까지 getCommData int는 0이였지만 멀티데이터처리할때는 i로 몇번째 index 전달
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

                self.logging.logger.debug("종목코드: %s - 종목명: %s - 보유수량: %s - 매입가:%s - 수익률: %s - 현재가: %s" % (
                    code, code_nm, stock_quantity, buy_price, learn_rate, current_price))

                # 여기서 code는 종목번호로 key - int, value - list이다. 그래서 각원소에 각각 하나씩
                if code in self.account_stock_dict:  # dictionary 에 해당 종목이 있나 확인
                    pass
                else:
                    self.account_stock_dict[code] = {} # 없으면 추가

                code_nm = code_nm.strip()
                stock_quantity = int(stock_quantity.strip())
                buy_price = int(buy_price.strip())
                learn_rate = float(learn_rate.strip())
                current_price = int(current_price.strip())
                total_chegual_price = int(total_chegual_price.strip())
                possible_quantity = int(possible_quantity.strip())

                # int인 code 한개당 - 밑에 7가지 항목 같고있음 (2차원배열)
                self.account_stock_dict[code].update({"종목명": code_nm})
                self.account_stock_dict[code].update({"보유수량": stock_quantity})
                self.account_stock_dict[code].update({"매입가": buy_price})
                self.account_stock_dict[code].update({"수익률(%)": learn_rate})
                self.account_stock_dict[code].update({"현재가": current_price})
                self.account_stock_dict[code].update({"매입금액": total_chegual_price})
                self.account_stock_dict[code].update({'매매가능수량': possible_quantity})

            self.logging.logger.debug("sPreNext : %s" % sPrevNext) # 다음페이지 존재 : 2, 없으면 : 0
            self.logging.logger.debug("계좌에 가지고 있는 종목은 %s " % rows)

            if sPrevNext == "2": # 다음이 존재하면 sPrevNext를 2로 설정해서 한번더 요청
                self.detail_account_mystock(sPrevNext="2")
                """
                이상태로하면 이벤트 루프떄문에 안된다.
                그래서 이벤트 루프를 전역변수로 선언해야 두번 생성하지않고 받고 끊고 넘겨서 다시켜고가 가능하다.
                """
            else: # 없으면 끄기
                self.detail_account_info_event_loop.exit() # 내용을 다받았으니 끄기

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

                self.logging.logger.debug("미체결 종목 : %s "  % self.not_account_stock_dict[order_no])

            self.detail_account_info_event_loop.exit()

        elif sRQName == "주식일봉차트조회":
            code = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "종목코드")
            # 0 대입하면 오늘자 하루 데이터만 가져오는것
            code = code.strip()
            # data = self.dynamicCall("GetCommDataEx(QString, QString)", sTrCode, sRQName)
            # [[‘’, ‘현재가’, ‘거래량’, ‘거래대금’, ‘날짜’, ‘시가’, ‘고가’, ‘저가’. ‘’], [‘’, ‘현재가’, ’거래량’, ‘거래대금’, ‘날짜’, ‘시가’, ‘고가’, ‘저가’, ‘’]. […]]
            """
            GetCommDataEx 함수 - 600일치 데이터 가져오기
            아니면 GetCommData 함수 사용해서 이상의 데이터를 가져오기
            """

            cnt = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName) # 멀티데이터조회할때 개수받아오는 함수
            self.logging.logger.debug("남은 일자 수 %s" % cnt)


            for i in range(cnt): # 여기서는 종목의 개수가아니라 한종목의 "일수"
                data = [] # GetCommDataEx 로 데이터 가져올때 나오는 이중 리스트 형태와 똑같이 만들기위해

                current_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "현재가")  # 출력 : 000070
                value = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "거래량")  # 출력 : 000070
                trading_value = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "거래대금")  # 출력 : 000070
                date = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "일자")  # 출력 : 000070
                start_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "시가")  # 출력 : 000070
                high_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "고가")  # 출력 : 000070
                low_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "저가")  # 출력 : 000070

                data.append("")
                data.append(current_price.strip())
                data.append(value.strip())
                data.append(trading_value.strip())
                data.append(date.strip())
                data.append(start_price.strip())
                data.append(high_price.strip())
                data.append(low_price.strip())
                data.append("")

                self.calcul_data.append(data.copy()) #리스트는 주소값을 이기때문에 복사본으로 값만 넘겨야함


            if sPrevNext == "2": # 과거 데이터가 존재하면 2로 바뀐다.
                self.day_kiwoom_db(code=code, sPrevNext=sPrevNext) # 재귀적인 성질때문에 뒤에 데이터가 더존재하면 600개씩 가져옴

            else: # 없으면 더이상 존재하지않으니 이벤트루프 종료
                self.logging.logger.debug("총 일수 %s" % len(self.calcul_data))

                ######################## 여기서부터  그랜빌 방법 추후에 딥러닝으로 대체

                pass_success = False # 120 선 종목이 가능한지 확인하기위한 변수

                # 120일 이평선을 그릴만큼의 데이터가 있는지 체크
                if self.calcul_data == None or len(self.calcul_data) < 120:
                    pass_success = False

                else: # 이평선은 키움api에 존재하지않아서 만들어서 써야한다.
                    # 120일 이평선의 최근 가격 구함
                    total_price = 0
                    for value in self.calcul_data[:120]:
                        total_price += int(value[1])
                    moving_average_price = total_price / 120

                    # 오늘자 주가가 120일 이평선에 걸쳐있는지 확인
                    bottom_stock_price = False
                    check_price = None
                    if int(self.calcul_data[0][7]) <= moving_average_price and moving_average_price <= int(self.calcul_data[0][6]):
                        # 리스트의 데이터 꼴을보면 [0][n]에서 0은 첫번째 정보이고 N을 그정보의 값으로 ex)7: 고가, 6: 저가
                        self.logging.logger.debug("오늘 주가 120이평선 아래에 걸쳐있는 것 확인")
                        bottom_stock_price = True
                        check_price = int(self.calcul_data[0][6])


                    # 과거 일봉 데이터를 조회하면서 120일 이평선보다 주가가 계속 밑에 존재하는지 확인
                    prev_price = None
                    if bottom_stock_price == True:

                        moving_average_price_prev = 0
                        price_top_moving = False
                        idx = 1
                        while True:

                            if len(self.calcul_data[idx:]) < 120:  # 120일치가 있는지 계속 확인
                                self.logging.logger.debug("120일치가 없음")
                                break

                            total_price = 0
                            for value in self.calcul_data[idx:120+idx]:
                                total_price += int(value[1])
                            moving_average_price_prev = total_price / 120

                            if moving_average_price_prev <= int(self.calcul_data[idx][6]) and idx <= 20:
                                self.logging.logger.debug("20일 동안 주가가 120일 이평선과 같거나 위에 있으면 조건 통과 못함")
                                price_top_moving = False
                                break

                            elif int(self.calcul_data[idx][7]) > moving_average_price_prev and idx > 20:  # 120일 이평선 위에 있는 구간 존재
                                self.logging.logger.debug("120일치 이평선 위에 있는 구간 확인됨")
                                price_top_moving = True
                                prev_price = int(self.calcul_data[idx][7])
                                break

                            idx += 1

                        # 해당부분 이평선이 가장 최근의 이평선 가격보다 낮은지 확인
                        if price_top_moving == True:
                            if moving_average_price > moving_average_price_prev and check_price > prev_price:
                                self.logging.logger.debug("포착된 이평선의 가격이 오늘자 이평선 가격보다 낮은 것 확인")
                                self.logging.logger.debug("포착된 부분의 저가가 오늘자 주가의 고가보다 낮은지 확인")
                                pass_success = True

                if pass_success == True: # 조건이 모두 맞으면 통과
                    self.logging.logger.debug("조건부 통과됨")

                    code_nm = self.dynamicCall("GetMasterCodeName(QString)", code)

                    f = open("files/condition_stock.txt", "a", encoding="utf8")
                    f.write("%s\t%s\t%s\n" % (code, code_nm, str(self.calcul_data[0][1])))
                    f.close()

                elif pass_success == False:
                    self.logging.logger.debug("조건부 통과 못함")

                self.calcul_data.clear() # 다음종목 분석하기위해 비우기
                self.calculator_event_loop.exit()

                """
                종목명을 이용해서 파일에 저장하기
                open("저장폴더/파일명", "쓰기조건(a: 이어쓰기, w: 새로쓰기)", "인코딩")
                이름만 저장하면 나중에 이름만 가져와서 사용하는방식식
                """

    def stop_screen_cancel(self, sScrNo=None): # 요청 안끊으면 뒤에입력 못받음 나중에 추가설명 하기
        self.dynamicCall("DisconnectRealData(QString)", sScrNo)

    def get_code_list_by_market(self, market_code): #주식 시장 종목 가져오는 함수
        '''
        종목코드 리스트 받기
        #0:KOSPI, 10:코스닥

        :param market_code: 시장코드 입력

        GetCodeListByMarket(QString) - market_code 매개변수로 넘기면
        :return: 종목 코드들이 ;기준으로 넘어옴 ex) 156184;854612;
        '''
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_code)
        code_list = code_list.split(';')[:-1] # 맨마지막에 '' 처럼 빈칸이 오기때문에 마지막은 제외하고 자른다.
        return code_list

    def calculator_fnc(self):
        '''
        get_code_list_by_market 함수를 이용해서 가져온 데이터를 통해서 분석하는 함수
        가져온 데이터가 종목 코드이니 이 코드를 이용해서 TR보내면 그 종목에대한 정보를 가져오는 형식
        '''

        code_list = self.get_code_list_by_market("10") # 코스닥 정보 가져오기
        self.logging.logger.debug("코스닥 갯수 %s " % len(code_list))

        for idx, code in enumerate(code_list):
            self.dynamicCall("DisconnectRealData(QString)", self.screen_calculation_stock)  # 스크린 연결 끊기
            # 연결을 끊음으로써 키움서버에 요청한 내용을 지운다.
            # 스크린을 끊는 이유는 한정된 공간에 너무많은 데이터를 넣으면 데이터 오버플로우발생하니 끊기

            self.logging.logger.debug("%s / %s :  KOSDAQ Stock Code : %s is updating... " % (idx + 1, len(code_list), code))
            self.day_kiwoom_db(code=code) # 각종목의 데이터를 요구하는 함수 실행

    def day_kiwoom_db(self, code=None, date=None, sPrevNext="0"): # 특정종목의 일봉 데이터 TR요청하기
        QTest.qWait(4000)  # 3.6초마다 딜레이를 준다.
        """
        여기서 sleep() 이나 timer() 함수를 사용하지 않은 이유는 이벤트 처리떄문이다.
        두개는 멈추는동안 이벤트역시 멈추기때문에 중간에 이벤트가 끊겨서 에러가 발생한다.
        
        QTest.qWait 은 서버에 요청한 이벤트와 이벤트 루프의 동작은 유지하면서, 타이머를 건다.
        """

        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        # 수정주가구분은 회사가 액면가분할처럼 시가총액은 같은데 주식수를 늘린것을 반영하면 1, 이전값은 0

        if date != None: # 특정 날짜부터 사용할예정이면 이함수 사용
            self.dynamicCall("SetInputValue(QString, QString)", "기준일자", date) # data 양식은 YYYYMMDD

        self.dynamicCall("CommRqData(QString, QString, int, QString)", "주식일봉차트조회", "opt10081", sPrevNext,
                         self.screen_calculation_stock)  # Tr서버로 전송 -Transaction

        self.calculator_event_loop.exec_()

    def read_code(self): # 분석해놓은 파일 불어올때 사용하는 함수
        if os.path.exists("files/condition_stock.txt"): # 해당 경로에 파일이 있는지 체크한다.
            f = open("files/condition_stock.txt", "r", encoding="utf8") # "r"을 인자로 던져주면 파일 내용을 읽어 오겠다는 뜻이다.

            lines = f.readlines() #파일에 있는 내용들이 모두 읽어와 진다.
            for line in lines: #줄바꿈된 내용들이 한줄 씩 읽어와진다.
                if line != "":
                    ls = line.split("\t") # \t 기준으로 넣었기 때문에

                    stock_code = ls[0]
                    stock_name = ls[1]
                    stock_price = int(ls[2].split("\n")[0])
                    stock_price = abs(stock_price)

                    self.portfolio_stock_dict.update({stock_code:{"종목명":stock_name, "현재가":stock_price}})
            f.close()

    def screen_number_setting(self): # 스크린 번호를 할당하는 함수수
        screen_overwrite = [] # 계좌평가, 미체결, 포트폴리오에 담긴 종목코드들을 중복되지않게 모으는 역할

        #계좌가잔고내역에 있는 종목들
        for code in self.account_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)


        #미체결에 있는 종목들
        for order_number in self.not_account_stock_dict.keys():
            code = self.not_account_stock_dict[order_number]['종목코드']

            if code not in screen_overwrite:
                screen_overwrite.append(code)


        #포트폴리로에 담겨있는 종목들
        for code in self.portfolio_stock_dict.keys():

            if code not in screen_overwrite:
                screen_overwrite.append(code)


        # 스크린번호 할당
        cnt = 0 # 종목 개수
        for code in screen_overwrite:

            temp_screen = int(self.screen_real_stock)
            meme_screen = int(self.screen_meme_stock)

            if (cnt % 50) == 0:
                temp_screen += 1
                self.screen_real_stock = str(temp_screen)

            if (cnt % 50) == 0:
                meme_screen += 1
                self.screen_meme_stock = str(meme_screen)

            if code in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict[code].update({"스크린번호": str(self.screen_real_stock)})
                self.portfolio_stock_dict[code].update({"주문용스크린번호": str(self.screen_meme_stock)})

            elif code not in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict.update({code: {"스크린번호": str(self.screen_real_stock), "주문용스크린번호": str(self.screen_meme_stock)}})

            cnt += 1

        """
        스크린하나당 100개씩 요청할수있다. 50개에 하나씩 추가해서 안전하게 사용하기
        포트폴리오 딕셔너리에 추가하는 이유는 실시간 정보를 처리하기위해서이다.
        종목마다 스크린 번호를 할당하면 실시간 정보를 일대일대응으로 알수있다.
        
        screen_overwrite 에 종목코드들이 들어가있고 한 스크린에 50개씩 들어갈때마다 새로운 스크린추가
        cnt : 종목개수로 한번돌때마다 항상추가
        """

    def realdata_slot(self, sCode, sRealType, sRealData): # 이벤트로 연결한 실시간 슬롯
        """
        :param sCode: 요청한 종목의 코드 ex)"091349"
        :param sRealType: 받을 실시간 데이터(ex 호가잔량) - FID(왼쪽에 있는 숫자), 넘어올때는 한글로넘어옴
        :param sRealData: 실시간으로 받는 데이터의 리스트
        :return:
        """

        if sRealType == "장시작시간": # 한글값 그대로 넘어옴, FID값 아님
            fid = self.realType.REALTYPE[sRealType]['장운영구분']  # (0:장시작전, 2:장종료전(20분), 3:장시작, 4,8:장종료(30분), 9:장마감)
            value = self.dynamicCall("GetCommRealData(QString, int)", sCode, fid)
            "GetCommData 대신 실시간에서는 GetCommRealData 로 쪼개서 받는다."

            if value == '0':
                self.logging.logger.debug("장 시작 전")

            elif value == '3':
                self.logging.logger.debug("장 시작")

            elif value == "2":
                self.logging.logger.debug("장 종료, 동시호가로 넘어감")

            elif value == "4":
                self.logging.logger.debug("3시30분 장 종료")

                # 장이 종료되면 실시간 이벤트 다끊기
                for code in self.portfolio_stock_dict.keys():
                    self.dynamicCall("SetRealRemove(QString, QString)", self.portfolio_stock_dict[code]['스크린번호'], code)

                """장 종료하고 종목분석후 프로그램 종료"""
                QTest.qWait(5000)

                self.file_delete() # 기존에있던 파일 지우고 새로쓰기
                self.calculator_fnc() # 종목분석

                sys.exit()

        # 실시간정보를 이용해서 살지말지 결정하는 파트트
        elif sRealType == "주식체결":
            a = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['체결시간'])  # 출력 HHMMSS
            b = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['현재가'])  # 출력 : +(-)2520
            b = abs(int(b))

            c = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['전일대비'])  # 출력 : +(-)2520
            c = abs(int(c))

            d = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['등락율'])  # 출력 : +(-)12.98
            d = float(d)

            e = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['(최우선)매도호가'])  # 출력 : +(-)2520
            e = abs(int(e))

            f = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['(최우선)매수호가'])  # 출력 : +(-)2515
            f = abs(int(f))

            g = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['거래량'])  # 출력 : +240124  매수일때, -2034 매도일 때
            g = abs(int(g))

            h = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['누적거래량'])  # 출력 : 240124
            h = abs(int(h))

            i = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['고가'])  # 출력 : +(-)2530
            i = abs(int(i))

            j = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['시가'])  # 출력 : +(-)2530
            j = abs(int(j))

            k = self.dynamicCall("GetCommRealData(QString, int)", sCode,
                         self.realType.REALTYPE[sRealType]['저가'])  # 출력 : +(-)2530
            k = abs(int(k))

            if sCode not in self.portfolio_stock_dict:
                self.portfolio_stock_dict.update({sCode: {}})

            self.portfolio_stock_dict[sCode].update({"체결시간": a})
            self.portfolio_stock_dict[sCode].update({"현재가": b})
            self.portfolio_stock_dict[sCode].update({"전일대비": c})
            self.portfolio_stock_dict[sCode].update({"등락율": d})
            self.portfolio_stock_dict[sCode].update({"(최우선)매도호가": e})
            self.portfolio_stock_dict[sCode].update({"(최우선)매수호가": f})
            self.portfolio_stock_dict[sCode].update({"거래량": g})
            self.portfolio_stock_dict[sCode].update({"누적거래량": h})
            self.portfolio_stock_dict[sCode].update({"고가": i})
            self.portfolio_stock_dict[sCode].update({"시가": j})
            self.portfolio_stock_dict[sCode].update({"저가": k})

            "여기까지 종목의 실시간 정보를 받아오는 과정이고 다음부터 실시간으로 분석하는 과정"
            """############## 기존 평가잔고에있는 종목 매도 ################"""
            if sCode in self.account_stock_dict.keys() and sCode not in self.jango_dict.keys(): #실시간으로 매수된적이 없어야하므로 jango_dict에 없어야한다.
                asd = self.account_stock_dict[sCode]
                meme_rate = (b - asd['매입가']) / asd['매입가'] * 100

                if asd['매매가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):

                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["신규매도", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 2, sCode, asd['매매가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ""]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매도주문 전달 성공")
                        del self.account_stock_dict[sCode]
                    else:
                        self.logging.logger.debug("매도주문 전달 실패")
                """################### 실시간 매도 ##########################"""
            elif sCode in self.jango_dict.keys(): # 잔고에 존재하는지 확인
                jd = self.jango_dict[sCode]
                meme_rate = (b - jd['매입단가']) / jd['매입단가'] * 100 # 매입기준 현재 얼마나 차이나는지

                if jd['주문가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5): # 여기서는 +- 5%기준으로 매매하는루트

                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["신규매도", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 2, sCode, jd['주문가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ""]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매도주문 전달 성공")
                    else:
                        self.logging.logger.debug("매도주문 전달 실패")

                "####################### 실시간 매수 - 매수취소 과정 ############################"
            elif d > 2.0 and sCode not in self.jango_dict: #장고에 없는 종목 and 등락율 > 2.0 이면 매수 방법
                self.logging.logger.debug("매수조건 통과 %s " % sCode)

                result = (self.use_money * 0.1) / e
                quantity = int(result) # 수량구하는 방법

                order_success = self.dynamicCall(
                    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                    ["신규매수", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 1, sCode, quantity, e, self.realType.SENDTYPE['거래구분']['지정가'], ""]
                )

                if order_success == 0: # 0이면 성공 이외는 실패, 1초에 최대 5번 주문가능
                    self.logging.logger.debug("매수주문 전달 성공")
                else:
                    self.logging.logger.debug("매수주문 전달 실패")


            not_meme_list = list(self.not_account_stock_dict) # 리스트로 copy 하는이유는 중간에 원소가 추가되면 오류로 프로그램 종료됌
            for order_num in not_meme_list: # 모든주문은 주문이 체결되기 전까지 미체결
                code = self.not_account_stock_dict[order_num]["종목코드"]
                meme_price = self.not_account_stock_dict[order_num]['주문가격']
                not_quantity = self.not_account_stock_dict[order_num]['미체결수량']
                order_gubun = self.not_account_stock_dict[order_num]['주문구분']


                if order_gubun == "매수" and not_quantity > 0 and e > meme_price: # 주문가격이 최우선 매도호가가 주문가격보다 높아지면 취소
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["매수취소", self.portfolio_stock_dict[sCode]["주문용스크린번호"], self.account_num, 3, code, 0, 0, self.realType.SENDTYPE['거래구분']['지정가'], order_num]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매수취소 전달 성공")
                    else:
                        self.logging.logger.debug("매수취소 전달 실패")

                elif not_quantity == 0: # 취소가 완료되면
                    del self.not_account_stock_dict[order_num] # 미체결 해당부분 삭제

    def chejan_slot(self, sGubun, nItemCnt, sFidList): # 주문이 들어가면 결과 데이터를 반환받는 함수
        """
        :param sGubun: 0: 주문체결, 1: 잔고, 4: 파생잔고
        :param nItemCnt:
        :param sFidList:
        :return:
        """
        if int(sGubun) == 0: # 주문 체결 - 접수 확인 체결 과정
            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목명'])
            stock_name = stock_name.strip()

            origin_order_number = self.dynamicCall("GetChejanData(int)",
                                                   self.realType.REALTYPE['주문체결']['원주문번호'])  # 출력 : defaluse : "000000"
            order_number = self.dynamicCall("GetChejanData(int)",
                                            self.realType.REALTYPE['주문체결']['주문번호'])  # 출럭: 0115061 마지막 주문번호

            order_status = self.dynamicCall("GetChejanData(int)",
                                            self.realType.REALTYPE['주문체결']['주문상태'])  # 출력: 접수, 확인, 체결
            order_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문수량'])  # 출력 : 3
            order_quan = int(order_quan)

            order_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문가격'])  # 출력: 21000
            order_price = int(order_price)

            not_chegual_quan = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['미체결수량'])  # 출력: 15, default: 0
            not_chegual_quan = int(not_chegual_quan)

            order_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문구분'])  # 출력: -매도, +매수
            order_gubun = order_gubun.strip().lstrip('+').lstrip('-')

            chegual_time_str = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['주문/체결시간'])  # 출력: '151028'

            chegual_price = self.dynamicCall("GetChejanData(int)",
                                             self.realType.REALTYPE['주문체결']['체결가'])  # 출력: 2110  default : ''
            if chegual_price == '': # 체결가는 데이터가 없으면 ''로 반환되서 0으로 바꿔주기
                chegual_price = 0
            else:
                chegual_price = int(chegual_price)

            chegual_quantity = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['체결량'])  # 출력: 5  default : ''
            if chegual_quantity == '':
                chegual_quantity = 0
            else:
                chegual_quantity = int(chegual_quantity)

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['현재가'])  # 출력: -6000
            current_price = abs(int(current_price))

            first_sell_price = self.dynamicCall("GetChejanData(int)",
                                                self.realType.REALTYPE['주문체결']['(최우선)매도호가'])  # 출력: -6010
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)",
                                               self.realType.REALTYPE['주문체결']['(최우선)매수호가'])  # 출력: -6000
            first_buy_price = abs(int(first_buy_price))

            ######## 새로 들어온 주문이면 주문번호 할당
            if order_number not in self.not_account_stock_dict.keys():
                self.not_account_stock_dict.update({order_number: {}})

            self.not_account_stock_dict[order_number].update({"종목코드": sCode})
            self.not_account_stock_dict[order_number].update({"주문번호": order_number})
            self.not_account_stock_dict[order_number].update({"종목명": stock_name})
            self.not_account_stock_dict[order_number].update({"주문상태": order_status})
            self.not_account_stock_dict[order_number].update({"주문수량": order_quan})
            self.not_account_stock_dict[order_number].update({"주문가격": order_price})
            self.not_account_stock_dict[order_number].update({"미체결수량": not_chegual_quan})
            self.not_account_stock_dict[order_number].update({"원주문번호": origin_order_number})
            self.not_account_stock_dict[order_number].update({"주문구분": order_gubun})
            self.not_account_stock_dict[order_number].update({"주문/체결시간": chegual_time_str})
            self.not_account_stock_dict[order_number].update({"체결가": chegual_price})
            self.not_account_stock_dict[order_number].update({"체결량": chegual_quantity})
            self.not_account_stock_dict[order_number].update({"현재가": current_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매도호가": first_sell_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매수호가": first_buy_price})

        elif int(sGubun) == 1: # 체결이되면 잔고가 바뀌니 그러면 1이 반환된다.
            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목코드'])[1:]

            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목명'])
            stock_name = stock_name.strip()

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['현재가'])
            current_price = abs(int(current_price))

            stock_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['보유수량'])
            stock_quan = int(stock_quan)

            like_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['주문가능수량'])
            like_quan = int(like_quan)

            buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매입단가'])
            buy_price = abs(int(buy_price))

            total_buy_price = self.dynamicCall("GetChejanData(int)",
                                               self.realType.REALTYPE['잔고']['총매입가'])  # 계좌에 있는 종목의 총매입가
            total_buy_price = int(total_buy_price)

            meme_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매도매수구분'])
            meme_gubun = self.realType.REALTYPE['매도수구분'][meme_gubun]

            first_sell_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매도호가'])
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매수호가'])
            first_buy_price = abs(int(first_buy_price))

            if sCode not in self.jango_dict.keys():
                self.jango_dict.update({sCode: {}})

            self.jango_dict[sCode].update({"현재가": current_price})
            self.jango_dict[sCode].update({"종목코드": sCode})
            self.jango_dict[sCode].update({"종목명": stock_name})
            self.jango_dict[sCode].update({"보유수량": stock_quan})
            self.jango_dict[sCode].update({"주문가능수량": like_quan})
            self.jango_dict[sCode].update({"매입단가": buy_price})
            self.jango_dict[sCode].update({"총매입가": total_buy_price})
            self.jango_dict[sCode].update({"매도매수구분": meme_gubun})
            self.jango_dict[sCode].update({"(최우선)매도호가": first_sell_price})
            self.jango_dict[sCode].update({"(최우선)매수호가": first_buy_price})

            if stock_quan == 0:
                del self.jango_dict[sCode]

        # 송수신 메세지 get
    def msg_slot(self, sScrNo, sRQName, sTrCode, msg):
        self.logging.logger.debug("스크린: %s, 요청이름: %s, tr코드: %s --- %s" % (sScrNo, sRQName, sTrCode, msg))

        # 파일 삭제
    def file_delete(self):
        if os.path.isfile("files/condition_stock.txt"):
            os.remove("files/condition_stock.txt")
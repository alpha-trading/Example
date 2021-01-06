import numpy as np
import utils
import random
"""
학습행동결정
지연보상 - 매도기준으로 손익률, 즉시보상 - 거래할때마다 -부여(초반에 할때마다 -이지만 e으로 탐험하면 올라갈여지있음)
"""

class Agent:
    '에이전트 상태가 구성하는 값 개수'
    STATE_DIM = 2  # 주식 보유 비율, 포트폴리오 가치 비율

    '매매 수수료 및 세금'
    TRADING_CHARGE = 0.00015  # 거래 수수료 0.015%
    TRADING_TAX = 0.0025  # 거래세 0.25%

    '행동'
    BUY_ten_per = 0  # 매수
    BUY_two_per = 1  # 매수
    BUY_thr_per = 2  # 매수
    BUY_fou_per = 3  # 매수
    BUY_fiv_per = 4  # 매수
    ACTION_SELL = 5  # 매도
    ACTION_HOLD = 6  # 홀딩

    """
    인공 신경망에서 확률을 구할 행동들
    공매도는 없다는 가정하에, 포지션없을때 -> 매도 = 관망
    매수포지션일때 ->  
    """

    ACTIONS = [BUY_ten_per, BUY_two_per, BUY_thr_per, BUY_fou_per, BUY_fiv_per, ACTION_SELL]
    NUM_ACTIONS = len(ACTIONS)  # 인공 신경망에서 고려할 출력값의 개수

    def __init__(
        self, _environment,):
        # Environment 객체
        # 현재 주식 가격을 가져오기 위해 환경 참조
        self.environment = _environment

        # Agent 클래스의 속성
        self.initial_balance = 0  # 초기 자본금
        self.balance = 0  # 현재 현금 잔고
        self.num_stocks = 0  # 보유 주식 수

        # 포트폴리오 가치: balance + num_stocks * {현재 주식 가격}
        self.portfolio_value = 0 # 이걸기준으로 매수% 선택하기
        self.prev_portfolio_value = 0  # 직전 학습 시점의 PV
        self.num_buy_10 = 0  # 매수 횟수
        self.num_buy_20 = 0  # 매수 횟수
        self.num_buy_30 = 0  # 매수 횟수
        self.num_buy_40 = 0  # 매수 횟수
        self.num_buy_50 = 0  # 매수 횟수
        self.num_sell = 0  # 매도 횟수
        self.num_hold = 0  # 홀딩 횟수
        self.immediate_reward = 0  # 즉시 보상
        self.profitloss = 0  # 현재 손익(직전 포폴대비, 매도기준 현 포폴가치)
        self.now_portfolio = 0 # 하한선 매도 체크용
        self.buy_penalty_reward = 0 # 매수할때마다 -1, 잦은 거래 방지

        # Agent 클래스의 상태
        self.ratio_hold = 0  # 주식 보유 비율
        self.ratio_portfolio_value = 0  # 포트폴리오 가치 비율

    '에이전트의 상태를 초기화'
    def reset(self):
        self.balance = self.initial_balance
        self.num_stocks = 0
        self.portfolio_value = self.initial_balance
        self.prev_portfolio_value = self.initial_balance
        self.num_buy_10 = 0  # 매수 횟수
        self.num_buy_20 = 0  # 매수 횟수
        self.num_buy_30 = 0  # 매수 횟수
        self.num_buy_40 = 0  # 매수 횟수
        self.num_buy_50 = 0  # 매수 횟수
        self.num_sell = 0
        self.num_hold = 0
        self.immediate_reward = 0
        self.ratio_hold = 0
        self.ratio_portfolio_value = 0
        self.now_portfolio = self.initial_balance
        self.buy_penalty_reward = 0

    def reset_exploration(self):
        self.exploration_base = 0.5 + np.random.rand() / 2

    '초기 자본금 설정'
    def set_balance(self, balance):
        self.initial_balance = balance

    '에이전트 상태 반환'
    def get_states(self):
        self.ratio_hold = self.num_stocks / int(
            self.portfolio_value / self.environment.get_price())
        self.ratio_portfolio_value = (
            self.portfolio_value / self.prev_portfolio_value
        )
        return (
            self.ratio_hold,
            self.ratio_portfolio_value
        )

    '탐험 또는 정책 신경망에 의한 행동 결정'
    def decide_action(self, pred_value, pred_policy, epsilon):

        pred = pred_policy
        if pred is None:
            pred = pred_value

        if pred is None:
            # 예측 값이 없을 경우 탐험
            epsilon = 1
        else:
            # 값이 모두 같은 경우 탐험
            maxpred = np.max(pred)
            if (pred == maxpred).all():
                epsilon = 1

        # 탐험 결정
        if np.random.rand() < epsilon:
            exploration = True
            action_num = random.randrange(0, 6)
            action = Agent.ACTIONS[action_num]

        else:
            exploration = False
            action_num = np.argmax(pred) # 정책을 이용한 방법
            action = Agent.ACTIONS[action_num]

        return action, exploration # 행동(숫자), 탐험여부

    '행동의 유효성 판단'
    def validate_action(self, action): #actions 배열인덱스로
        if action == Agent.BUY_ten_per:
            # 적어도 10%를 살 수 있는지 확인
            if self.balance < self.portfolio_value * 0.1:
                return False

        if action == Agent.BUY_two_per:
            # 적어도 20%를 살 수 있는지 확인
            if self.balance < self.portfolio_value * 0.2:
                return False

        if action == Agent.BUY_thr_per:
            # 적어도 30%를 살 수 있는지 확인
            if self.balance < self.portfolio_value * 0.3:
                return False

        if action == Agent.BUY_fou_per:
            # 적어도 40%를 살 수 있는지 확인
            if self.balance < self.portfolio_value * 0.4:
                return False

        if action == Agent.BUY_fiv_per:
            # 적어도 50%를 살 수 있는지 확인
            if self.balance < self.portfolio_value * 0.5:
                return False

        if action == Agent.ACTION_SELL:
            # 주식 잔고가 있는지 확인 
            if self.num_stocks <= 0:
                return False

        return True

    '매수할 주식 수 결정'
    def decide_trading_unit(self, action):
        if action == Agent.ACTIONS[0]:
            # 포폴기준 10퍼에 해당하는 주식수 return
            trading_size = int((self.portfolio_value * 0.1) / self.environment.get_closed_price())

        if action == Agent.ACTIONS[1]:
            # 포폴기준 20퍼에 해당하는 주식수 return
            trading_size = int((self.portfolio_value * 0.2) / self.environment.get_closed_price())

        if action == Agent.ACTIONS[2]:
            # 포폴기준 30퍼에 해당하는 주식수 return
            trading_size = int((self.portfolio_value * 0.3) / self.environment.get_closed_price())

        if action == Agent.ACTIONS[3]:
            # 포폴기준 40퍼에 해당하는 주식수 return
            trading_size = int((self.portfolio_value * 0.4) / self.environment.get_closed_price())

        if action == Agent.ACTIONS[4]:
            # 포폴기준 50퍼에 해당하는 주식수 return
            trading_size = int((self.portfolio_value * 0.5) / self.environment.get_closed_price())

        return trading_size

    '행동 수행 - reward 2개 반환'
    def act(self, _action):
        if not self.validate_action(_action):
            action = Agent.ACTION_HOLD

        # 환경에서 현재 가격 얻기
        curr_price = self.environment.get_closed_price()

        # 보상 초기화
        self.immediate_reward = 0
        self.buy_penalty_reward = 0

        # 10% 매수
        if action == Agent.ACTIONS[0]:
            # 매수할 단위를 판단
            trading_unit = self.decide_trading_unit(0)
            balance = (self.balance - curr_price * trading_unit)

            # 보유 현금이 모자랄 경우 보유 현금으로 가능한 만큼 최대한 매수 - 세금 계산(x)
            if balance < 0:
                trading_unit = int(self.balance / curr_price)

            # 수수료를 적용하여 총 매수 금액 산정
            invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount < self.balance:
                trading_unit -= trading_unit
                invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount > 0:
                self.balance -= invest_amount  # 보유 현금을 갱신
                self.num_stocks += trading_unit  # 보유 주식 수를 갱신
                self.num_buy += 1  # 매수 횟수 증가
                self.buy_penalty_reward -= 1

        # 20% 매수
        if action == Agent.ACTIONS[1]:
            # 매수할 단위를 판단
            trading_unit = self.decide_trading_unit(1)
            balance = (self.balance - curr_price * trading_unit)

            # 보유 현금이 모자랄 경우 보유 현금으로 가능한 만큼 최대한 매수 - 세금 계산(x)
            if balance < 0:
                trading_unit = int(self.balance / curr_price)

            # 수수료를 적용하여 총 매수 금액 산정
            invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount < self.balance:
                trading_unit -= trading_unit
                invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount > 0:
                self.balance -= invest_amount  # 보유 현금을 갱신
                self.num_stocks += trading_unit  # 보유 주식 수를 갱신
                self.num_buy += 1  # 매수 횟수 증가
                self.buy_penalty_reward -= 1

        # 30% 매수
        if action == Agent.ACTIONS[2]:
            # 매수할 단위를 판단
            trading_unit = self.decide_trading_unit(2)
            balance = (self.balance - curr_price * trading_unit)

            # 보유 현금이 모자랄 경우 보유 현금으로 가능한 만큼 최대한 매수 - 세금 계산(x)
            if balance < 0:
                trading_unit = int(self.balance / curr_price)

            # 수수료를 적용하여 총 매수 금액 산정
            invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount < self.balance:
                trading_unit -= trading_unit
                invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount > 0:
                self.balance -= invest_amount  # 보유 현금을 갱신
                self.num_stocks += trading_unit  # 보유 주식 수를 갱신
                self.num_buy += 1  # 매수 횟수 증가
                self.buy_penalty_reward -= 1

        # 40% 매수
        if action == Agent.ACTIONS[3]:
            # 매수할 단위를 판단
            trading_unit = self.decide_trading_unit(3)
            balance = (self.balance - curr_price * trading_unit)

            # 보유 현금이 모자랄 경우 보유 현금으로 가능한 만큼 최대한 매수 - 세금 계산(x)
            if balance < 0:
                trading_unit = int(self.balance / curr_price)

            # 수수료를 적용하여 총 매수 금액 산정
            invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount < self.balance:
                trading_unit -= trading_unit
                invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount > 0:
                self.balance -= invest_amount  # 보유 현금을 갱신
                self.num_stocks += trading_unit  # 보유 주식 수를 갱신
                self.num_buy += 1  # 매수 횟수 증가
                self.buy_penalty_reward -= 1

        # 50% 매수
        if action == Agent.ACTIONS[4]:
            # 매수할 단위를 판단
            trading_unit = self.decide_trading_unit(4)
            balance = (self.balance - curr_price * trading_unit)

            # 보유 현금이 모자랄 경우 보유 현금으로 가능한 만큼 최대한 매수 - 세금 계산(x)
            if balance < 0:
                trading_unit = int(self.balance / curr_price)

            # 수수료를 적용하여 총 매수 금액 산정
            invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount < self.balance:
                trading_unit -= trading_unit
                invest_amount = curr_price * (1 + self.TRADING_CHARGE) * trading_unit

            if invest_amount > 0:
                self.balance -= invest_amount  # 보유 현금을 갱신
                self.num_stocks += trading_unit  # 보유 주식 수를 갱신
                self.num_buy += 1  # 매수 횟수 증가
                self.buy_penalty_reward -= 1

        # 매도
        if action == Agent.ACTIONS[5]:
            # 전량 매도
            # 매도
            invest_amount = curr_price * (1 - (self.TRADING_TAX + self.TRADING_CHARGE)) * self.num_stocks
            if invest_amount > 0: # 0이하면 매도가 이뤄지지않은걸로 생각
                "현포폴 이전으로 넘기고, 매도후 포폴 갱신"
                self.prev_portfolio_value = self.portfolio_value  # 현재 포폴 이전값으로갱신, 마지막매도기준 포폴
                self.portfolio_value = self.balance + curr_price * self.num_stocks # 매도가정 포폴갱신

                "매도후 주식수, 가치 변경"
                self.num_stocks = 0  # 보유 주식 수를 갱신
                self.balance += invest_amount  # 보유 현금을 갱신
                self.num_sell += 1  # 매도 횟수 증가

                " 매도기준 손익 갱신 - 이전대비 손익비율"
                self.profitloss = (
                        (self.portfolio_value - self.prev_portfolio_value) / self.prev_portfolio_value
                )

                " 즉시보상 손익 갱신 기준으로 넣기"
                self.immediate_reward = self.profitloss

        # 홀딩
        if action == Agent.ACTIONS[6]:
            self.num_hold += 1  # 홀딩 횟수 증가

        " 체크용은 계속 가치 생신"
        self.now_portfolio = self.balance + curr_price * self.num_stocks  # 현 가치 계속 갱신
        # 이전가격대비 13퍼나 떨어지면 즉시 매도
        if (self.prev_portfolio_value - self.now_portfolio) / self.prev_portfolio_value > 0.13:
            # 매도
            invest_amount = curr_price * (1 - (self.TRADING_TAX + self.TRADING_CHARGE)) * self.num_stocks
            if invest_amount > 0:  # 0이하면 매도가 이뤄지지않은걸로 생각
                "현포폴 이전으로 넘기고, 매도후 포폴 갱신"
                self.prev_portfolio_value = self.portfolio_value  # 현재 포폴 이전값으로갱신, 마지막매도기준 포폴
                self.portfolio_value = self.balance + curr_price * self.num_stocks  # 매도가정 포폴갱신

                "매도후 주식수, 가치 변경"
                self.num_stocks = 0  # 보유 주식 수를 갱신
                self.balance += invest_amount  # 보유 현금을 갱신
                self.num_sell += 1  # 매도 횟수 증가

                " 매도기준 손익 갱신 - 이전대비 손익비율"
                self.profitloss = (
                        (self.portfolio_value - self.prev_portfolio_value) / self.prev_portfolio_value
                )

                " 즉시보상 손익 갱신 기준으로 넣기"
                self.immediate_reward = self.profitloss

        return self.immediate_reward, self.buy_penalty_reward
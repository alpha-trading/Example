import os
import logging
import abc
import collections
import threading
import time
import settings
import numpy as np
from agent import Agent
from utils import sigmoid
from environment import Environment
from agent import Agent
from networks import Network, DNN
from visualizer import Visualizer

"""
최소거래, 최대거래, 지연보상 - 삭제후 정리
"""
class ReinforcementLearner:
    __metaclass__ = abc.ABCMeta
    lock = threading.Lock()

    def __init__(self, rl_method='rl', stock_code=None,
                 chart_data=None, training_data=None,
                 net='dnn', num_steps=1, lr=0.001,
                 value_network=None, policy_network=None,
                 output_path='', reuse_models=False):
        # 인자 확인
        assert num_steps > 0
        assert lr > 0

        # 강화학습 기법 설정
        self.rl_method = rl_method

        # 환경 설정
        self.stock_code = stock_code
        self.chart_data = chart_data
        self.environment = Environment(chart_data)

        # 에이전트 설정
        self.agent = Agent(self.environment)

        # 학습 데이터
        self.training_data = training_data # 차트 데이터 전처리한것
        self.sample = None
        self.training_data_idx = -1

        # 벡터 크기 = 학습 데이터 벡터 크기 + 에이전트 상태 크기 ->  학습할 최종 데이터
        self.num_features = self.agent.STATE_DIM
        if self.training_data is not None:
            self.num_features += self.training_data.shape[1]

        # 신경망 설정
        self.net = net
        self.num_steps = num_steps
        self.lr = lr
        self.value_network = value_network
        self.policy_network = policy_network
        self.reuse_models = reuse_models
        # 가시화 모듈
        self.visualizer = Visualizer()

        # 메모리 - 이 데이터로 신경망 학습
        self.memory_sample = []
        self.memory_action = []
        self.memory_reward = []
        self.memory_penalty = []
        self.memory_value = []
        self.memory_policy = []
        self.memory_pv = []
        self.memory_num_stocks = []
        self.memory_exp_idx = []
        self.memory_learning_idx = []
        # 에포크 관련 정보
        self.loss = 0.
        self.itr_cnt = 0
        self.exploration_cnt = 0
        self.batch_size = 0
        self.learning_cnt = 0
        # 로그 등 출력 경로
        self.output_path = output_path
        # 모델 위치(모델 재사용시 사용)
        self.model_path = ''

    " 가치 신경망 생성"
    def init_value_network(self, shared_network=None, activation='relu', loss='mse', value_network_path=''):
        self.model_path = value_network_path

        if self.net == 'dnn': # DNN 신경망 여기서 생성
            self.value_network = DNN(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, shared_network=shared_network,
                activation=activation, loss=loss)

        if self.reuse_models and os.path.exists(self.model_path):
            self.value_network.load_model(model_path=self.model_path)


    " 정책 신경망 생성 - 추후 사용시 위처럼 약간 변형"
    def init_policy_network(self, shared_network=None,
                            activation='relu', loss='binary_crossentropy'):
        if self.reuse_models and os.path.exists(self.policy_network_path):
            self.policy_network.load_model(
                model_path=self.policy_network_path)

        elif self.net == 'dnn': # DNN 신경망 여기서 생성
            self.policy_network = DNN(
                input_dim=self.num_features,
                output_dim=self.agent.NUM_ACTIONS,
                lr=self.lr, shared_network=shared_network,
                activation=activation, loss=loss)

    def reset(self):
        self.sample = None
        self.training_data_idx = -1
        # 환경 초기화
        self.environment.reset()
        # 에이전트 초기화
        self.agent.reset()
        # 가시화 초기화
        self.visualizer.clear([0, len(self.chart_data)])
        # 메모리 초기화
        self.memory_sample = []
        self.memory_action = []
        self.memory_reward = []
        self.memory_penalty = []
        self.memory_value = []
        self.memory_policy = []
        self.memory_pv = []
        self.memory_num_stocks = []
        self.memory_exp_idx = []
        self.memory_learning_idx = []
        # 에포크 관련 정보 초기화
        self.loss = 0.
        self.itr_cnt = 0
        self.exploration_cnt = 0
        self.batch_size = 0
        self.learning_cnt = 0

    " 환경 객체에서 샘플을 획득 - 학습데이터에서 하나 생성"
    def build_sample(self):
        self.environment.observe()
        if len(self.training_data) > self.training_data_idx + 1:
            self.training_data_idx += 1

            # 26개의 값들로 구성
            self.sample = self.training_data.iloc[self.training_data_idx].tolist()

            # 샘플에 상태값 2개추가
            self.sample.extend(self.agent.get_states())
            return self.sample
        return None

    " delayed_reward는 사용안함"
    " 배치 학습 데이터 생성 - 버추얼 함수"
    @abc.abstractmethod
    def get_batch(self, batch_size, discount_factor):
        pass

    " 신경망 학습 함수 - get_batch 함수 호출"
    def update_networks(self, batch_size, discount_factor):
        # 배치 학습 데이터 생성
        x, y_value, y_policy = self.get_batch(batch_size=batch_size, discount_factor=discount_factor)
        if len(x) > 0:
            loss = 0
            if y_value is not None:
                # 가치 신경망 갱신
                loss += self.value_network.train_on_batch(x, y_value)
            if y_policy is not None:
                # 정책 신경망 갱신
                loss += self.policy_network.train_on_batch(x, y_policy)
            return loss
        return None

    " 신경망 학습 요청 함수 - update_networks 사용"
    def fit(self, discount_factor, full=False): # 에포크 종료되면 True 로 전체데이터 학습
        batch_size = len(self.memory_action) if full else self.batch_size

        # 배치 학습 데이터 생성 및 신경망 갱신
        if batch_size > 0:
            _loss = self.update_networks(batch_size, discount_factor)
            if _loss is not None:
                self.loss += abs(_loss)
                self.learning_cnt += 1
                self.memory_learning_idx.append(self.training_data_idx)
            self.batch_size = 0

    " 에포크 정보 가시화 함수"
    def visualize(self, epoch_str, num_epoches, epsilon):
        self.memory_action = [Agent.ACTION_HOLD] * (self.num_steps - 1) + self.memory_action
        self.memory_num_stocks = [0] * (self.num_steps - 1) \
                                 + self.memory_num_stocks
        if self.value_network is not None:
            self.memory_value = [np.array([np.nan] \
                                          * len(Agent.ACTIONS))] * (self.num_steps - 1) \
                                + self.memory_value
        if self.policy_network is not None:
            self.memory_policy = [np.array([np.nan] \
                                           * len(Agent.ACTIONS))] * (self.num_steps - 1) \
                                 + self.memory_policy
        self.memory_pv = [self.agent.initial_balance] * (self.num_steps - 1) + self.memory_pv
        self.visualizer.plot(
            epoch_str=epoch_str, num_epoches=num_epoches,
            epsilon=epsilon, action_list=Agent.ACTIONS,
            actions=self.memory_action,
            num_stocks=self.memory_num_stocks,
            outvals_value=self.memory_value,
            outvals_policy=self.memory_policy,
            exps=self.memory_exp_idx,
            learning_idxes=self.memory_learning_idx,
            initial_balance=self.agent.initial_balance,
            pvs=self.memory_pv,
        )
        self.visualizer.save(os.path.join(
            self.epoch_summary_dir,
            'epoch_summary_{}.png'.format(epoch_str))
        )

    " 강화학습 수행"
    def run(self, num_epoches=100, balance=10000000,
            discount_factor=0.95, start_epsilon=0.5, learning=False): # 디폴트가 learning 이라 main 에서따로안쳐도 되긴함
        """
        :param learning: True: 학습, False: 투자 시뮬레이션
        """
        info = "[{code}] RL:{rl} Net:{net} LR:{lr} DF:{discount_factor}".format(
            code=self.stock_code, rl=self.rl_method, net=self.net,
            lr=self.lr, discount_factor=discount_factor
        )
        with self.lock:
            logging.info(info)

        # 시작 시간
        time_start = time.time()

        " 가시화 준비"
        # 차트 데이터는 변하지 않으므로 미리 가시화
        self.visualizer.prepare(self.environment.chart_data, info) # 봉차트만 먼저

        # 가시화 결과 저장할 폴더 준비
        self.epoch_summary_dir = os.path.join(self.output_path, 'epoch_summary_{}'.format(
                self.stock_code))
        if not os.path.isdir(self.epoch_summary_dir): # 폴더가 없으면 만들고
            os.makedirs(self.epoch_summary_dir)
        else: # 폴더가 있으면 지우고 다시쓰기
            for f in os.listdir(self.epoch_summary_dir):
                os.remove(os.path.join(self.epoch_summary_dir, f))

        # 에이전트 초기 자본금 설정
        self.agent.set_balance(balance)

        # 학습에 대한 정보 초기화
        max_portfolio_value = 0
        epoch_win_cnt = 0

        " 학습 반복"
        for epoch in range(num_epoches):
            " 초기화 및 전처리"
            time_start_epoch = time.time()

            # step 샘플을 만들기 위한 큐
            q_sample = collections.deque(maxlen=self.num_steps)

            # 환경, 에이전트, 신경망, 가시화, 메모리 초기화
            self.reset()

            # 학습을 진행할 수록 탐험 비율 감소
            if learning:
                epsilon = start_epsilon * (1. - float(epoch) / (num_epoches - 1))
                self.agent.reset_exploration()
            else:
                epsilon = start_epsilon

            " 하나의 에포크 실행 시작"
            while True:
                # 샘플 생성
                next_sample = self.build_sample()
                if next_sample is None:
                    break

                # num_steps만큼 샘플 저장 - 다 찰때까지 continue
                q_sample.append(next_sample)
                if len(q_sample) < self.num_steps:
                    continue

                # 가치, 정책 신경망 예측 - predict 함수로 사용
                pred_value = None
                pred_policy = None
                if self.value_network is not None:
                    pred_value = self.value_network.predict(list(q_sample))
                if self.policy_network is not None:
                    pred_policy = self.policy_network.predict(list(q_sample))

                # 신경망 또는 탐험에 의한 행동 결정 - decide_action 함수 사용
                action, exploration = self.agent.decide_action(pred_value, pred_policy, epsilon)

                # 결정한 행동을 수행하고 즉시 보상과 지연 보상 획득 - act 함수 사용
                immediate_reward, buy_penalty_reward = self.agent.act(action)

                # 행동 및 행동에 대한 결과를 저장
                self.memory_sample.append(list(q_sample))
                self.memory_action.append(action)
                self.memory_reward.append(immediate_reward)
                self.memory_penalty.append(buy_penalty_reward)
                if self.value_network is not None:
                    self.memory_value.append(pred_value)
                if self.policy_network is not None:
                    self.memory_policy.append(pred_policy)
                self.memory_pv.append(self.agent.portfolio_value)
                self.memory_num_stocks.append(self.agent.num_stocks)
                if exploration:
                    self.memory_exp_idx.append(self.training_data_idx)

                # 반복에 대한 정보 갱신
                self.batch_size += 1
                self.itr_cnt += 1
                self.exploration_cnt += 1 if exploration else 0

            # 에포크 종료 후 학습
            if learning:
                self.fit(discount_factor, full=True) # 지연보상, 할인율

            " 가시화 파트"
            # 에포크 관련 정보 로그 기록
            num_epoches_digit = len(str(num_epoches))
            epoch_str = str(epoch + 1).rjust(num_epoches_digit, '0')
            time_end_epoch = time.time()
            elapsed_time_epoch = time_end_epoch - time_start_epoch
            if self.learning_cnt > 0:
                self.loss /= self.learning_cnt
            logging.info("[{}][Epoch {}/{}] Epsilon:{:.4f} "
                         "#Expl.:{}/{} #Buy_10:{} #Buy_20:{} #Buy_30:{}"
                         " #Buy_40:{} #Buy_50:{} #Sell:{} #Hold:{} "
                         "#Stocks:{} PV:{:,.0f} "
                         "LC:{} Loss:{:.6f} ET:{:.4f}".format(
                self.stock_code, epoch_str, num_epoches, epsilon,
                self.exploration_cnt, self.itr_cnt,
                self.agent.num_buy_10, self.agent.num_buy_20,
                self.agent.num_buy_30, self.agent.num_buy_40,
                self.agent.num_buy_50, self.agent.num_sell,
                self.agent.num_hold, self.agent.num_stocks,
                self.agent.portfolio_value, self.learning_cnt,
                self.loss, elapsed_time_epoch))

            # 에포크 관련 정보 가시화
            self.visualize(epoch_str, num_epoches, epsilon)

            # 학습 관련 정보 갱신
            max_portfolio_value = max(
                max_portfolio_value, self.agent.portfolio_value)
            if self.agent.portfolio_value > self.agent.initial_balance:
                epoch_win_cnt += 1

        " 학습 반복 끝"
        # 종료 시간
        time_end = time.time()
        elapsed_time = time_end - time_start

        # 학습 관련 정보 로그 기록
        with self.lock:
            logging.info("[{code}] Elapsed Time:{elapsed_time:.4f} "
                         "Max PV:{max_pv:,.0f} #Win:{cnt_win}".format(
                code=self.stock_code, elapsed_time=elapsed_time,
                max_pv=max_portfolio_value, cnt_win=epoch_win_cnt))

    def save_models(self):
        if self.value_network is not None and self.value_network_path is not None:
            self.value_network.save_model(self.value_network_path)
        if self.policy_network is not None and self.policy_network_path is not None:
            self.policy_network.save_model(self.policy_network_path)

    def save_last_action(self, code_name):
        output_path = os.path.join(settings.BASE_DIR, 'last_action/{}'.format(code_name))
        if not os.path.isdir(output_path):
            os.makedirs(output_path)

        actions = ['BUY_ten_per', 'BUY_two_per', 'BUY_thr_per', 'BUY_fou_per', 'BUY_fiv_per', 'ACTION_SELL',
                   'ACTION_HOLD']
        file = open(os.path.join(output_path, 'action.txt'), 'wt')
        file.write(actions[self.memory_action[-1]])
        file.close()


class DQNLearner(ReinforcementLearner):
    def __init__(self, *args, value_network_path=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.value_network_path = value_network_path
        self.init_value_network(value_network_path=self.value_network_path)

    def get_batch(self, batch_size, discount_factor):
        memory = zip( # 원본 변경 안함
            reversed(self.memory_sample[-batch_size:]),
            reversed(self.memory_action[-batch_size:]),
            reversed(self.memory_value[-batch_size:]),
            reversed(self.memory_reward[-batch_size:]),
            reversed(self.memory_penalty[-batch_size:])
        )
        x = np.zeros((batch_size, self.num_steps, self.num_features))
        y_value = np.zeros((batch_size, self.agent.NUM_ACTIONS)) # 신경망출력 행동저장

        value_max_next = 0
        for i, (sample, action, value, reward, penalty) in enumerate(memory):
            x[i] = sample
            y_value[i] = value # 상태 가치함수
            r = reward + penalty
            " 현재 reward = (최종 - 현재 + 다음 - 현재) 에서 (매도기준 리워드 - 패널티)"
            y_value[i, action] = r + discount_factor * value_max_next # 행동 가치함수
            value_max_next = value.max()
        return x, y_value, None
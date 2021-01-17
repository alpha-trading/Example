"""
1. 입력층과 1번째 레이어랑 노드수 같을 필요없음
2. 출력층은 행동의 가지수만큼 - 6
3. shared_network : 신경망의 상단부로, A2C 에서는 가치, 정책신경망이 초반에 공유함
4. 함수형 API 이니 save_model 함수로 사용하기
5. 구조 유지하면서 일부분만 수정하기

1. 입력 - 출력 - 히든층 신경망다시만들기
2. 저장 로드 - 모델로(문제될시 변경)
"""
import os
import threading
import numpy as np
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, LSTM, Conv2D, \
    BatchNormalization, Dropout, MaxPooling2D, Flatten
from tensorflow.keras.optimizers import SGD
from tensorflow import keras
import tensorflow as tf

class Network:
    lock = threading.Lock() # A3C 용으로 사용

    def __init__(self, input_dim=0, output_dim=0, lr=0.001,
                shared_network=None, activation='sigmoid', loss='mse'):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.lr = lr
        self.shared_network = shared_network
        self.activation = activation
        self.loss = loss
        self.model = None

    " predict, train 함수는 keras.Model 함수에서 사용"
    def predict(self, sample): # 여러샘플 한꺼번에 받아서 신경망의 출력을 반환
        with self.lock:
            return self.model.predict(sample).flatten()

    def train_on_batch(self, x, y):
        loss = 0.
        with self.lock:
            loss = self.model.train_on_batch(x, y)
        return loss

    def save_model(self, model_path): # 폴더생성후, 그위치에 저장
        if model_path is not None and self.model is not None:
            self.model.save_weights(model_path, overwrite=True)

    def load_model(self, model_path):
        if model_path is not None:
            self.model.load_weights(model_path)

    @classmethod
    def get_shared_network(cls, net='dnn', num_steps=1, input_dim=0): # 신경망을 불러오는 함수
        if net == 'dnn':
            return DNN.get_network_head(Input((input_dim,)))
        """elif net == 'lstm':
            return LSTMNetwork.get_network_head(Input((num_steps, input_dim)))
        elif net == 'cnn':
            return CNN.get_network_head(Input((1, num_steps, input_dim)))"""

class DNN(Network):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        inp = None # 5개씩 며칠 -> 1차원배열로 받기(데이터순서 고려x)
        output = None

        if self.shared_network is None: # 모델이 없으면 get 으로 만들어서
            inp = Input((self.input_dim,))
            output = self.get_network_head(inp).output

        else: # 공유 신경망이 존재하면 있던거에다가 대입
            inp = self.shared_network.input
            output = self.shared_network.output

        output = Dense(self.output_dim, activation=self.activation, kernel_initializer='he_uniform')(output)
        self.model = Model(inp, output)
        self.model.compile(optimizer=SGD(lr=self.lr, momentum=0.9, nesterov=True), loss=self.loss)

    @staticmethod
    def get_network_head(inp): # 공유 신경망 생성파트(있으면 사용안하고 가져오기) - 함수형 api
        batch1 = keras.layers.BatchNormalization()(inp)
        hidden1 = keras.layers.Dense(300, activation="relu", kernel_initializer="he_uniform")(batch1)
        drop1 = Dropout(0.1)(hidden1)

        batch2 = keras.layers.BatchNormalization()(drop1)
        hidden2 = keras.layers.Dense(150, activation="relu", kernel_initializer="he_uniform")(batch2)
        drop2 = Dropout(0.1)(hidden2)

        batch3 = keras.layers.BatchNormalization()(drop2)
        hidden3 = keras.layers.Dense(100, activation="relu", kernel_initializer="he_uniform")(batch3)
        drop3 = Dropout(0.1)(hidden3)

        batch4 = keras.layers.BatchNormalization()(drop3)
        hidden4 = keras.layers.Dense(50, activation="relu", kernel_initializer="he_uniform")(batch4)
        drop4 = Dropout(0.1)(hidden4)

        batch5 = keras.layers.BatchNormalization()(drop4)
        hidden5 = keras.layers.Dense(25, activation="relu", kernel_initializer="he_uniform")(batch5)
        drop5 = Dropout(0.1)(hidden5)

        batch6 = keras.layers.BatchNormalization()(drop5)
        output = keras.layers.Dense(14, activation="relu", kernel_initializer="he_uniform")(batch6)

        return Model(inp, output)

    " 두 함수는 입력 sample 차원만 변형하고 부모클래스 그대로 사용"
    def train_on_batch(self, x, y):
        x = np.array(x).reshape((-1, self.input_dim))
        " -1은 전체행을뜻하고, 뒤의 열원소에 맞게 변형 - 12개원소에서 (-1, 2) = 6열, (-1. 3) = 4열"

        return super().train_on_batch(x, y) # 부모 클래스 함수 사용

    def predict(self, sample):
        sample = np.array(sample).reshape((1, self.input_dim))
        " 1차원 배열의 입력을, 1행짜리 2차원 배열로 바꾸기 - 배열로 입력값을 구성해야되서 2차원 배열로"

        return super().predict(sample)

from tensorflow import keras
from utils import sigmoid
from agent import Agent
from environment import Environment
import numpy as np

"""
30분봉기준 하루에 7*2 =14개씩나옴, 10개면 2주 -> 각각 140개씩 데이터 5종류 -> 700개 뉴런(5개분할)
inputs에 넣을데이터 - 시가, 고가, 저가, 현재가, 거래량, 5개만사용해보기

데이터를 environment 이용해서 긁어오기 -> 신경망에 넣어서 학습하기 -> 결과값 이용해서 추론하기
"""

class DQN():
    def __init__(self, lr=0.001, activation='relu', loss='mse',
                 optimizer='SGD(lr=0.01, momentum=0.9, nesterov=True)'):
        self.lr = lr
        self.activation = activation
        self.loss = loss
        self.optimizer = optimizer

        # 생성자에서 모델 생성
        input_start_price = keras.layers.Input(shape=[140], name="start_price")
        input_high_price = keras.layers.Input(shape=[140], name="high_price")
        input_low_price = keras.layers.Input(shape=[140], name="low_price")
        input_current_price = keras.layers.Input(shape=[140], name="current_price")
        input_volume = keras.layers.Input(shape=[140], name="volume_price")
        concat = keras.layers.concatenate([input_start_price, input_high_price, input_low_price,
                                           input_current_price, input_volume])

        batch1 = keras.layers.BatchNormalization()(concat)
        hidden1 = keras.layers.Dense(1000, activation="relu", kernel_initializer="he_uniform")(batch1)
        batch2 = keras.layers.BatchNormalization()(hidden1)
        hidden2 = keras.layers.Dense(750, activation="relu", kernel_initializer="he_uniform")(batch2)
        batch3 = keras.layers.BatchNormalization()(hidden2)
        hidden3 = keras.layers.Dense(500, activation="relu", kernel_initializer="he_uniform")(batch3)
        batch4 = keras.layers.BatchNormalization()(hidden3)
        hidden4 = keras.layers.Dense(250, activation="relu", kernel_initializer="he_uniform")(batch4)
        batch5 = keras.layers.BatchNormalization()(hidden4)
        hidden5 = keras.layers.Dense(125, activation="relu", kernel_initializer="he_uniform")(batch5)
        batch6 = keras.layers.BatchNormalization()(hidden5)
        hidden6 = keras.layers.Dense(64, activation="relu", kernel_initializer="he_uniform")(batch6)
        batch7 = keras.layers.BatchNormalization()(hidden6)
        hidden7 = keras.layers.Dense(32, activation="relu", kernel_initializer="he_uniform")(batch7)
        batch8 = keras.layers.BatchNormalization()(hidden7)
        _output = keras.layers.Dense(1)(batch8)

        self.model = keras.Model(inputs=[input_start_price, input_high_price, input_low_price,
                                           input_current_price, input_volume], outputs=[_output])

    def set_compile(self, _loss="mse", _optimizer="SGD(lr=0.01, momentum=0.9, nesterov=True)",
                    _metrics=['accuracy']):
        self.model.compile(loss=_loss, optimizer=_optimizer, metrics=_metrics)

    def set_fit(self, x, y, _epochs, _validation_data, _callbacks):
        self.model.fit(x, y, epochs=_epochs, validation_data=_validation_data, callbacks=_callbacks)

    def set_evaluate(self, x, y, _batch_size=1):
        self.model.evaluate(x, y, batch_size=_batch_size)

    def set_predcit(self, _inputs):
        pass

    def save_model(self):
        pass

    def load_model(self, model_name):
        pass
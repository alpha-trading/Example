"""
학습할 환경조성, 종가위치는 추후에 csv 파일 보고 수정
"""

class Environment:
    CURRENT_PRICE = 4 # 종가의 위치(추후에 csv파일 생각해서 변경)
    START_PRICE = 5
    HIGH_PRICE = 3
    LOW_PRICE = 2
    VOLUME = 6

    def __init__(self, chart_data=None):
        self.chart_data = chart_data
        self.observation = None
        self.idx = -1

    def reset(self):
        self.observation = None
        self.idx = -1

    def observe(self):
        if len(self.chart_data) > self.idx + 1: # 존재하면
            self.idx += 1
            self.observation = self.chart_data.iloc[self.idx]
            # 관찰값 반환, iloc이면 인덱스가아니라 행번호로 반환
            return self.observation
        return None

    def get_closed_price(self):
        if self.observation is not None:
            return self.observation[self.CURRENT_PRICE] # 차트의 행데이터이니 가격만가져오고, 추후에 다른값도 변경
        return None

    def get_start_price(self):
        if self.observation is not None:
            return self.observation[self.START_PRICE] # 차트의 행데이터이니 가격만가져오고, 추후에 다른값도 변경
        return None

    def get_low_price(self):
        if self.observation is not None:
            return self.observation[self.LOW_PRICE] # 차트의 행데이터이니 가격만가져오고, 추후에 다른값도 변경
        return None

    def get_high_price(self):
        if self.observation is not None:
            return self.observation[self.HIGH_PRICE] # 차트의 행데이터이니 가격만가져오고, 추후에 다른값도 변경
        return None

    def get_volume(self):
        if self.observation is not None:
            return self.observation[self.VOLUME] # 차트의 행데이터이니 가격만가져오고, 추후에 다른값도 변경
        return None

    def set_chart_data(self, chart_data):
        self.chart_data = chart_data
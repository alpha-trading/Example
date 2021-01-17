import pandas as pd
import numpy as np

" 실시간 데이터는 종가 = 현재가"
" date 지우고 학습 추후에 문제될시 추가"
COLUMNS_CHART_DATA = ['open', 'high', 'low', 'close', 'volume']

COLUMNS_TRAINING_DATA_V1 = [
    'open_lastclose_ratio', 'high_close_ratio', 'low_close_ratio',
    'close_lastclose_ratio', 'volume_lastvolume_ratio',
    'close_ma5_ratio', 'volume_ma5_ratio',
    'close_ma10_ratio', 'volume_ma10_ratio',
    'close_ma20_ratio', 'volume_ma20_ratio',
    'close_ma60_ratio', 'volume_ma60_ratio',
    'close_ma120_ratio', 'volume_ma120_ratio',
    'RSI_10', 'RSI_14', 'RSI_25'
]


def preprocess(data, ver='v1'):
    windows = [5, 10, 20, 60, 120]
    for window in windows:
        # pandas 의 rolling 함수는 묶어서 계산가능
        data['close_ma{}'.format(window)] = data['close'].rolling(window).mean()
        data['volume_ma{}'.format(window)] = data['volume'].rolling(window).mean()
        data['close_ma%d_ratio' % window] = (data['close'] - data['close_ma%d' % window]) \
            / data['close_ma%d' % window]
        data['volume_ma%d_ratio' % window] = (data['volume'] - data['volume_ma%d' % window]) \
            / data['volume_ma%d' % window]

    # pandas 의 loc[행, 열] 로 가져올수 있음 + 행끼리 계산하니 for 문 필요없음
    data['open_lastclose_ratio'] = np.zeros(len(data))
    data.loc[1:, 'open_lastclose_ratio'] = (data['open'][1:].values - data['close'][:-1].values) \
        / data['close'][:-1].values

    data['high_close_ratio'] = (data['high'].values - data['close'].values) \
        / data['close'].values

    data['low_close_ratio'] = (data['low'].values - data['close'].values) \
        / data['close'].values

    data['close_lastclose_ratio'] = np.zeros(len(data))
    data.loc[1:, 'close_lastclose_ratio'] = (data['close'][1:].values - data['close'][:-1].values) \
        / data['close'][:-1].values

    data['volume_lastvolume_ratio'] = np.zeros(len(data))
    data.loc[1:, 'volume_lastvolume_ratio'] = (data['volume'][1:].values - data['volume'][:-1].values) \
        / data['volume'][:-1].replace(to_replace=0, method='ffill').replace(to_replace=0, method='bfill').values

    " RSI(10) 구현"
    data['RSI'] = np.zeros(len(data))
    data['U'] = np.where(data.diff(1)['close'] > 0, data.diff(1)['close'], 0)
    data['D'] = np.where(data.diff(1)['close'] < 0, data.diff(1)['close']*(-1), 0)

    data['AU_10'] = data['U'].rolling(10).mean()
    data['DU_10'] = data['D'].rolling(10).mean()
    data['AU_14'] = data['U'].rolling(14).mean()
    data['DU_14'] = data['D'].rolling(14).mean()
    data['AU_25'] = data['U'].rolling(25).mean()
    data['DU_25'] = data['D'].rolling(25).mean()

    data['RSI_10'] = data['AU_10'] / (data['AU_10'] + data['DU_10']) * 100
    data['RSI_14'] = data['AU_14'] / (data['AU_14'] + data['DU_14']) * 100
    data['RSI_25'] = data['AU_25'] / (data['AU_25'] + data['DU_25']) * 100

    return data


def load_data(fpath, ver='v1'):
    """
    :param fpath: 파일위치
    :param ver: 디폴트 1로
    :return: 데이터 항상 다읽어올거니 date 안씀
    """
    header = None if ver == 'v1' else 0
    data = pd.read_csv(fpath, thousands=',', header=header)

    if ver == 'v1':
        data.columns = ['open', 'high', 'low', 'close', 'volume']

    # 데이터 전처리
    data = preprocess(data)

    # 차트 데이터 분리
    chart_data = data[COLUMNS_CHART_DATA]

    # 학습 데이터 분리
    training_data = None
    if ver == 'v1':
        training_data = data[COLUMNS_TRAINING_DATA_V1]
    else:
        raise Exception('Invalid version.')
    
    return chart_data, training_data

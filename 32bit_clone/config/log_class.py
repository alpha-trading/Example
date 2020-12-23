import logging.config
from datetime import datetime

class Logging():
    def __init__(self, config_path='config/logging.conf', log_path = 'log'):
        self.config_path = config_path
        self.log_path = log_path

        logging.config.fileConfig(self.config_path) # conf 파일의 경로를 추가
        self.logger = logging.getLogger('Kiwoom') # 커스텀 로그를 구분하기위함 '키'값을 매개변수로
        self.Kiwoom_log()

    # 로그설정
    def kiwoom_log(self):
        fh = logging.FileHandler(self.log_path + '/{:%Y-%m-%d}.log'.format(datetime.now()), encoding="utf-8") # 로그파일 생성
        formatter = logging.Formatter(
            '[%(asctime)s] I %(filename)s | %(name)s-%(funcName)s-%(lineno)04d I %(levelname)-8s > %(message)s')

        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
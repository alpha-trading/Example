from slacker import Slacker

class Slack():
    def __init__(self):
        self.token = 'xapp-1-A01HQN2Q3ED-1596285858276-1c8e353bd0f02abfd52f01de2cdcaadf7ff13fd9d89051fdd71424e2951b0bcc'

    def notification(self, pretext=None, title=None, fallback=None, text=None):
        attachments_dict = dict() # 메세지와 관련된 변수를 담는곳
        attachments_dict['pretext'] = pretext #test1 - 메세지 요약본
        attachments_dict['title'] = title #test2 - 제목
        attachments_dict['fallback'] = fallback #test3 - 미리보기창 내용
        attachments_dict['text'] = text #test4 - 내용

        attachments = [attachments_dict] # 슬랙으로 딕셔너리 보낼려면 리스트로 변경해서 보내야함

        slack = Slacker(self.token) # 슬랙 인스턴스화
        slack.chat.post_message(channel='#Alpha_Trading', text=None, attachments=attachments, as_user=None)

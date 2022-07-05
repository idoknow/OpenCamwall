import abc


class Message(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def fetch(self, message_id=0, target_type='person', target=0, content='', status='等待'):
        """获取一个或多个消息
        :except: 获取失败
        :return: 倒序 [(id,type,target,content,status)]
        """
        pass

    @abc.abstractmethod
    def update_status(self, message_id, new_status):
        """更新一个消息的状态
        :except: 更新失败
        """
        pass

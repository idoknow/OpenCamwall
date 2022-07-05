import abc


class Account(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def register(self, openid, qq):
        """通过openid和QQ号注册用户
        :except: 绑定失败
        :return: 记录id
        """
        pass

    @abc.abstractmethod
    def unbind(self, qq):
        """解绑某个QQ号
        :except: 解绑失败
        """
        pass

    @abc.abstractmethod
    def find(self, account_id=0, openid='', qq=0):
        """通过openid或qq或account_id查询一个或多个绑定账户记录
        :except: 查询失败
        :return: [(account_id,timestamp,openid,qq)]
        """
        pass

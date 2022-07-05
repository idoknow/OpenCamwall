import abc


class Constant(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def update(self, key, value):
        """更新常量
        :except: 更新失败
        """
        pass

    @abc.abstractmethod
    def fetch(self, key):
        """获取常量值
        :except: 获取失败
        :return: 常量
        """
        pass

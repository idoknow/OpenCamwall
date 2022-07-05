import abc


class Service(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def insert(self, name, description, order, page, color, enable, external):
        """新增服务
        :param name: 服务名称
        :param description: 服务描述
        :param order: 服务排序
        :param page: 服务页面
        :param color: 服务颜色
        :param enable: 服务是否启用
        :param external: 服务外部链接
        :except: 新增失败
        """
        pass

    @abc.abstractmethod
    def fetch(self, name=''):
        """获取服务列表
        :param name: 服务名称
        :except: 获取失败
        :return: 列表
        """
        pass

    @abc.abstractmethod
    def set_enable(self, service_id, enable):
        """设置服务是否启用
        :param service_id: 服务id
        :param enable: 服务是否启用
        :except: 设置失败
        """
        pass

    @abc.abstractmethod
    def delete(self, service_id):
        """删除服务
        :param service_id: 服务id
        :except: 删除失败
        """
        pass

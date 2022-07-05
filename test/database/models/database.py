import abc


class Database(metaclass=abc.ABCMeta):
    account = None
    banlist = None
    constant = None
    message = None
    post = None
    service = None

    database_context = None

    def __init__(self, database_context=None):
        if database_context is None:
            database_context = {}
        self.database_context = database_context
        self.connect()

    @abc.abstractmethod
    def connect(self):
        """连接数据库"""
        pass

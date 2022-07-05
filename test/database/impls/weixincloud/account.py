import sys

sys.path.append("..")
from test.database.models import account


class WCAccount(account):
    def register(self, openid, qq):
        pass

    def unbind(self, qq):
        pass

    def find(self, account_id=0, openid='', qq=0):
        pass

    def ban_account(self, openid, expire, reason):
        pass

import pkg.chat.manager
import pkg.database.database

from mirai import At, AtAll, GroupMessage, MessageEvent, Mirai, Plain, StrangerMessage, WebSocketAdapter, FriendMessage, \
    Image


def login_via_qrcode_callback(path):
    chat_inst = pkg.chat.manager.get_inst()
    chat_inst.send_message_to_admins([
        '[bot]请使用账号登录手机QQ后扫码登录QQ空间',
        Image(path=path)
    ])

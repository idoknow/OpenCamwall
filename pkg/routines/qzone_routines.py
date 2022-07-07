import time

import pkg.chat.manager
import pkg.database.database
import pkg.qzone.publisher

from mirai import At, AtAll, GroupMessage, MessageEvent, Mirai, Plain, StrangerMessage, WebSocketAdapter, FriendMessage, \
    Image


def login_via_qrcode_callback(path):
    chat_inst = pkg.chat.manager.get_inst()
    chat_inst.send_message_to_admins([
        '[bot]请使用账号登录手机QQ后扫码登录QQ空间',
        Image(path=path)
    ])


# 发送所有正在等待的posts
def clean_pending_posts(interval_seconds=10):
    db_inst = pkg.database.database.get_inst()
    posts_data = db_inst.pull_posts(status='通过')
    for post in posts_data['posts']:
        # print("正在发送",post)
        pkg.qzone.publisher.get_inst().prepare_post(post)
        time.sleep(interval_seconds)

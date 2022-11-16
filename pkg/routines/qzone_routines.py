import logging
import threading
import time

import pkg.chat.manager
import pkg.database.database
import pkg.qzone.publisher
import pkg.qzone.model
import pkg.routines.post_routines

import pkg.funcmgr.control as funcmgr

from mirai import Image


def qzone_cookie_invalidated_callback():
    chat_bot = pkg.chat.manager.get_inst()
    if chat_bot is not None:
        chat_bot.send_message_to_admins(["[bot]cookie已失效,回复'更新cookie'进行重新登录"])


def login_via_qrcode_callback(path):
    chat_inst = pkg.chat.manager.get_inst()
    if chat_inst is not None:
        chat_inst.send_message_to_admins([
            '[bot]请使用账号登录手机QQ后扫码登录QQ空间',
            Image(path=path)
        ])


mutex = threading.Lock()


# 发表所有正在等待的posts
@funcmgr.function([funcmgr.Functions.ROUTINE_POST_CLEAN_PENDING_POSTS])
def clean_pending_posts(interval_seconds=10):
    try:
        mutex.acquire()
        db_inst = pkg.database.database.get_inst()
        posts_data = db_inst.pull_posts(status='通过')

        if len(posts_data['posts']) > 0:
            # 检查qzone_cookie是否可用
            try:
                res = pkg.qzone.model.get_inst().check_alive()
            except pkg.qzone.model.CookieExpiredException as e:
                chat_inst = pkg.chat.manager.get_inst()
                if chat_inst is not None:
                    chat_inst.send_message_to_admins("[bot]无可用qzone_cookie,请先刷新cookie后重试")
                return

        for post in posts_data['posts']:
            # print("正在发送",post)
            try:
                start_ts = time.time()
                tid = pkg.qzone.publisher.get_inst().prepare_and_publish_post(post)
                # 发表完成
                finish_ts = time.time()
                chat_inst = pkg.chat.manager.get_inst()

                if chat_inst is not None:
                    chat_inst.send_message_to_admin_groups(
                        "[bot]已完成发表:##{} 耗时:{:.2f}s".format(post['id'], finish_ts - start_ts))
                logging.info("已完成发表:##{} 耗时:{:.2f}s".format(post['id'], finish_ts - start_ts))
                pkg.database.database.get_inst().update_post_status(post_id=post['id'], new_status='已发表')

                threading.Thread(target=pkg.routines.post_routines.post_finished,
                                 args=(post['id'], post['qq'], tid)).start()
            except Exception as e:

                chat_inst = pkg.chat.manager.get_inst()
                if chat_inst is not None:
                    chat_inst.send_message_to_admin_groups("##{}发表失败:{}".format(post['id'], e))
                pkg.database.database.get_inst().update_post_status(post_id=post['id'], new_status='失败',
                                                                    review=str(e)[:120])
                logging.exception(e)
            time.sleep(interval_seconds)
    finally:
        mutex.release()

import logging
import threading
import time

import pkg.chat.manager
import pkg.database.database
import pkg.qzone.publisher
import pkg.qzone.model
import pkg.routines.post_routines

from mirai import Image


def login_via_qrcode_callback(path):
    chat_inst = pkg.chat.manager.get_inst()
    chat_inst.send_message_to_admins([
        '[bot]请使用账号登录手机QQ后扫码登录QQ空间',
        Image(path=path)
    ])


mutex = threading.Lock()


# 发表所有正在等待的posts
def clean_pending_posts(interval_seconds=10):
    try:
        mutex.acquire()
        db_inst = pkg.database.database.get_inst()
        posts_data = db_inst.pull_posts(status='通过')

        if len(posts_data['posts'])>0:
            # 检查qzone_token是否可用
            if pkg.qzone.model.get_inst().qzone_token=="" or 'invalidated':
                pkg.chat.manager.get_inst().send_message_to_admins("无可用qzone_token,请先刷新cookie后重试")
                return

        for post in posts_data['posts']:
            # print("正在发送",post)
            try:
                start_ts = time.time()
                tid = pkg.qzone.publisher.get_inst().prepare_post(post)
                # 发表完成
                finish_ts = time.time()
                # pkg.chat.manager.get_inst().send_message_to_admins(
                #     "[bot]已完成发表:##{} 耗时:{:.2f}s".format(post['id'], finish_ts - start_ts))
                logging.info("已完成发表:##{} 耗时:{:.2f}s".format(post['id'], finish_ts - start_ts))
                pkg.database.database.get_inst().update_post_status(post_id=post['id'], new_status='已发表')

                threading.Thread(target=pkg.routines.post_routines.post_finished,
                                 args=(post['id'], post['qq'], tid)).start()
            except Exception as e:
                pkg.chat.manager.get_inst().send_message_to_admins("##{}发表失败:{}".format(post['id'], e))
                pkg.database.database.get_inst().update_post_status(post_id=post['id'], new_status='失败',
                                                                    review=str(e)[:120])
                logging.exception(e)
            time.sleep(interval_seconds)
    finally:
        mutex.release()

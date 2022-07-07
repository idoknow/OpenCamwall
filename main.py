import threading
import time

import config

import pkg.chat.manager
import pkg.database.database
import pkg.webapi.api
import pkg.qzone.login
import pkg.qzone.model
import pkg.qzone.publisher

import pkg.routines.qzone_routines


def qzone_cookie_invalidated_callback():
    chat_bot = pkg.chat.manager.get_inst()
    chat_bot.send_message_to_admins(["[bot]qzone_token刷新失败,cookie可能已经失效,回复'更新cookie'进行重新登录"])


if __name__ == '__main__':

    # 建立数据库对象
    db_mgr = pkg.database.database.MySQLConnection(config.database_context['host'],
                                                   config.database_context['port'],
                                                   config.database_context['user'],
                                                   config.database_context['password'],
                                                   config.database_context['db'])

    # 自动回复机器人
    chat_bot = pkg.chat.manager.ChatBot(config.qq_bot_uin,
                                        config.mirai_http_verify_key,
                                        config.auto_reply_message,
                                        config.qrcode_path,
                                        config.admin_uins,
                                        config.admin_groups, db_mgr)

    # RESTful API
    restful_api = pkg.webapi.api.RESTfulAPI(
        db_mgr,
        port=config.api_port,
        domain=config.api_domain,
        ssl_context=config.api_ssl_context
    )

    # 小程序图片获取
    emotion_publisher=pkg.qzone.publisher.EmotionPublisher(
        app_id=config.mini_program_appid,
        app_secret=config.mini_program_secret
    )

    chat_bot_thread = threading.Thread(target=chat_bot.bot.run, args=(), daemon=True)
    restful_api_thread = threading.Thread(target=restful_api.run_api, args=(), daemon=True)

    chat_bot_thread.start()
    restful_api_thread.start()

    time.sleep(5)

    # 向管理员发送QQ空间登录二维码
    qzone_login = pkg.qzone.login.QzoneLoginManager()
    if config.qzone_cookie=='':
        cookies = qzone_login.login_via_qrcode(
            qrcode_refresh_callback=pkg.routines.qzone_routines.login_via_qrcode_callback)

        cookie_str = ""

        for k in cookies:
            cookie_str += "{}={};".format(k, cookies[k])

        qzone_oper = pkg.qzone.model.QzoneOperator(int(str(cookies['uin']).replace("o", "")),
                                                   cookie_str)
        print(cookie_str)
        chat_bot.send_message_to_admins(["[bot]已成功通过二维码登录QQ空间"])
    else:
        qzone_oper = pkg.qzone.model.QzoneOperator(config.qzone_uin,
                                                   config.qzone_cookie)
        chat_bot.send_message_to_admins(["[bot]已成功使用提供的cookie登录QQ空间"])

    # qzone_oper.publish_emotion("已上线")

    time.sleep(100000)

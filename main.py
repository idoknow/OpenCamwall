import threading
import time

import config

import pkg.chat.manager
import pkg.database.database
import pkg.webapi.api
import pkg.qzone.login
import pkg.qzone.model

import pkg.routines.qzone_routines

if __name__ == '__main__':
    db_mgr = pkg.database.database.MySQLConnection(config.database_context['host'],
                                                   config.database_context['port'],
                                                   config.database_context['user'],
                                                   config.database_context['password'],
                                                   config.database_context['db'])

    chat_bot = pkg.chat.manager.ChatBot(config.qq_bot_uin,
                                        config.mirai_http_verify_key,
                                        config.auto_reply_message,
                                        config.qrcode_path,
                                        config.admin_uins,
                                        config.admin_groups, db_mgr)

    restful_api = pkg.webapi.api.RESTfulAPI(
        db_mgr,
        domain=config.api_domain,
        ssl_context=config.api_ssl_context
    )

    chat_bot_thread = threading.Thread(target=chat_bot.bot.run, args=(), daemon=True)
    restful_api_thread = threading.Thread(target=restful_api.run_api, args=(), daemon=True)

    chat_bot_thread.start()
    restful_api_thread.start()

    time.sleep(5)

    qzone_login = pkg.qzone.login.QzoneLoginManager()
    cookies = qzone_login.login_via_qrcode(
        qrcode_refresh_callback=pkg.routines.qzone_routines.login_via_qrcode_callback)

    cookie_str = ""

    for k in cookies:
        cookie_str += "{}={};".format(k, cookies[k])

    qzone_oper = pkg.qzone.model.QzoneOperator(int(str(cookies['uin']).replace("o", "")),
                                               cookie_str)

    chat_bot.send_message_to_admins(["[bot]已成功登录QQ空间,以上二维码已失效"])
    # qzone_oper.publish_emotion("已上线")

    time.sleep(100000)

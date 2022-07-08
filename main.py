import sys
import threading
import time
import logging

import config
import colorlog

import pkg.chat.manager
import pkg.database.database
import pkg.webapi.api
import pkg.qzone.login
import pkg.qzone.model
import pkg.qzone.publisher

import pkg.routines.qzone_routines

import pkg.audit.recorder.visitors
import pkg.audit.recorder.likers
import pkg.audit.analyzer.analyzer


def qzone_cookie_invalidated_callback():
    chat_bot = pkg.chat.manager.get_inst()
    chat_bot.send_message_to_admins(["[bot]qzone_token刷新失败,cookie可能已经失效,回复'更新cookie'进行重新登录"])


def main():
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
    emotion_publisher = pkg.qzone.publisher.EmotionPublisher(
        env_id=config.cloud_env_id,
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
    if config.qzone_cookie == '':
        cookies = qzone_login.login_via_qrcode(
            qrcode_refresh_callback=pkg.routines.qzone_routines.login_via_qrcode_callback)

        cookie_str = ""

        for k in cookies:
            cookie_str += "{}={};".format(k, cookies[k])

        qzone_oper = pkg.qzone.model.QzoneOperator(int(str(cookies['uin']).replace("o", "")),
                                                   cookie_str,
                                                   cookie_invalidated_callback=qzone_cookie_invalidated_callback)
        print(cookie_str)
        # chat_bot.send_message_to_admins(["[bot]已通过二维码登录QQ空间"])
        logging.info("已通过二维码登录QQ空间")
    else:
        qzone_oper = pkg.qzone.model.QzoneOperator(config.qzone_uin,
                                                   config.qzone_cookie,
                                                   cookie_invalidated_callback=qzone_cookie_invalidated_callback)
        # chat_bot.send_message_to_admins(["[bot]已使用提供的cookie登录QQ空间"])
        logging.info("已使用提供的cookie登录QQ空间")

    # qzone_oper.publish_emotion("已上线")

    # 启动分析程序
    visitor_recorder_thread = threading.Thread(target=pkg.audit.recorder.visitors.initialize, args=(), daemon=True)
    visitor_recorder_thread.start()

    time.sleep(3)

    liker_recorder_thread = threading.Thread(target=pkg.audit.recorder.likers.initialize_liker_recorder, args=(),
                                             daemon=True)
    liker_recorder_thread.start()

    time.sleep(3)

    analyzer_thread = threading.Thread(target=pkg.audit.analyzer.analyzer.initialize, args=(), daemon=True)
    analyzer_thread.start()


log_colors_config = {
    'DEBUG': 'green',  # cyan white
    'INFO': 'white',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

if __name__ == '__main__':
    logging.basicConfig(level=config.logging_level,  # 设置日志输出格式
                        filename='camwall.log',  # log日志输出的文件位置和文件名
                        format="[%(asctime)s.%(msecs)03d] %(filename)s (%(lineno)d) - [%(levelname)s] : %(message)s",
                        # 日志输出的格式
                        # -8表示占位符，让输出左对齐，输出长度都为8位
                        datefmt="%Y-%m-%d %H:%M:%S"  # 时间输出的格式
                        )
    sh = logging.StreamHandler()
    sh.setLevel(config.logging_level)
    sh.setFormatter(colorlog.ColoredFormatter(
        fmt="%(log_color)s[%(asctime)s.%(msecs)03d] %(filename)s (%(lineno)d) - [%(levelname)s] : "
            "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors=log_colors_config
    )
    )
    logging.getLogger().addHandler(sh)

    # logger = logging.getLogger('cw')
    #
    # fh = logging.FileHandler(filename='camwall.log', mode='a', encoding='utf8')
    #
    # fh_formatter = file_formatter = logging.Formatter(
    #     fmt="%(asctime)s - %(name)s - %(levelname)-9s - %(filename)-8s (%(lineno)s) - %(message)s",
    #     datefmt="%Y-%m-%d %H:%M:%S"
    # )
    # fh.setFormatter(fh_formatter)
    # fh.setLevel(config.logging_level)
    #
    # sh = logging.StreamHandler()
    #
    # sh_formatter = colorlog.ColoredFormatter(
    #     fmt="%(asctime)s - %(name)s - %(levelname)-9s - %(filename)-8s (%(lineno)s) - %(message)s",
    #     datefmt="%Y-%m-%d %H:%M:%S",
    #     log_colors={
    #         'DEBUG': 'white',  # cyan white
    #         'INFO': 'red',
    #         'WARNING': 'yellow',
    #         'ERROR': 'red',
    #         'CRITICAL': 'bold_red',
    #     }
    # )
    # sh.setFormatter(sh_formatter)
    # sh.setLevel(config.logging_level)
    #
    # logger.addHandler(fh)
    # logger.addHandler(sh)
    # logger.setLevel(config.logging_level)
    #
    # logger.info("正在执行启动流程...")

    main()

    while True:
        time.sleep(86400)

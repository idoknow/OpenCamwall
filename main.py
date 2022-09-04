import os
import re
import sys
import threading
import time
import logging
from pathlib import Path

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
        app_secret=config.mini_program_secret,
        watermarker=("cache/watermarker.jpg" if Path("cache/watermarker.jpg").exists() else '')
    )

    chat_bot_thread = threading.Thread(target=chat_bot.bot.run, args=(), daemon=True)
    restful_api_thread = threading.Thread(target=restful_api.run_api, args=(), daemon=True)

    chat_bot_thread.start()
    restful_api_thread.start()

    time.sleep(5)

    # 向管理员发送QQ空间登录二维码
    qzone_login = pkg.qzone.login.QzoneLoginManager()
    try:
        if config.qzone_cookie != '':
            qzone_oper = pkg.qzone.model.QzoneOperator(config.qzone_uin,
                                                       config.qzone_cookie,
                                                       cookie_invalidated_callback=qzone_cookie_invalidated_callback)
            # chat_bot.send_message_to_admins(["[bot]已使用提供的cookie登录QQ空间"])
            logging.info("已使用提供的cookie登录QQ空间")
        else:
            raise Exception("没有提供cookie")
    except Exception as e:
        logging.info("使用提供的cookie登录QQ空间失败,尝试使用二维码登录")
        cookies = qzone_login.login_via_qrcode(
            qrcode_refresh_callback=pkg.routines.qzone_routines.login_via_qrcode_callback)

        cookie_str = ""

        for k in cookies:
            cookie_str += "{}={};".format(k, cookies[k])

        qzone_oper = pkg.qzone.model.QzoneOperator(int(str(cookies['uin']).replace("o", "")),
                                                   cookie_str,
                                                   cookie_invalidated_callback=qzone_cookie_invalidated_callback)
        print(cookie_str)
        chat_bot.send_message_to_admins(["[bot]已通过二维码登录QQ空间"])
        logging.info("已通过二维码登录QQ空间")

        # 把cookie写进config.py
        config_file = open('config.py', encoding='utf-8', mode='r+')
        config_str = config_file.read()
        config_str = re.sub(r'qzone_cookie = .*', 'qzone_cookie = \'{}\''.format(cookie_str), config_str)

        config_file.seek(0)
        config_file.write(config_str)
        config_file.close()

    time.sleep(3)
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


def create_dir_not_exist(path):
    if not os.path.exists(path):
        os.mkdir(path)


def init_db():
    # 建立数据库对象
    db_mgr = pkg.database.database.MySQLConnection(config.database_context['host'],
                                                   config.database_context['port'],
                                                   config.database_context['user'],
                                                   config.database_context['password'],
                                                   config.database_context['db'],
                                                   autocommit=False)

    print("账户表...")
    sql = """CREATE TABLE IF NOT EXISTS `accounts` (
      `id` int NOT NULL AUTO_INCREMENT,
      `openid` varchar(64) NOT NULL DEFAULT '',
      `qq` varchar(16) NOT NULL DEFAULT 0,
      `timestamp` bigint DEFAULT NULL,
      `identity` varchar(32) DEFAULT 'user',
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("封禁记录表...")
    sql = """CREATE TABLE IF NOT EXISTS `banlist` (
      `id` bigint NOT NULL AUTO_INCREMENT,
      `openid` varchar(64) NOT NULL,
      `start` bigint NOT NULL DEFAULT 0,
      `expire` bigint NOT NULL DEFAULT 0,
      `reason` varchar(256) NOT NULL,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("运行时常量表...")
    sql = """CREATE TABLE IF NOT EXISTS `constants` (
      `key` varchar(128) NOT NULL,
      `value` varchar(4096) NOT NULL DEFAULT '',
      PRIMARY KEY (`key`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("填充运行时常量表...")
    sql = """insert into `constants`(`key`,`value`) values 
    ('announcement','此字段不为空时,小程序启动时将弹窗提示此字段内容'),
    ('banner','此字段不为空时,小程序将在页面顶部显示此内容'),
    ('rules','["使用json数据的格式来编写每一条投稿规则","小程序将自动为其编号,并显示在投稿入口处"]'),
    ('tags','["标签1","标签2","标签3"]'),
    ('tagstips','小程序上对标签的解释'),
    ('textfield0120','小程序\\'匿名投稿\\'标签的提示文字')"""
    db_mgr.cursor.execute(sql)

    print("说说内容跟踪记录表...")
    sql = """CREATE TABLE IF NOT EXISTS `emotions` (
      `id` bigint NOT NULL AUTO_INCREMENT,
      `pid` int NOT NULL DEFAULT -1,
      `eid` varchar(128) NOT NULL,
      `timestamp` bigint NOT NULL,
      `valid` int NOT NULL DEFAULT 0,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("空间事件表...")
    sql = """CREATE TABLE IF NOT EXISTS `events` (
      `id` bigint NOT NULL AUTO_INCREMENT,
      `type` varchar(64) NOT NULL,
      `timestamp` bigint NOT NULL,
      `json` varchar(1024) NOT NULL DEFAULT '{}',
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("反馈记录表...")
    sql = """CREATE TABLE IF NOT EXISTS `feedback` (
      `id` bigint NOT NULL AUTO_INCREMENT,
      `openid` varchar(128) NOT NULL,
      `content` varchar(1024) NOT NULL,
      `timestamp` bigint DEFAULT NULL,
      `media` text NOT NULL,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("接口日志表...")
    sql = """CREATE TABLE IF NOT EXISTS `logs` (
      `id` bigint NOT NULL AUTO_INCREMENT,
      `timestamp` bigint DEFAULT NULL,
      `location` varchar(128) NOT NULL,
      `account` varchar(128) NOT NULL,
      `operation` varchar(128) NOT NULL,
      `content` varchar(512) NOT NULL,
      `ip` varchar(32) NOT NULL,
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("稿件表...")
    sql = """CREATE TABLE IF NOT EXISTS `posts` (
      `id` int NOT NULL AUTO_INCREMENT,
      `openid` varchar(64) NOT NULL DEFAULT '',
      `qq` varchar(16) NOT NULL DEFAULT 0,
      `timestamp` bigint DEFAULT NULL,
      `text` text NOT NULL,
      `media` text NOT NULL,
      `anonymous` tinyint NOT NULL DEFAULT 0,
      `status` varchar(32) NOT NULL DEFAULT '未审核',
      `review` varchar(128) NOT NULL DEFAULT '无原因',
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("服务列表...")
    sql = """CREATE TABLE IF NOT EXISTS `services` (
      `id` bigint NOT NULL AUTO_INCREMENT,
      `name` varchar(256) DEFAULT NULL,
      `description` varchar(1024) DEFAULT NULL,
      `order` bigint NOT NULL DEFAULT 0,
      `page` varchar(512) DEFAULT NULL,
      `color` varchar(16) DEFAULT '#A7F2FF',
      `enable` tinyint(1) DEFAULT 0,
      `external` varchar(1024) DEFAULT '',
      PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("统计静态数据表...")
    sql = """CREATE TABLE IF NOT EXISTS `static_data` (
      `key` varchar(128) NOT NULL,
      `timestamp` bigint NOT NULL,
      `json` json DEFAULT NULL,
      PRIMARY KEY (`key`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci"""
    db_mgr.cursor.execute(sql)

    print("账户密码表...")
    sql = """create table `uniauth` (
        `id` bigint auto_increment primary key,
        `openid` varchar(128) ,
        `timestamp` bigint,
        `password` varchar(2048) default '',
        `status` varchar(128) default 'valid'
    );"""
    db_mgr.cursor.execute(sql)

    db_mgr.connection.commit()
    print("初始化数据库完成")


if __name__ == '__main__':

    if len(sys.argv) > 1 and sys.argv[1] == 'init_db':
        init_db()
        sys.exit(0)

    create_dir_not_exist('cache')

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
    ))
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

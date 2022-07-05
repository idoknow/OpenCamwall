from pkg.chat.manager import ChatBot
import config

import pkg.database.database

if __name__ == '__main__':
    db_mgr = pkg.database.database.MySQLConnection(config.database_context['host'],
                                                   config.database_context['port'],
                                                   config.database_context['user'],
                                                   config.database_context['password'],
                                                   config.database_context['db'])

    chat_bot = ChatBot(config.qq_bot_uin,
                       config.mirai_http_verify_key,
                       config.auto_reply_message,
                       config.qrcode_path,
                       config.admin_uins,
                       config.admin_groups, db_mgr)

    chat_bot.bot.run()

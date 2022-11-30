import logging
import threading
import re
from pathlib import Path
import pkg.qzone.model
import pkg.qzone.login
import pkg.routines.qzone_routines
import asyncio

from mirai import At, AtAll, GroupMessage, MessageEvent, Mirai, Plain, StrangerMessage, WebSocketAdapter, FriendMessage, \
    Image

import sys

sys.path.append("../")
from pkg.database.database import MySQLConnection

import pkg.funcmgr.control as funcmgr

inst = None

updating = False


def update_cookie_workflow():
    global updating
    if updating:
        return

    updating = True

    try:
        chat_bot = pkg.chat.manager.get_inst()

        # 向管理员发送QQ空间登录二维码
        qzone_login = pkg.qzone.login.QzoneLoginManager()
        cookies = qzone_login.login_via_qrcode(
            qrcode_refresh_callback=pkg.routines.qzone_routines.login_via_qrcode_callback)

        cookie_str = ""

        for k in cookies:
            cookie_str += "{}={};".format(k, cookies[k])

        qzone_oper = pkg.qzone.model.QzoneOperator(int(str(cookies['uin']).replace("o", "")),
                                                   cookie_str, cookie_invalidated_callback=pkg.routines.qzone_routines
                                                   .qzone_cookie_invalidated_callback)

        if chat_bot is not None:
            chat_bot.send_message_to_admins(["[bot]已通过二维码登录QQ空间"])

        logging.info("已通过二维码登录QQ空间")

        # 发送所有正在等待的说说
        temp_thread = threading.Thread(target=pkg.routines.qzone_routines.clean_pending_posts, args=(), daemon=True)
        temp_thread.start()

        # 把cookie写进config.py
        config_file = open('config.py', encoding='utf-8', mode='r+')
        config_str = config_file.read()
        config_str = re.sub(r'qzone_cookie = .*', 'qzone_cookie = \'{}\''.format(cookie_str), config_str)

        config_file.seek(0)
        config_file.write(config_str)
        config_file.close()
    finally:
        updating = False


class ChatBot:
    uin = 0
    mirai_host = ''
    verify_key = ''
    bot = None
    auto_reply_message = ''
    qrcode_path = ''
    admin_uins = []
    admin_groups = []

    db = None

    def __init__(self, uin: int, mirai_host: str, verify_key: str, auto_reply_message: str, qrcode_path: str,
                 admin_uins: set, admin_groups: set, db_mgr: MySQLConnection):
        global inst
        self.uin = uin
        self.mirai_host = mirai_host
        self.verify_key = verify_key
        self.auto_reply_message = auto_reply_message
        self.qrcode_path = qrcode_path
        self.admin_uins = admin_uins
        self.admin_groups = admin_groups

        self.db = db_mgr

        bot = Mirai(
            qq=uin,
            adapter=WebSocketAdapter(
                verify_key=verify_key,
                host=mirai_host,
                port=8080
            )
        )

        @bot.on(FriendMessage)
        async def on_friend_message(event: FriendMessage):
            return await self.on_message(event)

        @bot.on(StrangerMessage)
        async def on_strange_message(event: StrangerMessage):
            return await self.on_message(event)

        @bot.on(GroupMessage)
        async def on_group_message(event: GroupMessage):
            return self.on_group_message(event)

        self.bot = bot

        inst = self

    def send_message_to_admins(self, message_chain):
        for admin in self.admin_uins:
            self.send_message('person', admin, message_chain)

    def send_message_to_admin_groups(self, message_chain):
        for admin_group in self.admin_groups:
            self.send_message('group', admin_group, message_chain)

    @funcmgr.function([funcmgr.Functions.CHAT])
    def send_message(self, target_type, target, message):
        if target_type == 'group':
            send_task = self.bot.send_group_message(target, message)
            asyncio.run(send_task)
        elif target_type == 'person':
            send_task = self.bot.send_friend_message(target, message)
            asyncio.run(send_task)
        else:
            raise Exception('target_type error')

    async def on_message(self, event: MessageEvent):
        logging.info("[QQ消息:{}".format(event.sender.id) + "]:" + str(event.message_chain))
        if event.sender.id == self.uin:
            return
        elif '更新cookie' in str(event.message_chain) and event.sender.id in self.admin_uins:
            update_thread = threading.Thread(target=update_cookie_workflow, daemon=True)
            update_thread.start()
        else:
            openid = re.findall(r'#id{[-_\d\w]{28}}', str(event.message_chain))
            if len(openid) > 0:

                try:
                    self.db.register(
                        openid[0].replace("#id{", "").replace("}", ""),
                        event.sender.id)
                    return await self.bot.send(event, "[bot]" + "绑定成功,请重新进入小程序")
                except Exception as e:
                    return await self.bot.send(event, "[bot]" + "绑定失败:{}".format(str(e)))

            elif re.match('#解绑', str(event.message_chain)):
                try:
                    self.db.unbinding(event.sender.id)
                    return await self.bot.send(event, "[bot]" + "解绑成功")
                except Exception as e:
                    return await self.bot.send(event, "[bot]" + "解绑失败:{}".format(str(e)))
            else:
                message_chain = [
                    self.auto_reply_message,
                    Image(path=str(self.qrcode_path)) if Path(self.qrcode_path).exists() else Plain(""),
                ]
                return await self.bot.send(event, message_chain)

    async def on_group_message(self, event: GroupMessage):

        if event.group.id not in self.admin_groups:
            return
        if At(self.bot.qq) in event.message_chain:
            if len(event.message_chain[Plain]) == 0:
                return await self.bot.send_group_message(event.group.id,
                                                         [Plain(
                                                             "[bot]审核消息格式:\n##id 通过|拒绝:理由\n\n示例:\n##87 通过\n##89 拒绝:重复投稿")])
            plainText = str(event.message_chain[Plain][0]).replace("：", ":")
            # print("Text: "+plainText)
            postid = re.findall(r'##[\d]*', str(event.message_chain))
            if len(postid) == 0:
                return await self.bot.send_group_message(event.group.id,
                                                         [Plain(
                                                             "[bot]审核消息格式:\n##id 通过|拒绝:理由\n\n示例:\n##87 通过\n##89 拒绝:重复投稿")])

            else:
                id = str(postid[0]).replace("##", "")
                # print("id:",id)
                denial = re.findall(r'拒绝:.+', str(plainText))
                # print("denial:",denial)
                approval = re.findall(r'通过', str(plainText))
                # print("approval:",approval)
                recall = re.findall(r'撤回', str(plainText))
                # print("recall:",recall)

                if len(denial) == len(approval) == 0 == len(recall):
                    return await self.bot.send_group_message(event.group.id, [
                        Plain(
                            "[bot]审核消息格式:\n##id 通过|拒绝:理由|撤回:理由\n\n示例:\n##87 通过\n##89 拒绝:重复投稿")])

                elif len(denial) + len(approval) + len(recall) > 1:
                    return await self.bot.send_group_message(event.group.id, [Plain("[bot]要么拒绝要么通过！")])

                else:
                    if len(denial) > 0:
                        try:
                            self.db.update_post_status(id, "拒绝", review=denial[0], old_status="未审核")
                            pending = self.db.pull_posts(status="未审核", capacity=0)

                            msg_chain = [Plain("[bot]已拒绝此稿件")]
                            if pending['table_amount'] > 0:
                                msg_chain.append("(剩余{}条未审核)".format(pending['table_amount']))

                            return await self.bot.send_group_message(event.group.id, msg_chain)
                        except Exception as e:
                            logging.exception(e)
                            return await self.bot.send_group_message(event.group.id,
                                                                     [Plain("[bot]拒绝失败:{}".format(str(e)))])

                    elif len(approval) > 0:
                        try:
                            self.db.update_post_status(id, "通过", old_status="未审核")
                            pending = self.db.pull_posts(status="未审核", capacity=0)

                            msg_chain = [Plain("[bot]已通过此稿件")]
                            if pending['table_amount'] > 0:
                                msg_chain.append("(剩余{}条未审核)".format(pending['table_amount']))

                            return await self.bot.send_group_message(event.group.id, msg_chain)
                        except Exception as e:
                            logging.exception(e)
                            return await self.bot.send_group_message(event.group.id,
                                                                     [Plain("[bot]通过失败:{}".format(str(e)))])

                    elif len(recall) > 0:
                        try:
                            self.db.update_post_status(id, "撤回", review=recall[0])

                            msg_chain = [Plain("[bot]即将撤回此稿件")]
                            return await self.bot.send_group_message(event.group.id, msg_chain)
                        except Exception as e:
                            logging.exception(e)
                            return await self.bot.send_group_message(event.group.id,
                                                                     [Plain("[bot]撤回失败:{}".format(str(e)))])


def get_inst() -> ChatBot:
    global inst
    return inst

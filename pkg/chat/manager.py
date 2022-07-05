from email.quoprimime import quote
from pydoc import plain
import re
import threading
import requests
import mirai
from pathlib import Path
import time
import json
import asyncio

from mirai import At, AtAll, GroupMessage, MessageEvent, Mirai, Plain, StrangerMessage, WebSocketAdapter, FriendMessage, \
    Image

import sys

sys.path.append("../")
from pkg.database.database import MySQLConnection


class ChatBot:
    uin = 0
    verify_key = ''
    bot = None
    auto_reply_message = ''
    qrcode_path = ''
    admin_uins = []
    admin_groups = []

    db = None

    def __init__(self, uin: int, verify_key: str, auto_reply_message: str, qrcode_path: str,
                 admin_uins: set, admin_groups: set, db_mgr: MySQLConnection):
        self.uin = uin
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
                host='localhost',
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

    async def on_message(self, event: MessageEvent):
        print(event.sender.id, event.message_chain, sep=":")
        if event.sender.id == self.uin:
            return
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

            elif re.match('#unbinding', str(event.message_chain)):
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

                if len(denial) == len(approval) == 0:
                    return await self.bot.send_group_message(event.group.id, [
                        Plain("[bot]审核消息格式:\n##id 通过|拒绝:理由\n\n示例:\n##87 通过\n##89 拒绝:重复投稿")])

                elif len(denial) != 0 and len(approval) != 0:
                    return await self.bot.send_group_message(event.group.id, [Plain("[bot]要么拒绝要么通过！")])

                else:
                    if len(denial) > 0:
                        try:
                            self.db.update_post_status(id, "拒绝", review=denial[0], old_status="未审核")
                            return await self.bot.send_group_message(event.group.id, [Plain("[bot]已拒绝此投稿")])
                        except Exception as e:
                            return await self.bot.send_group_message(event.group.id,
                                                                     [Plain("[bot]拒绝失败:{}".format(str(e)))])

                    elif len(approval) > 0:
                        try:
                            self.db.update_post_status(id, "通过", old_status="未审核")
                            return await self.bot.send_group_message(event.group.id, [Plain("[bot]已通过此投稿")])
                        except Exception as e:
                            return await self.bot.send_group_message(event.group.id,
                                                                     [Plain("[bot]通过失败:{}".format(str(e)))])

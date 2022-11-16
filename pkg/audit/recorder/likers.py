# 单条说说点赞量分析
import logging
import re
import threading
import requests
import json
import time

import pkg.database.database
import pkg.audit.recorder.visitors
import pkg.qzone.model

EMOTION_INFO_API = "https://user.qzone.qq.com/proxy/domain/r.qzone.qq.com/cgi-bin/user/qz_opcnt2?_stp={" \
                   "}&unikey=http://user.qzone.qq.com/{}/mood/{}&face=0&fupdate=1 "


class Emotion:
    id = 0
    pid = 0
    eid = ""
    timestamp = 0
    valid = 0

    def __init__(self, id, pid, eid, timestamp, valid) -> None:
        self.id = id
        self.pid = pid
        self.eid = eid
        self.timestamp = timestamp
        self.valid = valid

    def is_valid(self):
        return self.valid == 1

    def schedule(self):
        now = int(time.time())
        for tp in record_time:
            if tp >= now - self.timestamp:
                now = int(time.time())
                # print("schedule:{} next_point:{}".format(tp - (now - self.timestamp), tp))
                time.sleep(tp - (now - self.timestamp))
                if not self.is_valid():  # 已经不可用了，退出
                    break
                go(self.record, args=(tp,))

    def record(self, interval):
        # print("record:eid:{} pid:{}".format(self.eid, self.pid))
        nowmill = int(time.time()) * 1000
        url = EMOTION_INFO_API.format(nowmill, pkg.qzone.model.get_inst().uin, self.eid)
        # print(url)
        resp = requests.get(url)

        respobj = json.loads(resp.text.replace("_Callback(", "")[:-3])

        if respobj["message"] == "succ":

            # 检查newdata是否完整，不完整则结束跟踪，valid设置为0
            crt_newdata = dict(respobj["data"][0]["current"]["newdata"])
            # print(crt_newdata)
            if crt_newdata.__contains__("LIKE") and crt_newdata.__contains__("PRD") and crt_newdata.__contains__(
                    "CS") and crt_newdata.__contains__("ZS"):  # 点赞，浏览，评论，转发
                like_amt = 0
                read_amt = 0
                comment_amt = 0
                forward_amt = 0

                like_amt = crt_newdata["LIKE"]
                read_amt = crt_newdata["PRD"]
                comment_amt = crt_newdata["CS"]
                forward_amt = crt_newdata["ZS"]

                jsonobj = {
                    "pid": self.pid,
                    "eid": self.eid,
                    "interval": interval,
                    "like": like_amt,
                    "read": read_amt,
                    "comment": comment_amt,
                    "forward": forward_amt
                }

                jsontext = json.dumps(jsonobj)

                try:
                    # 存数据库
                    pkg.database.database.get_inst().acquire()
                    try:
                        pkg.database.database.get_inst().ensure_connection()

                        sql = "insert into `events` (`type`,`timestamp`,`json`) values ('{}',{},'{}')".format(
                            pkg.audit.recorder.visitors.TYPE_LIKER_RECORD, int(time.time()), jsontext)
                        logging.info("说说(pid:{}) 时间点{}记录".format(self.pid, interval))
                        pkg.database.database.get_inst().cursor.execute(sql)
                    finally:
                        pkg.database.database.get_inst().release()
                except Exception as e1:
                    logging.exception(e1)
            else:
                # print("set invalid:{}".format(self.eid))
                # invalid
                self.valid = 0
                # 修改数据库记录

                pkg.database.database.get_inst().acquire()
                try:
                    pkg.database.database.get_inst().ensure_connection()
                    sql = "update `emotions` set `valid`=0 where id={}".format(self.id)
                    pkg.database.database.get_inst().cursor.execute(sql)
                finally:
                    pkg.database.database.get_inst().release()
        else:
            raise Exception("err msg:" + respobj["message"])


record_time = [600, 1200, 1800, 3600, 7200, 360 * 60, 720 * 60,
               1440 * 60]  # 10m,20m,30m,60m,120m(2h),360m(6h),720m(12h),1440m(24h)

tracking = []


def fetch_new_emotions_loop():
    while True:
        go(fetch_new_emotions)
        time.sleep(300)


def fetch_new_emotions():
    global tracking
    # print("fetch new emotions")

    qzone_inst = pkg.qzone.model.get_inst()
    if qzone_inst is None:
        return

    respobj = pkg.qzone.model.get_inst().get_emotion_list()
    if respobj["code"] != 200:
        raise Exception("err code:{} msg:{}".format(respobj["code"], respobj["msg"]))
    else:
        # 遍历检查是否已跟踪
        for emo in respobj["data"]:
            if index_by_emotion_id(emo["tid"]) == -1:
                # 不存在，验证是否还在跟踪期内，存数据库，存运行时变量
                now = time.time()
                if now - record_time[-1] >= emo["time"]:
                    # print("获取新emo时由于不在跟踪列表且不在跟踪期跳过:{}".format(emo["content"]))
                    continue

                # 从content提取pid
                logging.info("检测到新说说:{}".format(emo["content"]))
                pid = -1
                postid = re.findall(r'## [\d]*', emo["content"])
                if len(postid) != 0:
                    pid = int(str(postid[0]).replace("##", ""))

                try:
                    pkg.database.database.get_inst().acquire()
                    try:
                        pkg.database.database.get_inst().ensure_connection()

                        sql = "insert into `emotions` (`pid`,`eid`,`timestamp`,`valid`) values" \
                              " ({},'{}',{},1)".format(pid, emo["tid"], emo["time"])

                        pkg.database.database.get_inst().cursor.execute(sql)

                        pkg.database.database.get_inst().cursor.execute(
                            "select id from `emotions` where `eid`='{}'".format(emo["tid"]))
                        id = int(pkg.database.database.get_inst().cursor.fetchone()[0])
                    finally:
                        pkg.database.database.get_inst().release()
                    # 存运行时变量
                    emotion_obj = Emotion(id, pid, emo["tid"], emo["time"], 1)

                    tracking.append(emotion_obj)

                    go(emotion_obj.schedule)
                except Exception as e:
                    logging.exception(e)


def index_by_emotion_id(eid):
    global tracking
    # print(type(tracking),isinstance(tracking,Iterable))
    i = 0
    for emo in tracking:
        if emo.eid == eid:
            return i
        i += 1
    return -1


def load_tracking_emotions():  # 从数据库加载所有仍在跟踪的说说到运行时变量
    global tracking
    logging.info("正在从数据库加载仍在跟踪期的说说...")
    now = int(time.time())
    max_time_ago = now - record_time[-1]

    pkg.database.database.get_inst().acquire()
    try:
        pkg.database.database.get_inst().ensure_connection()
        pkg.database.database.get_inst().cursor.execute(
            "select id,`pid`,`eid`,`timestamp`,`valid` from `emotions` where `timestamp`>={};".format(max_time_ago))
        rows = pkg.database.database.get_inst().cursor.fetchall()
    finally:
        pkg.database.database.get_inst().release()

    for row in rows:
        emotion_obj = Emotion(row[0], row[1], row[2], row[3], row[4])
        logging.info("正在跟踪说说:{}".format(emotion_obj.eid))
        tracking.append(emotion_obj)
        go(emotion_obj.schedule)


def initialize_liker_recorder():
    load_tracking_emotions()
    fetch_new_emotions_loop()


def go(target, daemon=True, args=()):
    t1 = threading.Thread(target=target, args=args, daemon=daemon)
    t1.start()
    return t1


if __name__ == "__main__":
    # observer.initialize()
    initialize_liker_recorder()

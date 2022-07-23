import logging
from datetime import datetime
import json
import time

import pkg.database.database

TIME_PERIOD = [23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 2, 1, 0, ]

ANALYZE_ALL_PERIOD = 10

mysql_conn = 0
db_cursor = 0


# 分析历史热度和热度比
def analyze_history_heat_rate_and_heat():
    global db_cursor, mysql_conn

    AMOUNT_PER_QUERY = 1000

    now = int(time.time())

    result = pkg.database.database.get_inst().fetch_events(now - now % 86400 - (86400 * 100) - 8 * 3600, now,
                                                           page=1, capacity=0, event_type="visitor_increase")

    page = 0
    if result["eligible_amount"] % AMOUNT_PER_QUERY == 0:
        page = int(result["eligible_amount"] / AMOUNT_PER_QUERY)
    else:
        page = int(result["eligible_amount"] / AMOUNT_PER_QUERY) + 1

    data = []
    data_heat = []
    data_heat_per_hour = []
    last_recorded_amount_of_day = 0  # 上一个日访客量
    last_heat_recorded_timestamp = 0  # 上一次记录总访问量的时间戳
    last_recorded_heat = 0  # 上一次记录的总访客量

    for p in range(1, page + 1):
        time.sleep(0.2)

        result = pkg.database.database.get_inst().fetch_events(now - now % 86400 - (86400 * 100) - 8 * 3600, now,
                                                               page=p, capacity=AMOUNT_PER_QUERY,
                                                               event_type="visitor_increase")

        for event in result["events"]:
            jsonobj = json.loads(event["json"])
            if last_recorded_amount_of_day != 0 and (jsonobj["today_amount"] < last_recorded_amount_of_day):
                datet = datetime.fromtimestamp(event["timestamp"] - 86400)
                data.append(["{}".format(datet.date()), last_recorded_amount_of_day])

            last_recorded_amount_of_day = jsonobj["today_amount"]

            # 记录per hour和heat
            if (event["timestamp"] - last_heat_recorded_timestamp >= 3600 or last_heat_recorded_timestamp == 0) and (
                    event['timestamp'] >= (now - now % 86400 - (86400 * 100) - 8 * 3600)):
                data_heat.append([event['timestamp'] * 1000, jsonobj["total_amount"]])

                if last_recorded_heat != 0:
                    data_heat_per_hour.append([int((event['timestamp']) * 1000),
                                               int((jsonobj['total_amount'] - last_recorded_heat) / ((event[
                                                                                                          "timestamp"] - last_heat_recorded_timestamp) / 3600))])

                last_recorded_heat = jsonobj["total_amount"]
                last_heat_recorded_timestamp = event["timestamp"]

    datet = datetime.fromtimestamp(now)
    data.append(["{}".format(datet.date()), last_recorded_amount_of_day])

    try:
        pkg.database.database.get_inst().acquire()
        try:
            make_db_conn_sure()
            # 存数据库
            logging.info("分析日访客量完成")

            sql = "update `static_data` set `timestamp` = {},`json`='{}' where `key` = 'history_heat_rate';".format(
                int(time.time()), json.dumps(data))
            pkg.database.database.get_inst().cursor.execute(sql)

            logging.info("分析总访客量曲线完成")

            sql = "update `static_data` set `timestamp` = {},`json`='{}' where `key` = 'history_heat';".format(
                int(time.time()), json.dumps(data_heat))
            pkg.database.database.get_inst().cursor.execute(sql)

            logging.info("分析总访客量每小时完成")

            sql = "update `static_data` set `timestamp` = {},`json`='{}' where `key` = 'history_heat_per_hour';".format(
                int(time.time()), json.dumps(data_heat_per_hour))
            pkg.database.database.get_inst().cursor.execute(sql)
        finally:
            pkg.database.database.get_inst().release()
    except Exception as e:
        logging.exception(e)


# 分析历史说说发表
def analyze_history_emo_posted():
    global db_cursor, mysql_conn

    try:
        pkg.database.database.get_inst().acquire()
        try:
            make_db_conn_sure()
            now = int(time.time())
            pkg.database.database.get_inst().cursor.execute(
                "select `pid`,`timestamp` from `emotions` where `timestamp` >={}".format(
                    now - now % 86400 - (86400 * 100) - 8 * 3600))

            data = []
            while True:
                result = pkg.database.database.get_inst().cursor.fetchone()
                if result is None:
                    break
                if result[0] == -1:
                    continue
                data.append([int(result[1] * 1000), result[0]])

            # 存数据库
            logging.info("分析说说发表完成")

            make_db_conn_sure()

            sql = "update `static_data` set `timestamp` = {},`json`='{}' where `key` = 'history_emo_posted';".format(
                int(time.time()), json.dumps(data))
            pkg.database.database.get_inst().cursor.execute(sql)
        finally:
            pkg.database.database.get_inst().release()
    except Exception as e:
        logging.exception(e)


# 分析访客数量
def analyze_visitor_heat():
    global db_cursor, mysql_conn
    # (07) 1 2 3 4 5 6 7
    # (21) 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 0 1 2

    result = pkg.database.database.get_inst().fetch_events(0, int(time.time()), page=1, capacity=2147483640,
                                                           event_type="liker_record", json_like="\"interval\": 1200")

    if result["result"] == "success":
        # make temp array
        week = []  # 每个week的所有day
        for i in range(0, 7):
            day = []  # 每个day的所有hour
            for j in range(0, 20):
                hour = []  # 每个hour的所有样本
                day.append(hour)
            week.append(day)
        if result["events"] != None:
            for event in result["events"]:
                # 提取十分钟内的点赞量
                eventjson = json.loads(event["json"])
                wd, h_in_day = __calc_day_and_hour(event["timestamp"])
                if 2 < h_in_day < 7:
                    continue

                # print("append temp:",TIME_PERIOD.index(h_in_day),h_in_day,event["timestamp"])
                week[wd][TIME_PERIOD.index(h_in_day)].append(eventjson["like"])

        # 包装为static-data
        data = []
        day_index = 0
        for day in week:
            hour_index = 0

            for hour in day:  # 遍历每天的每个时段
                sum = 0

                for sample in hour:  # 遍历每个时段的样本
                    sum += sample

                average = (int(sum / len(hour)) if len(hour) > 0 else -1)
                if average != -1:
                    data.append([hour_index, day_index, average])
                hour_index += 1
            day_index += 1

        # 存数据库
        logging.info("分析周时段热力完成")

        pkg.database.database.get_inst().acquire()

        try:
            make_db_conn_sure()

            sql = "update `static_data` set `timestamp` = {},`json`='{}' where `key` = 'visitor_heat';".format(
                int(time.time()), json.dumps(data))
            pkg.database.database.get_inst().cursor.execute(sql)
        finally:
            pkg.database.database.get_inst().release()
    else:
        raise Exception("err:message:" + result["result"])


def __calc_day_and_hour(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    weekday = dt.weekday()
    timestamp += 28800  # 我们在东八区
    second_in_this_day = timestamp % 86400
    hour_in_day = second_in_this_day / 60 / 60

    return weekday, int(hour_in_day)


def initialize():
    analyzer_loop()


def make_db_conn_sure():
    pkg.database.database.get_inst().ensure_connection()


def analyze_all():
    try:
        analyze_visitor_heat()
        analyze_history_heat_rate_and_heat()
        analyze_history_emo_posted()
    except Exception as e:
        logging.exception(e)


def analyzer_loop():
    while True:
        try:
            logging.info("启动分析...")
            analyze_all()
            logging.info("完成时间:" + str(time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime())))
        except Exception as e:
            logging.error("无法完成分析" + str(time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime())))
            logging.exception(e)
        time.sleep(60 * ANALYZE_ALL_PERIOD)


if __name__ == "__main__":
    initialize()

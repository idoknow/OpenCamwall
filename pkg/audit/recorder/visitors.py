# 数据分析角色的观察者

import time
import json
import pkg.database.database
import pkg.qzone.model

last_record_total = 0
mysql_conn = 0
db_cursor = 0

RECORD_VISITOR_PERIOD = 5
VISITOR_AMOUNT_ACCURACY = 10

TYPE_VISITOR_INCREASE = "visitor_increase"
TYPE_NEW_POSTED = "new_posted"
TYPE_LIKER_RECORD = "liker_record"


def visitor_observer_loop():
    while True:
        record_visitor()
        time.sleep(60 * RECORD_VISITOR_PERIOD)


last_today_amount = -1


def record_visitor():
    global db_cursor, last_record_total, mysql_conn, last_today_amount
    try:
        obj = {
            'data': pkg.qzone.model.get_inst().get_visitor_amount_data(),
        }
        print("正在检查访客数量...total:{} today:{}".format(obj["data"]["total"], obj["data"]["today"]))
        if obj["data"]["total"] - last_record_total >= VISITOR_AMOUNT_ACCURACY or (
                obj["data"]["today"] < last_today_amount != -1):
            result = {
                "today_amount": obj["data"]["today"],
                "total_amount": obj["data"]["total"]
            }
            jsontext = json.dumps(result)

            if result["total_amount"] != 0:
                pkg.database.database.get_inst().ensure_connection()

                sql = "insert into `events` (`type`,`timestamp`,`json`) values ('{}',{},'{}')".format(
                    TYPE_VISITOR_INCREASE, int(time.time()), jsontext)
                print((time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(time.time()))))+" 记录访客:" + sql)
                pkg.database.database.get_inst().cursor.execute(sql)
                last_record_total = obj["data"]["total"]
        last_today_amount = obj["data"]["today"]
    except Exception as e:
        print(e)


def initialize_visitor_recorder():
    global mysql_conn, db_cursor, last_record_total
    # 读取上次的访客数量
    pkg.database.database.get_inst().ensure_connection()
    pkg.database.database.get_inst().cursor.execute(
        "select `json` from `events` where `type`='" + TYPE_VISITOR_INCREASE + "' order by id desc limit 1;")
    lsjson = pkg.database.database.get_inst().cursor.fetchone()
    obj = json.loads(lsjson[0])
    last_record_total = obj["total_amount"]
    visitor_observer_loop()


def initialize():
    initialize_visitor_recorder()


if __name__ == "__main__":
    initialize()
    record_visitor()

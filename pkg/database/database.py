import hashlib
import json
import math
import threading
import time
import uuid

import pymysql as pymysql
import requests
from pymysql.converters import escape_string

import pkg.routines.feedback_routines
import pkg.routines.post_routines

inst = None


def raw_to_escape(raw):
    return raw.replace("\\", "\\\\").replace('\'', '‘')


def md5Hash(string):
    return hashlib.md5(str(string).encode('utf8')).hexdigest()


def get_qq_nickname(uin):
    url = "https://r.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={}".format(uin)
    response = requests.get(url)
    text = response.content.decode('gbk', 'ignore')
    json_data = json.loads(text.replace("portraitCallBack(", "")[:-1])
    nickname = json_data[str(uin)][6]
    return nickname


class MySQLConnection:
    connection = None
    cursor = None

    # 互斥锁
    mutex = threading.Lock()

    current_salt = ''
    previous_salt = ''

    appid = ''
    app_secret = ''

    def __init__(self, host, port, user, password, database, appid='', app_secret='', autocommit=True):
        global inst
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self.appid = appid
        self.app_secret = app_secret

        inst = self

        salt_thread = threading.Thread(target=self.salt_generator, args=(), daemon=True)
        salt_thread.start()

        self.connect()

    def connect(self, autocommit=True):
        self.connection = pymysql.connect(host=self.host,
                                          port=self.port,
                                          user=self.user,
                                          password=self.password,
                                          db=self.database,
                                          autocommit=autocommit,
                                          charset='utf8mb4', )
        self.cursor = self.connection.cursor()

    def ensure_connection(self, attempts=3):
        for i in range(attempts):
            try:
                self.connection.ping()
                return i
            except:
                self.connect()
                if i == attempts - 1:
                    raise Exception('MySQL连接失败')
            time.sleep(2)

    def acquire(self):
        self.mutex.acquire(timeout=3)
        if not self.mutex.locked():  # 五秒还没获得锁,大抵又死锁了
            self.mutex.release()
            self.mutex.acquire()

    def release(self):
        self.mutex.release()

    def salt_generator(self):
        self.current_salt = md5Hash(str(uuid.uuid4()))
        while True:
            self.previous_salt = self.current_salt
            self.current_salt = md5Hash(str(uuid.uuid4()))
            time.sleep(120)

    def get_current_salt(self):
        return self.current_salt

    wx_code2session_url = 'https://api.weixin.qq.com/sns/jscode2session?appid={}&secret={}&js_code={}&grant_type=authorization_code'

    def get_openid(self, code):
        result = {
            'result': 'success',
            'openid': ''
        }
        # 从微信获取openid
        res = requests.get(self.wx_code2session_url.format(self.appid, self.app_secret, code))
        # print(res.json())
        res_json = res.json()
        if 'errcode' in res_json and res_json['errcode'] != 0:
            if res_json['errcode'] == 40029:
                result['result'] = 'code无效'
            elif res_json['errcode'] == 45011:
                result['result'] = '请求频繁'
            elif res_json['errcode'] == 40226:
                result['result'] = '用户已被系统风控'
            else:
                result['result'] = '未知错误'
            return result
        else:
            result['openid'] = res_json['openid']
            return result

    def register(self, openid: str, uin):

        self.acquire()
        try:
            self.ensure_connection()
            sql = "select * from `accounts` where `qq`='{}'".format(escape_string(str(uin)))
            self.cursor.execute(sql)
            results = self.cursor.fetchall()
            for _ in results:
                # 只要有
                raise Exception("该QQ号已经绑定了微信号,请进入小程序尝试刷新,若要解除绑定请发送 #解绑")

            sql = "insert into `accounts` (`qq`,`openid`,`timestamp`) values ('{}','{}',{})".format(
                escape_string(str(uin)), escape_string(openid),
                int(time.time()))
            self.cursor.execute(sql)

            # 插入到绑定表完成了,检查账户密码表
            sql = "select * from `uniauth` where `openid`='{}'".format(escape_string(openid))
            self.cursor.execute(sql)
            results = self.cursor.fetchall()
            if len(results) == 0:
                sql = "insert into `uniauth` (`openid`,`timestamp`) values ('{}',{})".format(escape_string(openid),
                                                                                             int(time.time()))
                self.cursor.execute(sql)
        finally:
            self.release()
        # self.connection.commit()

    def unbinding(self, uin):
        self.acquire()
        try:
            self.ensure_connection()
            sql = "delete from `accounts` where `qq`='{}'".format(escape_string(str(uin)))
            self.cursor.execute(sql)
        finally:
            self.release()
        # self.connection.commit()

    def post_new(self, text: str, media: str, anonymous: bool, qq: int, openid: str):
        self.acquire()
        try:
            self.ensure_connection()
            sql = "insert into `posts` (`openid`,`qq`,`timestamp`,`text`,`media`,`anonymous`) values ('{}','{}',{},'{}'," \
                  "'{}',{})".format(escape_string(openid), escape_string(str(qq)), int(time.time()),
                                    escape_string(text), escape_string(media), 1 if anonymous else 0)
            self.cursor.execute(sql)
            # self.connection.commit()

            sql = "select `id` from `posts` where `openid`='{}' order by `id` desc limit 1".format(
                escape_string(openid))
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
        finally:
            self.release()

        pkg.routines.post_routines.new_post_incoming({
            'id': result[0],
            'text': text,
            'media': media,
            'anonymous': anonymous,
            'qq': qq,
        })

        return result[0]

    def pull_one_post(self, post_id=-1, status='', openid='', order='asc'):
        results = self.pull_posts(post_id, status, openid, order, capacity=1)
        if len(results['posts']) > 0:
            return results['posts'][0]
        else:
            return {'result': 'err:no result'}

    def pull_posts(self, post_id=-1, status='', openid='', order='asc', capacity=10, page=1):
        where_statement = ''
        if post_id != -1:
            where_statement = "and `id`={}".format(post_id)
        if status != '' and status != '所有':
            where_statement += " and `status`='{}'".format(status)
        if openid != '':
            where_statement += " and `openid`='{}'".format(openid)

        # 计算总数
        self.acquire()
        try:
            self.ensure_connection()
            sql = "select count(*) from `posts` where 1=1 {} order by `id` {}".format(where_statement, order)
            self.cursor.execute(sql)
            total = self.cursor.fetchone()[0]

            # 计算page是否超范围
            if page > math.ceil(total / capacity):
                page = math.ceil(total / capacity)
                if page == 0:
                    page = 1

            limit_statement = ''
            if capacity != -1:
                limit_statement = "limit {},{}".format((page - 1) * capacity, capacity)

            sql = "select * from `posts` where 1=1 {} order by `id` {} {}".format(where_statement, order,
                                                                                  limit_statement)
            self.cursor.execute(sql)
            results = self.cursor.fetchall()
        finally:
            self.release()

        posts = []
        for res in results:
            posts.append({
                'result': 'success',
                'id': res[0],
                'openid': res[1],
                'qq': res[2],
                'timestamp': res[3],
                'text': res[4],
                'media': res[5],
                'anonymous': res[6],
                'status': res[7],
                'review': res[8]
            })
        result = {
            'result': 'success',
            'page': page,
            'page_list': [i for i in range(1, int(total / capacity) + (2 if total % capacity > 0 else 1))],
            'table_amount': total,
            'status': status,
            'posts': posts
        }

        return result

    def update_post_status(self, post_id, new_status, review='', old_status=''):
        self.acquire()
        try:

            self.ensure_connection()
            sql = "select `status` from `posts` where `id`={}".format(post_id)
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
        finally:
            self.release()

        if result is None:
            raise Exception("无此稿件:{}".format(post_id))

        if old_status != '':
            if result[0] != old_status:
                raise Exception("此稿件状态不是:{}".format(old_status))

        self.acquire()
        try:

            self.ensure_connection()
            sql = "update `posts` set `status`='{}' where `id`={}".format(escape_string(new_status), post_id)
            self.cursor.execute(sql)
            if review != '':
                sql = "update `posts` set `review`='{}' where `id`={}".format(escape_string(review), post_id)
                self.cursor.execute(sql)
        finally:
            self.release()

        temp_thread = threading.Thread(target=pkg.routines.post_routines.post_status_changed,
                                       args=(post_id, new_status), daemon=True)
        # pkg.routines.post_routines.post_status_changed
        # self.connection.commit()
        temp_thread.start()

    def pull_log_list(self, capacity=10, page=1):
        self.acquire()
        try:

            self.ensure_connection()
            limit_statement = "limit {},{}".format((page - 1) * capacity, capacity)

            sql = "select count(*) from `logs` order by `id` desc"
            self.cursor.execute(sql)
            total = self.cursor.fetchone()[0]

            sql = "select * from `logs` order by `id` desc {}".format(limit_statement)
            self.cursor.execute(sql)
            logs = self.cursor.fetchall()
        finally:
            self.release()

        result = {'result': 'success', 'logs': []}
        for log in logs:
            result['logs'].append({
                'id': log[0],
                'timestamp': log[1],
                'location': log[2],
                'account': log[3],
                'operation': log[4],
                'content': log[5],
                'ip': log[6]
            })

        result['page'] = page
        result['page_list'] = [i for i in range(1, int(total / capacity) + (2 if total % capacity > 0 else 1))]
        return result

    def fetch_qq_accounts(self, openid):
        self.ensure_connection()

        result = {
            'isbanned': False,
        }

        if openid == '':
            raise Exception("openid不能为空")

        self.acquire()
        try:
            self.ensure_connection()
            # 检查账户密码表,不存在则插入
            sql = "select * from `uniauth` where `openid`='{}'".format(escape_string(openid))
            self.cursor.execute(sql)
            results = self.cursor.fetchall()
            if len(results) == 0:
                sql = "insert into `uniauth` (`openid`,`timestamp`) values ('{}',{})".format(escape_string(openid),
                                                                                             int(time.time()))
                self.cursor.execute(sql)

            # 检查是否被封禁
            sql = "select * from `banlist` where `openid`='{}' order by id desc".format(escape_string(openid))
            self.cursor.execute(sql)
            ban = self.cursor.fetchone()
            if ban is not None:
                start_time = ban[2]
                expire_time = ban[3]
                reason = ban[4]
                if time.time() < expire_time:
                    result['isbanned'] = True
                    result['start'] = start_time
                    result['expire'] = expire_time
                    result['reason'] = reason
                    return result

            sql = "select * from `accounts` where `openid`='{}'".format(escape_string(openid))
            self.cursor.execute(sql)
            accounts = self.cursor.fetchall()
        finally:
            self.release()

        result['accounts'] = []
        for account in accounts:
            # 获取nick
            result['accounts'].append({
                'id': account[0],
                'qq': account[2],
                'nick': get_qq_nickname(account[2]),
                'resgister_time': account[3],
                'identity': account[4],
            })

        return result

    def fetch_constant(self, key):
        self.acquire()
        try:

            self.ensure_connection()
            sql = "select * from `constants` where `key`='{}'".format(escape_string(key))
            self.cursor.execute(sql)
            row = self.cursor.fetchone()
        finally:
            self.release()

        result = {
            'result': 'success',
            'exist': False,
            'value': ''
        }

        if row is None:
            result['exist'] = False
        else:
            result['exist'] = True
            result['value'] = row[1]

        return result

    def fetch_service_list(self):
        self.acquire()
        try:

            self.ensure_connection()
            sql = "select * from `services`"
            self.cursor.execute(sql)
            services = self.cursor.fetchall()
        finally:
            self.release()

        result = {
            'result': 'success',
            'services': []
        }

        for service in services:
            if service[6] != 1:
                continue
            result['services'].append({
                'id': service[0],
                'name': service[1],
                'description': service[2],
                'order': service[3],
                'page_url': service[4],
                'color': service[5],
                'enable': service[6],
                'external_url': service[7],
            })

        return result

    def fetch_events(self, begin_ts, end_ts, page, capacity, event_type='', json_like=''):

        result = {
            'result': 'success',
            'eligible_amount': 0,
            'page': page,
            'capacity': capacity,
            'beginning': begin_ts,
            'ending': end_ts,
            'events': []
        }

        type_condition = ''
        if event_type != '':
            type_condition = "and `type`='{}'".format(event_type)

        json_like_condition = ''
        if json_like != '':
            json_like_condition = "and `json` like '%{}%'".format(json_like)

        # 获取符合必须条件的数量
        sql = "select count(*) from `events` where `timestamp`>={} and `timestamp`<={} {} {}".format(begin_ts, end_ts,
                                                                                                     type_condition,
                                                                                                     json_like_condition)
        self.acquire()
        try:
            self.ensure_connection()

            self.cursor.execute(sql)
            eligible_count = self.cursor.fetchone()[0]
            result['eligible_amount'] = eligible_count

            # 分页获取符合必须条件的数据
            limit_statement = "limit {},{}".format((page - 1) * capacity, capacity)
            sql = "select * from `events` where `timestamp`>={} and `timestamp`<={} {} {} {}".format(begin_ts, end_ts,
                                                                                                     type_condition,
                                                                                                     json_like_condition,
                                                                                                     limit_statement)
            self.cursor.execute(sql)
            events = self.cursor.fetchall()
        finally:
            self.release()

        for event in events:
            result['events'].append({
                'id': event[0],
                'type': event[1],
                'timestamp': event[2],
                'json': event[3],
            })

        return result

    def fetch_static_data(self, key):
        self.acquire()
        try:

            self.ensure_connection()
            sql = "select * from `static_data` where `key`='{}'".format(escape_string(key))
            self.cursor.execute(sql)
            row = self.cursor.fetchone()
        finally:
            self.release()

        result = {
            'result': 'success',
            'timestamp': 0,
            'content': ''
        }

        if row is not None:
            result['timestamp'] = row[1]
            result['content'] = row[2]

        return result

    def fetch_content_list(self, capacity, page):
        self.acquire()
        try:
            self.ensure_connection()
            limit_statement = "limit {},{}".format((page - 1) * capacity, capacity)
            sql = "select count(*) \nfrom (\n\tselect p.id pid,p.openid,e.id eid,p.`status` `status`,(\n\t\tcase " \
                  "\n\t\twhen p.`timestamp`is null\n\t\tthen e.`timestamp`\n\t\twhen e.`timestamp`is null\n\t\tthen " \
                  "p.`timestamp`\n\t\twhen (e.`timestamp` is not null) and (p.`timestamp`is not null)\n\t\tthen greatest(" \
                  "p.`timestamp`,e.`timestamp`)\n\t\tend\n\t) gr_time from posts p\n\tleft outer join emotions e\n\ton " \
                  "p.id=e.pid\n    \n\tunion\n    \n\tselect p.id pid,p.openid,e.id eid,p.`status` `status`,(\n\t\tcase " \
                  "\n\t\twhen p.`timestamp`is null\n\t\tthen e.`timestamp`\n\t\twhen e.`timestamp`is null\n\t\tthen " \
                  "p.`timestamp`\n\t\twhen (e.`timestamp` is not null) and (p.`timestamp`is not null)\n\t\tthen greatest(" \
                  "p.`timestamp`,e.`timestamp`)\n\t\tend\n\t) gr_time from posts p\n\tright outer join emotions e\n\ton " \
                  "p.id=e.pid\n) t\norder by gr_time desc "
            self.cursor.execute(sql)
            total = self.cursor.fetchone()[0]

            sql = "select * \nfrom (\n\tselect coalesce(p.id,-1) pid,coalesce(p.openid,''),coalesce(-1,e.id) eid," \
                  "coalesce(e.eid,'') euid,coalesce( p.`status`,'已发表') `status`,(\n\t\tcase \n\t\twhen p.`timestamp`is " \
                  "null\n\t\tthen e.`timestamp`\n\t\twhen e.`timestamp`is null\n\t\tthen p.`timestamp`\n\t\twhen (" \
                  "e.`timestamp` is not null) and (p.`timestamp`is not null)\n\t\tthen greatest(p.`timestamp`," \
                  "e.`timestamp`)\n\t\tend\n\t) gr_time from posts p\n\tleft outer join emotions e\n\ton p.id=e.pid\n    " \
                  "\n\tunion\n    \n\tselect coalesce(p.id,-1) pid,coalesce(p.openid,''),coalesce(-1,e.id) eid," \
                  "coalesce(e.eid,'') euid,coalesce( p.`status`,'已发表') `status`,(\n\t\tcase \n\t\twhen p.`timestamp`is " \
                  "null\n\t\tthen e.`timestamp`\n\t\twhen e.`timestamp`is null\n\t\tthen p.`timestamp`\n\t\twhen (" \
                  "e.`timestamp` is not null) and (p.`timestamp`is not null)\n\t\tthen greatest(p.`timestamp`," \
                  "e.`timestamp`)\n\t\tend\n\t) gr_time from posts p\n\tright outer join emotions e\n\ton p.id=e.pid\n) " \
                  "t\norder by gr_time desc {}".format(limit_statement)
            self.cursor.execute(sql)
            contents = self.cursor.fetchall()
        finally:
            self.release()

        result = {
            'result': 'success',
            'amt': total,
            'page': page,
            'capacity': capacity,
            'contents': []
        }

        for content in contents:
            content_result = {
                'pid': content[0],
                'openid': content[1],
                'eid': content[2],
                'euid': content[3],
                'status': content[4],
                'timestamp': content[5],
            }

            if content[3] != '':
                # 检出所有点赞记录
                self.acquire()
                try:
                    self.ensure_connection()
                    sql = "select `timestamp`,json from `events` where `type`='liker_record' and `json` like '%{}%' order by `timestamp`;".format(
                        content[3])
                    self.cursor.execute(sql)
                    liker_record_rows = self.cursor.fetchall()
                finally:
                    self.release()
                # 结果
                like_records = []
                for liker_record in liker_record_rows:
                    # 加载liker_record的json
                    json_obj = json.loads(liker_record[1])

                    like_records.append([liker_record[0], json_obj['interval'], json_obj['like']])
                content_result['like_records'] = like_records

            result['contents'].append(content_result)
        return result

    def user_feedback(self, openid, content, media):
        self.acquire()
        try:

            self.ensure_connection()
            sql = "insert into `feedback`(`openid`,`content`,`timestamp`,`media`)" \
                  " values('{}','{}',{},'{}')".format(escape_string(openid),
                                                      escape_string(content),
                                                      int(time.time()),
                                                      escape_string(media))

            temp_thread = threading.Thread(target=pkg.routines.feedback_routines.receive_feedback,
                                           args=(openid, content),
                                           daemon=True)
            temp_thread.start()

            self.cursor.execute(sql)
        finally:
            self.release()
        return 'success'

    def fetch_uniauth_by_openid(self, openid):

        result = {
            'uid': 0,
            'result': 'success',
            'openid': openid,
            'timestamp': 0,
        }
        self.acquire()
        try:
            self.ensure_connection()
            sql = "select * from `uniauth` where `openid`='{}'".format(escape_string(openid))
            self.cursor.execute(sql)
            row = self.cursor.fetchone()
            if row is None:
                result['result'] = 'fail:没有此账户'
                return result
            result['timestamp'] = row[2]
            result['uid'] = row[0] + 10000
            if row[4] != 'valid':
                result['result'] = 'fail:账户不可用'
                return result
            if row[3] == '':
                result['result'] = 'warn:账户未设置密码'
                return result
        finally:
            self.release()
        return result

    def change_password(self, openid, password):
        self.acquire()
        try:
            self.ensure_connection()
            sql = "update `uniauth` set `password`='{}' where `openid`='{}'".format(escape_string(password),
                                                                                    escape_string(openid))
            self.cursor.execute(sql)
        finally:
            self.release()
        return 'success'

    def verify_account(self, uid, password, service_name):
        result = {
            'result': 'success',
            'uid': '',
        }

        self.acquire()
        try:
            self.ensure_connection()
            # 从accounts表检出此qq号的openid
            sql = "select `openid` from `uniauth` where `id`={}".format(int(uid) - 10000)
            self.cursor.execute(sql)
            row = self.cursor.fetchone()
            if row is None:
                result['result'] = 'fail:没有此账户'
                return result
            openid = row[0]
            # 从uniauth表检出此openid的密码
            sql = "select * from `uniauth` where `openid`='{}'".format(escape_string(openid))
            self.cursor.execute(sql)
            row = self.cursor.fetchone()
            if row is None:
                result['result'] = 'fail:无此账户'
                return result
            if row[3] == '':
                result['result'] = 'fail:账户未设置密码'
                return result
            if row[4] != 'valid':
                result['result'] = 'fail:账户不可用'
                return result

            if password != md5Hash(row[3] + self.current_salt) and password != md5Hash(row[3] + self.previous_salt):
                result['result'] = 'fail:密码错误'
                return result
            result['uid'] = md5Hash(openid + service_name)
        finally:
            self.release()

        return result

    def submit_ticket(self, title, openid, contact, content, media):
        result = {
            'result': 'success',
            'id': 0
        }

        self.acquire()
        try:
            self.ensure_connection()
            sql = "insert into `stu_work_tickets`(`timestamp`,`launcher`,`title`,`contact`,`content`,`media`)" \
                  " values ({},'{}','{}','{}','{}','{}')".format(int(time.time()),
                                                                 escape_string(openid),
                                                                 escape_string(title),
                                                                 escape_string(contact),
                                                                 escape_string(content),
                                                                 media)
            self.cursor.execute(sql)

            sql = "select id from `stu_work_tickets` where `launcher` = '{}' order by id desc limit 1" \
                .format(escape_string(openid))

            self.cursor.execute(sql)
            row = self.cursor.fetchone()
            result['id'] = row[0]
        finally:
            self.release()

        return result

    pull_tickets_order_sql = """
        select {},
                ifNull(f_amt,0) famt,
                if((select openid a 
                    from `stu_work_follow_relationships` 
                    where `target`=f_target and openid='{}' 
                    limit 1) 
                    is null,0,1) followed,
                (select count(*) 
                from `stu_work_replies` 
                where `target`=f_target) ramt
        from (select *
            from (select target f_target,count(*) f_amt
                    from `stu_work_follow_relationships`
                    group by `target`) relationship
            right join (select *
                        from `stu_work_tickets`
                        where `timestamp` >= {} and `timestamp` <= {}) tickets
            on tickets.id=relationship.f_target) result
        order by {} desc
    """

    def pull_multi_tickets(self, capacity, page, start, end, orderby, openid):
        result = {
            'result': 'success',
            'page_list': [1],
            'page': 1,
            'eligible': 0,
            'orderby': orderby,
            'data': []
        }

        self.acquire()

        try:
            self.ensure_connection()

            if orderby == 'heat':
                orderby = 'famt'
            else:
                orderby = 'id'

            # 获取符合条件的数量
            self.cursor.execute(self.pull_tickets_order_sql.format("count(*) eligible", openid, start, end, orderby))
            row = self.cursor.fetchone()

            eligible = row[0]

            result['eligible'] = eligible

            # 计算数据起点
            page_amt = int(eligible / capacity) if eligible % capacity == 0 else int(eligible / capacity) + 1

            result['page_list'] = [i for i in range(1, page_amt + 1)]

            if page >= page_amt:
                page = page_amt

            if page <= 0:
                page = 1

            result['page'] = page

            self.cursor.execute(
                self.pull_tickets_order_sql.format("*", openid, start, end, orderby) + " limit {},{}".format(
                    (page - 1) * capacity, capacity))
            # print(self.pull_tickets_order_sql.format("*", openid, start, end, orderby)+" limit {},{}".format((
            # page-1)*capacity, capacity))
            rows = self.cursor.fetchall()

            data = []

            for row in rows:
                data.append({
                    'id': row[2],
                    'timestamp': row[3],
                    'launcher': row[4],
                    'title': row[5],
                    'contact': row[6],
                    'content': row[7],
                    'media': row[8],
                    'status': row[9],
                    'famt': row[10],
                    'followed': row[11],
                    'ramt': row[12]
                })

            result['data'] = data

            return result
        finally:
            self.release()

    def follow_ticket(self, openid, target):
        result = {
            'result': 'success'
        }

        self.acquire()

        try:
            self.ensure_connection()
            sql = "insert into `stu_work_follow_relationships`(`timestamp`, `openid`,`target`) values ({},'{}',{})".format(
                int(time.time()), escape_string(openid), target)
            self.cursor.execute(sql)
        finally:
            self.release()

        return result

    def unfollow_ticket(self, openid, target):
        result = {
            'result': 'success'
        }

        self.acquire()

        try:
            self.ensure_connection()
            sql = "delete from `stu_work_follow_relationships` where `openid`='{}' and `target`={}" \
                .format(escape_string(openid), target)
            self.cursor.execute(sql)
        finally:
            self.release()

        return result

    def get_ticket_follower_amt(self, target):
        result = {
            'result': 'success',
            'amt': 0
        }

        self.acquire()

        try:
            self.ensure_connection()
            sql = "select count(*) amt from `stu_work_follow_relationships` where `target`={}".format(target)
            self.cursor.execute(sql)
            row = self.cursor.fetchone()
            result['amt'] = row[0]
        finally:
            self.release()

        return result

    def reply_ticket(self, openid, nick, target, content, reply_type):
        result = {
            'result': 'success'
        }

        self.acquire()

        try:
            self.ensure_connection()

            sql = "insert into `stu_work_replies`(`timestamp`,`openid`,`nick`,`target`,`content`,`type`)" \
                  " values ({},'{}','{}',{},'{}','{}')".format(int(time.time()), escape_string(openid),
                                                               escape_string(nick), target, escape_string(content),
                                                               reply_type)
            self.cursor.execute(sql)
        finally:
            self.release()

        return result

    fetch_reply_sql = """
        select *,if(`openid`='{}',1,0) mine from `stu_work_replies` where `target`={} order by `id`
        """

    def fetch_ticket_replies(self, target, openid):
        result = {
            'result': 'success',
            'data': []
        }

        self.acquire()

        try:
            self.ensure_connection()
            self.cursor.execute(self.fetch_reply_sql.format(escape_string(openid), target))
            rows = self.cursor.fetchall()

            data = []

            for row in rows:
                data.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'nick': row[2],
                    'target': row[4],
                    'content': row[5],
                    'type': row[6],
                    'mine': row[7]
                })

            result['data'] = data
        finally:
            self.release()

        return result


def get_inst() -> MySQLConnection:
    global inst
    return inst

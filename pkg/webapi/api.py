import json
import time

from flask import Flask, request
import sys

import config
import pkg
import threading

import pkg.routines.post_routines

sys.path.append("../")
from pkg.database.database import MySQLConnection

inst = None

class RESTfulAPI:
    app = None

    db_mgr = None

    host = ''
    port = 8989
    domain = ''
    ssl_context = None

    proxy_thread = None

    def __init__(self, db: MySQLConnection, port=8989, host='0.0.0.0', domain='', ssl_context=None):
        self.db_mgr = db

        app = Flask(__name__)

        # 注册各接口
        @app.route('/postnew', methods=['GET'])
        def post_new():
            try:
                post_id = self.db_mgr.post_new(request.args['text'], request.args['media'],
                                               bool(request.args['anonymous']),
                                               int(request.args['qq']), request.args['openid'])

                return '操作成功'
            except Exception as e:
                return str(e)

        @app.route('/pullonepoststatus', methods=['GET'])
        def pull_one_post_status():
            try:
                result = self.db_mgr.pull_one_post(status=request.args['status'],
                                                   openid=request.args['openid'] if 'openid' in request.args else '')
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/pullmultipostsstatus', methods=['GET'])
        def pull_multi_posts_status():
            try:
                result = self.db_mgr.pull_posts(status=request.args['status'], order='desc',
                                                capacity=int(request.args['capacity']), page=int(request.args['page']))

                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/updatepoststatus', methods=['GET'])
        def update_post_status():
            try:
                self.db_mgr.update_post_status(int(request.args['id']), request.args['new-status'],
                                               review=request.args['review'] if 'review' in request.args else '')
                return 'success'
            except Exception as e:
                return str(e)

        @app.route('/cancelonepost', methods=['GET'])
        def cancel_one_post():
            try:
                # 获取id
                post_id = self.db_mgr.pull_one_post(status='未审核', openid=request.args['openid'])['id']
                self.db_mgr.update_post_status(post_id, '取消')

                return 'success'
            except Exception as e:
                return str(e)

        @app.route('/pullloglist', methods=['GET'])
        def pull_log_list():
            try:
                result = self.db_mgr.pull_log_list(int(request.args['capacity']), int(request.args['page']))
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                # raise e
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/account', methods=['GET'])
        def fetch_accounts():
            try:
                result = self.db_mgr.fetch_qq_accounts(request.args['openid'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                # raise e
                return "{}".format(str(e))

        @app.route('/constant', methods=['GET'])
        def fetch_constant():
            try:
                result = self.db_mgr.fetch_constant(request.args['key'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/fetchservicelist', methods=['GET'])
        def fetch_service_list():
            try:
                result = self.db_mgr.fetch_service_list()
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/events/fetchstaticdata', methods=['GET'])
        def fetch_static_data():
            try:
                result = self.db_mgr.fetch_static_data(request.args['key'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/events/fetchcontents', methods=['GET'])
        def fetch_contents():
            try:
                result = self.db_mgr.fetch_content_list(int(request.args['capacity']), int(request.args['page']))
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                # raise e
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/userfeedback', methods=['GET'])
        def user_feedback():
            try:
                result = self.db_mgr.user_feedback(request.args['openid'], request.args['content'],
                                                   media=request.args['media'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                return "失败:{}".format(str(e))

        self.app = app
        self.app.config['JSON_AS_ASCII'] = False
        self.app.config["CACHE_TYPE"] = "null"

        self.host = host
        self.port = port
        self.domain = domain
        self.ssl_context = ssl_context

        # self.proxy_thread = threading.Thread(target=self.run_api, args=(), daemon=True)
        #
        # self.proxy_thread.start()

    def run_api(self):
        if self.domain != '' and self.ssl_context != None:
            self.app.config['SERVER_NAME'] = self.domain
            self.app.run(host=self.host, port=self.port, ssl_context=self.ssl_context)
        else:
            self.app.run(host=self.host, port=self.port)


def get_inst() -> RESTfulAPI:
    global inst
    return inst


if __name__ == '__main__':
    db_mgr = pkg.database.database.MySQLConnection(config.database_context['host'],
                                                   config.database_context['port'],
                                                   config.database_context['user'],
                                                   config.database_context['password'],
                                                   config.database_context['db'])

    api = RESTfulAPI(db_mgr, domain=config.api_domain, ssl_context=config.api_ssl_context)

    time.sleep(100000)

import json
import logging
import time

from flask import Flask, request, send_file
from flask_cors import CORS
import sys

import config

import pkg.routines.post_routines

sys.path.append("../")
from pkg.database.database import MySQLConnection
from pkg.database.mediamgr import MediaManager

inst = None


class RESTfulAPI:
    app = None

    db_mgr = None

    media_mgr = None

    host = ''
    port = 8989
    domain = ''
    ssl_context = None

    proxy_thread = None

    def __init__(self, db: MySQLConnection, mm: MediaManager, port=8989, host='0.0.0.0', domain='', ssl_context=None):
        self.db_mgr = db
        self.media_mgr = mm

        app = Flask('__name__')

        # 注册各接口
        @app.route('/postnew', methods=['GET'])
        def post_new():
            try:
                post_id = self.db_mgr.post_new(request.args['text'], request.args['media'],
                                               True if request.args['anonymous'] == 'true' else False,
                                               int(request.args['qq']), request.args['openid'])

                return '操作成功'
            except Exception as e:
                logging.exception(e)
                return str(e)

        @app.route('/pullonepoststatus', methods=['GET'])
        def pull_one_post_status():
            try:
                result = self.db_mgr.pull_one_post(status=request.args['status'],
                                                   openid=request.args['openid'] if 'openid' in request.args else '')
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/pullmultipostsstatus', methods=['GET'])
        def pull_multi_posts_status():
            try:
                result = self.db_mgr.pull_posts(status=request.args['status'], order='desc',
                                                capacity=int(request.args['capacity']), page=int(request.args['page']))

                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/updatepoststatus', methods=['GET'])
        def update_post_status():
            try:
                self.db_mgr.update_post_status(int(request.args['id']), request.args['new-status'],
                                               review=request.args['review'] if 'review' in request.args else '')
                return 'success'
            except Exception as e:
                logging.exception(e)
                return str(e)

        @app.route('/cancelonepost', methods=['GET'])
        def cancel_one_post():
            try:
                # 获取id
                post_id = self.db_mgr.pull_one_post(status='未审核', openid=request.args['openid'])['id']
                self.db_mgr.update_post_status(post_id, '取消')

                return 'success'
            except Exception as e:
                logging.exception(e)
                return str(e)

        @app.route('/pullloglist', methods=['GET'])
        def pull_log_list():
            try:
                result = self.db_mgr.pull_log_list(int(request.args['capacity']), int(request.args['page']))
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                # raise e
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/get_openid', methods=['GET'])
        def get_openid():
            try:
                result = self.db_mgr.get_openid(request.args['code'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/account', methods=['GET'])
        def fetch_accounts():
            try:
                result = self.db_mgr.fetch_qq_accounts(request.args['openid'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                # raise e
                return "{}".format(str(e))

        @app.route('/constant', methods=['GET'])
        def fetch_constant():
            try:
                result = self.db_mgr.fetch_constant(request.args['key'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/fetchservicelist', methods=['GET'])
        def fetch_service_list():
            try:
                result = self.db_mgr.fetch_service_list()
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/events/fetchstaticdata', methods=['GET'])
        def fetch_static_data():
            try:
                result = self.db_mgr.fetch_static_data(request.args['key'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/events/fetchcontents', methods=['GET'])
        def fetch_contents():
            try:
                result = self.db_mgr.fetch_content_list(int(request.args['capacity']), int(request.args['page']))
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                # raise e
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/userfeedback', methods=['GET'])
        def user_feedback():
            try:
                result = self.db_mgr.user_feedback(request.args['openid'], request.args['content'],
                                                   media=request.args['media'])
                return result
            except Exception as e:
                logging.exception(e)
                return "失败:{}".format(str(e))

        @app.route('/fetchuniauthinfo', methods=['GET'])
        def fetch_uniauth_by_openid():
            try:
                result = self.db_mgr.fetch_uniauth_by_openid(request.args['openid'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/changepassword', methods=['GET'])
        def change_password():
            try:
                result = self.db_mgr.change_password(request.args['openid'], request.args['new-password'])
                return result
            except Exception as e:
                logging.exception(e)
                return "失败:{}".format(str(e))

        @app.route('/getloginsalt', methods=['GET'])
        def get_login_salt():
            return self.db_mgr.get_current_salt()

        @app.route('/verifyaccount', methods=['GET'])
        def verify_account():
            try:
                result = self.db_mgr.verify_account(request.args['uid'], request.args['password'],
                                                    request.args['service'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/media/upload_image', methods=['PUT', 'POST'])
        def upload_media():
            try:
                file = request.files['file']
                if file is None:
                    raise Exception('no file')

                result = self.media_mgr.upload_image(request.files['file'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/media/download_image/<string:file_name>', methods=['GET'])
        def download_media(file_name):
            try:
                if '/' in file_name:
                    return 'error', 400
                file_path = self.media_mgr.get_file_path(file_name)
                if file_path is None:
                    return 'error', 404
                return send_file(file_path)
            except Exception as e:
                logging.exception(e)
                return 'error', 500

        @app.route('/stuwork/submit_ticket', methods=['GET'])
        def stuwork_submit_ticket():
            try:
                result = self.db_mgr.submit_ticket(request.args['title'], request.args['openid'],
                                                   request.args['contact'],
                                                   request.args['content'], request.args['media'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/stuwork/pull_multi_tickets', methods=['GET'])
        def stuwork_pull_multi_tickets():
            try:
                result = self.db_mgr.pull_multi_tickets(int(request.args['capacity']), int(request.args['page']),
                                                        request.args['start'], request.args['end'],
                                                        request.args['orderby'], request.args['openid'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/stuwork/follow_ticket', methods=['GET'])
        def stuwork_follow_ticket():
            try:
                result = self.db_mgr.follow_ticket(request.args['openid'], request.args['target'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/stuwork/unfollow_ticket', methods=['GET'])
        def stuwork_unfollow_ticket():
            try:
                result = self.db_mgr.unfollow_ticket(request.args['openid'], request.args['target'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/stuwork/get_ticket_follower_amt', methods=['GET'])
        def stuwork_get_ticket_follower_amt():
            try:
                result = self.db_mgr.get_ticket_follower_amt(request.args['target'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/stuwork/reply_ticket', methods=['GET'])
        def stuwork_reply_ticket():
            try:
                result = self.db_mgr.reply_ticket(request.args['openid'], request.args['nick'],
                                                  request.args['target'], request.args['content'],
                                                  request.args['type'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        @app.route('/stuwork/fetch_ticket_replies', methods=['GET'])
        def stuwork_fetch_ticket_replies():
            try:
                result = self.db_mgr.fetch_ticket_replies(request.args['target'], request.args['openid'])
                return json.dumps(result, ensure_ascii=False)
            except Exception as e:
                logging.exception(e)
                return "{{\"result\":\"err:{}\"}}".format(str(e))

        self.app = app
        self.app.config['JSON_AS_ASCII'] = False
        self.app.config["CACHE_TYPE"] = "null"
        self.app.config["FILE_FOLDER"] = '.'

        CORS(self.app, supports_credentials=True)

        self.host = host
        self.port = port
        self.domain = domain
        self.ssl_context = ssl_context

        # self.proxy_thread = threading.Thread(target=self.run_api, args=(), daemon=True)
        #
        # self.proxy_thread.start()

    def run_api(self):
        if self.domain != '' and self.ssl_context is not None:
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

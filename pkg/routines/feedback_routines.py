import pkg.chat.manager
import pkg.database.database


def receive_feedback(openid,content):
    accounts_info = pkg.database.database.get_inst().fetch_qq_accounts(openid)

    qqs=[]
    for account in accounts_info['accounts']:
        qqs.append(account['qq'])

    pkg.chat.manager.get_inst().send_message_to_admins([
        '[bot]收到反馈\n来自:{}\n内容:{}'.format(','.join(qqs),content)
    ])

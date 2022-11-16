import pkg.chat.manager
import pkg.database.database
import pkg.funcmgr.control as funcmgr


@funcmgr.function([funcmgr.Functions.ROUTINE_FEEDBACK_SEND_TO_ADMINS])
def receive_feedback(openid, content):
    accounts_info = pkg.database.database.get_inst().fetch_qq_accounts(openid)

    qqs = []
    for account in accounts_info['accounts']:
        qqs.append(account['qq'])

    chat_inst = pkg.chat.manager.get_inst()

    if chat_inst is not None:
        chat_inst.send_message_to_admins([
            '[bot]收到反馈\n来自:{}\n内容:{}'.format(','.join(qqs), content)
        ])

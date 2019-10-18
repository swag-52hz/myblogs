from utils.zhenzismsclient import ZhenziSmsClient
from celery_tasks.main import app
import logging

logger = logging.getLogger('django')

@app.task(name='send_sms_code')
def send_sms_code(mobile, sms_num):
    try:
        client = ZhenziSmsClient('https://sms_developer.zhenzikj.com', '101357',
                                           'bf00ccbc-1f60-4f1c-a739-ba9ec7f4872d')
        data = client.send(mobile, '您的注册验证码为' + sms_num)
        result = int(data[8])
    except Exception as e:
        logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
    else:
        if result == 0:
            logger.info("发送验证码短信[正常][ mobile: %s sms_code: %s]" % (mobile, sms_num))
        else:
            logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)

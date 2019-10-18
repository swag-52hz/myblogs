from celery import Celery
import os


# 为celery使用django配置文件进行设置
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'

# 创建celery应用/实例
app = Celery('sms_codes', backend='redis://127.0.0.1:6379/2')

# 导入celery配置
app.config_from_object('celery_tasks.config')

# 自动注册celery任务
app.autodiscover_tasks(['celery_tasks.sms'])

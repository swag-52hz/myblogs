import logging
import json
import random
import string
import urllib
import http
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views import View
from django_redis import get_redis_connection
from utils.captcha.captcha import captcha
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from utils import zhenzismsclient as smsclient
from verifications import constants
from users import models
from verifications.forms import CheckImgCodeForm
from celery_tasks.sms import tasks as sms_tasks


# 导入日志器
logger = logging.getLogger('django')


class ImageCode(View):
    # 路径: /image_codes/<uuid:image_code_id>/
    def get(self, request, image_code_id):
        # 生成验证码以及验证码图片
        text, image = captcha.generate_captcha()
        # 连接redis数据库
        conn_redis = get_redis_connection(alias='verify_codes')
        # 生成验证码key值，通过uuid拼接
        img_key = 'img_{}'.format(image_code_id)
        # 将验证码存入数据库，并设置过期时间
        conn_redis.setex(img_key, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        # 打印日志
        logger.info('Image_code: {}'.format(text))
        # 将验证码图片返回给前端
        return HttpResponse(content=image, content_type='image/jpg')


class CheckUsernameView(View):
    # 路径：/usernames/(?P<username>\w{5,20})/
    def get(self, request, username):
        # 根据前端返回的username查看数据库中是否存在该用户名
        count = models.Users.objects.filter(username=username).count()
        # 将结果返回给前端
        data = {
            'count': count,
            'username': username
        }
        return to_json_data(data=data)


class CheckMobileView(View):
    # 路径: /moblies/(?P<moblie>1[3-9]\d{9})/
    def get(self, request, mobile):
        # 根据前端返回的mobile查看数据库中是否存在该手机号
        count = models.Users.objects.filter(mobile=mobile).count()
        # 将结果返回给前端
        data = {
            'count': count,
            'mobile': mobile
        }
        return to_json_data(data=data)


class SmsCodeView(View):
    # 路径：/sms/
    def post(self, request):
        # 获取前端参数
        json_data = request.body
        if not json_data:
            # 若没有接收到，则返回给前端参数错误
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将获取的参数解码并转为字典
        dict_data = json.loads(json_data.decode('utf-8'))
        # 验证参数，用form表单验证
        form = CheckImgCodeForm(data=dict_data)
        # 验证成功，则发送短信验证码,并存入redis数据库
        if form.is_valid():
            # 获取通过验证的手机号
            mobile = form.cleaned_data.get('mobile')
            # 生成随机的六位数短信验证码
            sms_num = ''.join([random.choice(string.digits) for _ in range(constants.SMS_CODE_NUMS)])
            # 将其存入redis数据库
            conn_redis = get_redis_connection(alias='verify_codes')
            sms_text_key = 'sms_{}'.format(mobile)    # 构建验证码键
            sms_flag_key = 'sms_flag_{}'.format(mobile)    # 构建发送标记键
            # 设置管道优化存储
            p1 = conn_redis.pipeline()
            try:
                p1.setex(sms_text_key, constants.SMS_CODE_REDIS_EXPIRES, sms_num)
                p1.setex(sms_flag_key, constants.SEND_SMS_CODE_INTERVAL, constants.SMS_CODE_TEMP_ID)
                p1.execute()
            except Exception as e:
                logger.debug('redis执行异常：{}'.format(e))
                return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])
             # 发送短信验证码,交给celery异步处理
            sms_tasks.send_sms_code.delay(mobile=mobile, sms_num=sms_num)
            return to_json_data(errno=Code.OK, errmsg="短信验证码发送成功")
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)    # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)
















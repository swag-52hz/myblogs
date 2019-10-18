from django import forms
from django_redis import get_redis_connection
from django.core.validators import RegexValidator
from users.models import Users


# 创建手机号的正则校验器
mobile_validator = RegexValidator(r"^1[3-9]\d{9}$", "手机号码格式不正确")


class CheckImgCodeForm(forms.Form):
    mobile = forms.CharField(max_length=11, min_length=11, validators=[mobile_validator,],
                             error_messages={"min_length": "手机号长度有误",
                                             "max_length": "手机号长度有误",
                                             "required": "手机号不能为空"})
    text = forms.CharField(max_length=4, min_length=4,
                           error_messages={"min_length": "图片验证码长度有误",
                                           "max_length": "图片验证码长度有误",
                                           "required": "图片验证码不能为空"})
    image_code_id = forms.UUIDField(error_messages={"required": "图片UUID不能为空"})

    def clean(self):    # 对多个字段进行校验
        clean_data = super().clean()
        mobile_num = clean_data.get('mobile')   # 获取手机号
        image_text = clean_data.get('text')     # 获取验证码
        image_uuid = clean_data.get('image_code_id')    # 获取uuid
        # 验证手机号是否已注册
        if Users.objects.filter(mobile=mobile_num):
            raise forms.ValidationError('此手机号已注册，请重新输入！')
        # 与redis建立连接
        conn_redis = get_redis_connection(alias='verify_codes')
        # 构建key
        img_key = 'img_{}'.format(image_uuid)
        # 获取验证码，redis当中去出来的为bytes
        image_code_origin = conn_redis.get(img_key)
        # 存在就解码，不存在就将其赋值为None
        image_code = image_code_origin.decode('utf-8') if image_code_origin else None
        # 取出以后将其删掉
        conn_redis.delete(img_key)
        if (not image_code) or (image_text != image_code):
            raise forms.ValidationError('图形验证失败！')
        # 检查是否在60秒内
        sms_flag_fmt = "sms_flag_{}".format(mobile_num).encode('utf-8')
        sms_flag = conn_redis.get(sms_flag_fmt)
        if sms_flag:
            raise forms.ValidationError("获取手机短信验证码过于频繁")



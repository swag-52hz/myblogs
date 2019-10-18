import re
from django import forms
from django_redis import get_redis_connection
from django.contrib.auth import login
from django.db.models import Q
from .constants import USER_SESSION_EXPIRES, SMS_CODE_NUMS
from .models import Users


class RegisterForm(forms.Form):
    username = forms.CharField(label='用户名', min_length=5, max_length=20,
                               error_messages={'max_length': '用户名长度要小于20',
                                               'min_length': '用户名长度要大于5',
                                               'required': '用户名不能为空'})
    password = forms.CharField(label='密码', min_length=6, max_length=20,
                               error_messages={'max_length': '密码长度要小于20',
                                               'min_length': '密码长度要大于6',
                                               'required': '密码不能为空'})
    password_repeat = forms.CharField(label='确认密码', min_length=6, max_length=20,
                                      error_messages={'max_length': '密码长度要小于20',
                                                      'min_length': '密码长度要大于6',
                                                      'required': '密码不能为空'})
    mobile = forms.CharField(label='手机号', min_length=11, max_length=11,
                                   error_messages={'max_length': '手机号长度有误！',
                                                   'min_length': '手机号长度有误！',
                                                   'required': '手机号不能为空！'})
    sms_code = forms.CharField(label='短信验证码', min_length=SMS_CODE_NUMS, max_length=SMS_CODE_NUMS,
                                     error_messages={'max_length': '短信验证码长度有误！',
                                                     'min_length': '短信验证码长度有误！',
                                                     'required': '短信验证码不能为空！'})

    def clean_mobile(self):     # 验证单个字段
        tel = self.cleaned_data.get('mobile')
        # 验证手机格式
        if not re.match(r'^1[3-9]\d{9}$', tel):
            raise forms.ValidationError('手机号码格式不正确！')
        # 验证手机号是否已被注册
        if Users.objects.filter(mobile=tel).exists():
            raise forms.ValidationError('手机号已注册，请重新输入！')
        # 记得返回，不然找不到
        return tel

    def clean_username(self):
        name = self.cleaned_data.get('username')
        # 判断用户名是否已注册
        if Users.objects.filter(username=name).exists():
            raise forms.ValidationError('此用户名已被注册！')
        return name

    def clean(self):
        cleaned_data = super().clean()
        # 获取数据
        passwd = cleaned_data.get('password')
        passwd_repeat = cleaned_data.get('password_repeat')
        tel = cleaned_data.get('mobile')
        sms_text = cleaned_data.get('sms_code')
        # 验证两次输入的密码是否一致
        if passwd != passwd_repeat:
            raise forms.ValidationError('两次密码不一致！')
        # 验证输入的短信验证码是否正确
        # 连接redis数据库
        redis_conn = get_redis_connection('verify_codes')
        # 构建短信验证码的键
        sms_key = 'sms_{}'.format(tel)
        # 获取数据库中的短信验证码
        real_sms = redis_conn.get(sms_key)
        # 此时real_sms为bytes类型，需解码
        if (not real_sms) or (sms_text != real_sms.decode('utf-8')):
            raise forms.ValidationError('短信验证码有误！')


class LoginForm(forms.Form):
    user_account = forms.CharField()
    password = forms.CharField(label='密码', max_length=20, min_length=6,
                               error_messages={"min_length": "密码长度要大于6",
                                               "max_length": "密码长度要小于20",
                                               "required": "密码不能为空"})
    remember_me = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        # 从传入的参数中拿到request
        self.request = kwargs.pop('request', None)
        # 继承父类的初始化方法
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean_user_account(self):
        # 对用户名进行单独验证
        user_info = self.cleaned_data.get('user_account')
        if not user_info:
            raise forms.ValidationError('用户账号不能为空！')
        if not re.match(r'^1[3-9]\d{9}$', user_info) and (len(user_info) < 5 or len(user_info) > 20):
            raise forms.ValidationError('用户账号格式不正确！')
        return user_info

    def clean(self):
        clean_data = super().clean()
        # 拿到清洗后的用户名
        user_info = clean_data.get('user_account')
        # 拿到清洗后的密码
        passwd = clean_data.get('password')
        # 拿到设置session标志
        hold_login = clean_data.get('remember_me')
        # 在form表单中实现登陆逻辑
        # 对比数据库中是否存在该用户名
        user_queryset = Users.objects.filter(Q(mobile=user_info) | Q(username=user_info))
        if user_queryset:
            # 拿到单个实例对象
            user = user_queryset.first()
            if user.check_password(passwd):     # 验证密码
                if hold_login:      # 验证设置session标记
                    self.request.session.set_expiry(0)
                else:
                    self.request.session.set_expiry(USER_SESSION_EXPIRES)
                # 用户登录
                login(self.request, user)
            else:
                forms.ValidationError('密码输入有误！')
        else:
            raise forms.ValidationError('用户名不存在！')








import json
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from .forms import RegisterForm, LoginForm
from .models import Users
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, reverse
from django.views import View


class LoginView(View):  # 实现登录的类视图
    def get(self, request):
        # get请求，返回登录页面
        return render(request, 'users/login.html')

    def post(self, request):
        # 从前端获取参数
        json_data = request.body
        # 若没有参数，则返回参数错误给前端
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将参数先解码再用json转成python字典格式
        dict_data = json.loads(json_data.decode('utf8'))
        # 交给form表单进行验证并实现登陆
        form = LoginForm(data=dict_data, request=request)
        # 若验证无误，则返回登录成功提示
        if form.is_valid():
            return to_json_data(errmsg='恭喜您，登陆成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(reverse('users:login'))


class RegisterView(View):
    def get(self, request):
        return render(request, 'users/register.html')

    def post(self, request):
        # 获取前端参数
        json_data = request.body
        if not json_data:
            # 若没有接收到，则返回给前端参数错误
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将获取的参数解码并转为字典
        dict_data = json.loads(json_data.decode('utf8'))
        # 通过form来验证参数
        form = RegisterForm(data=dict_data)
        # 若验证通过则将数据存入数据库
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            mobile = form.cleaned_data.get('mobile')

            user = Users.objects.create_user(username=username, password=password, mobile=mobile)
            # 登录
            login(request, user)
            # 返回给前端
            return to_json_data(errmsg='恭喜您，注册成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)



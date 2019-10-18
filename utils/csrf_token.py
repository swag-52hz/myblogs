from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views import View


class LoginView(View):
    # 设置csrf_token
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        pass

    def post(self, request):
        pass
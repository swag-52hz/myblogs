from django.urls import path, re_path
from verifications import views


app_name = 'verifications'
urlpatterns = [
    path('image_codes/<uuid:image_code_id>/', views.ImageCode.as_view(), name='image_codes'),
    re_path('usernames/(?P<username>\w{5,20})/', views.CheckUsernameView.as_view(), name='check_username'),
    re_path('mobiles/(?P<mobile>1[3-9]\d{9})/', views.CheckMobileView.as_view(), name='check_mobile'),
    path('sms_codes/', views.SmsCodeView.as_view(), name='sms_codes')
]
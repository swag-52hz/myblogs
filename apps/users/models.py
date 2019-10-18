from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as _UserManager


class UserManager(_UserManager):
    """
    define user manager for modifing 'no need email'
    when 'python manager.py createsuperuser '

    """

    def create_superuser(self, username, password, email=None, **extra_fields):
        super(UserManager, self).create_superuser(username=username,
                                                  password=password, email=email, **extra_fields)


class Users(AbstractUser):
    """
    add mobile、email_active fields to Django users models.
    """
    objects = UserManager()
    # A list of the field names that will be prompted for
    # when creating a user via the createsuperuser management command.
    REQUIRED_FIELDS = ['mobile']

    # help_text在api接口文档中会用到
    # verbose_name在admin站点中会用到
    mobile = models.CharField(max_length=11, unique=True, verbose_name="手机号", help_text='手机号',
                              error_messages={'unique': "此手机号已注册"}  # 指定报错的中文信息
                              )
    email_active = models.BooleanField(default=False, verbose_name='邮箱验证状态')

    class Meta:
        db_table = "tb_users"   # 指明数据库表名
        verbose_name = "用户"    # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):  # 打印对象时调用
        return self.username

    def get_groups_name(self):
       return '|'.join([i.name for i in self.groups.all()])

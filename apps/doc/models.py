from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from utils.models import ModelBase


class Doc(ModelBase):   # 文档数据表
    file_url = models.URLField(verbose_name='文件url', help_text='文件url')
    title = models.CharField(max_length=150, validators=[MinLengthValidator(1)], verbose_name='文档标题', help_text='文档标题')
    desc = models.TextField(validators=[MaxLengthValidator(200), MinLengthValidator(1)], verbose_name='文档描述', help_text='文档描述')
    image_url = models.URLField(default='', verbose_name='图片url', help_text='图片url')
    author = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'tb_docs'    # 指明数据库表名
        verbose_name = '文档'     # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称




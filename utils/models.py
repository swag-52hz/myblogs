from django.db import models


class ModelBase(models.Model):
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    update_time = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    is_delete = models.BooleanField(default=False, verbose_name='逻辑删除')

    class Meta:
        # 为抽象模型类, 用于其他模型来继承，数据库迁移时不会创建ModelBase表
        abstract = True


import pytz
from django.db import models
from django.core.validators import MinLengthValidator
from utils.models import ModelBase


class Tag(ModelBase):   # 文章分类表
    name = models.CharField(max_length=64, verbose_name='标签名', help_text='标签名')

    class Meta:
        # 以修改时间，id按从大到小进行排序
        ordering = ['-update_time', '-id']
        db_table = "tb_tag"  # 指明数据库表名
        verbose_name = "新闻标签"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return self.name


class News(ModelBase):  # 文章表
    title = models.CharField(max_length=150, validators=[MinLengthValidator(1)], verbose_name="标题", help_text="标题")
    digest = models.CharField(max_length=200, validators=[MinLengthValidator(1)], verbose_name="摘要", help_text="摘要")
    content = models.TextField(verbose_name="内容", help_text="内容")
    clicks = models.IntegerField(default=0, verbose_name="点击量", help_text="点击量")
    image_url = models.URLField(default="", verbose_name="图片url", help_text="图片url")
    # 使用外键关联文章分类表, models.SET_NULL:当关联的标签删除时，此字段设置为空
    tag = models.ForeignKey('Tag', on_delete=models.SET_NULL, null=True)
    # 使用外键关联用户表
    author = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_news"  # 指明数据库表名
        verbose_name = "新闻"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return self.title


class Comments(ModelBase):  # 文章评论表
    content = models.TextField(verbose_name='内容', help_text='内容')
    # 使用外键关联用户表
    author = models.ForeignKey('users.Users', on_delete=models.SET_NULL, null=True)
    # 使用外键关联文章表，当关联的文章删除时，此字段也将被删除
    news = models.ForeignKey('News', on_delete=models.CASCADE)
    # 添加父级评论字段，与表自身关联
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def to_dict_data(self):     # 定义序列化方法
        # 将页面显示的时间转换成上海时间
        local_tz = pytz.timezone('Asia/Shanghai')
        local_time = local_tz.normalize(self.update_time)
        comment_dict = {
            'news_id': self.news_id,
            'author': self.author.username,
            'update_time': local_time.strftime('%Y年%m月%d日 %H:%M:%S'),
            'content': self.content,
            'content_id': self.id,
            'parent': self.parent.to_dict_data() if self.parent else None
        }
        return comment_dict

    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_comments"  # 指明数据库表名
        verbose_name = "评论"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return '<评论{}>'.format(self.id)


class HotNews(ModelBase):   # 热门文章表
    PRI_CHOICES = [
        (1, '第一级'),
        (2, '第二级'),
        (3, '第三级')
    ]
    # 一对一关联
    news = models.OneToOneField('News', on_delete=models.CASCADE)
    # 设置优先级，根据此字段进行排序
    priority = models.IntegerField(choices=PRI_CHOICES, default=3, verbose_name="优先级", help_text="优先级")

    class Meta:
        ordering = ['-update_time', '-id']
        db_table = "tb_hotnews"  # 指明数据库表名
        verbose_name = "热门新闻"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return '<热门新闻{}>'.format(self.id)


class Banner(ModelBase):    # 轮播图表
    PRI_CHOICES = [
        (1, '第一级'),
        (2, '第二级'),
        (3, '第三级'),
        (4, '第四级'),
        (5, '第五级'),
        (6, '第六级'),
    ]
    image_url = models.URLField(verbose_name="轮播图url", help_text="轮播图url")
    priority = models.IntegerField(choices=PRI_CHOICES, default=6, verbose_name="优先级", help_text="优先级")
    news = models.OneToOneField('News', on_delete=models.CASCADE)

    class Meta:
        ordering = ['priority', '-update_time', '-id']
        db_table = "tb_banner"  # 指明数据库表名
        verbose_name = "轮播图"  # 在admin站点中显示的名称
        verbose_name_plural = verbose_name  # 显示的复数名称

    def __str__(self):
        return '<轮播图{}>'.format(self.id)








from haystack import indexes
from .models import News


class NewsIndex(indexes.SearchIndex, indexes.Indexable):
    """
    NewsIndex: 名称固定  News索引数据模型类
    """
    # 为字段建立索引，引用templates/search/indexes/news/news_text.txt文件（文件名为：模型类_text.txt）
    text = indexes.CharField(document=True, use_template=True)
    # 以下几个字段作用是可以直接使用News.字段名而不用News.objects.字段名
    id = indexes.IntegerField(model_attr='id')
    title = indexes.CharField(model_attr='title')
    digest = indexes.CharField(model_attr='digest')
    content = indexes.CharField(model_attr='content')
    image_url = indexes.CharField(model_attr='image_url')
    # comments = indexes.IntegerField(model_attr='comments')

    def get_model(self):
        """返回建立索引的模型类
        """
        return News

    def index_queryset(self, using=None):
        """返回要建立索引的数据查询集
        """

        return self.get_model().objects.filter(is_delete=False, tag_id__in=[1, 2, 3, 4, 5, 6])

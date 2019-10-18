import logging
import json

from haystack.views import SearchView as _SearchView
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views import View
from django.http import Http404
from news import models
from mysite import settings
from utils.json_fun import to_json_data
from .constants import PER_PAGE_NEWS_COUNT, SHOW_BANNER_COUNT, SHOW_HOTNEWS_COUNT
from utils.res_code import Code, error_map
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

logger = logging.getLogger('django')


class IndexView(View):
    def get(self, request):
        # 使用only进行查询优化
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        # 从数据库中取出热门新闻并根据优先级和点击量进行排序
        hot_news = models.HotNews.objects.select_related('news').\
            only('news__title', 'news__image_url', 'news_id').filter(is_delete=False).\
            order_by('priority', '-news__clicks')[0:SHOW_HOTNEWS_COUNT]
        # locals()的作用是将这个函数中的所有变量上传到模板中，而不用context
        return render(request, 'news/index.html', locals())


class NewsListView(View):
    def get(self, request):
        # 1,获取参数,并校验参数
        try:
            tag_id = int(request.GET.get('tag_id', 0))
        # 用户没有点击标签或者获取错误时，默认给0
        except Exception as e:
            logger.error('标签错误:\n{}'.format(e))
            tag_id = 0
        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.error('页码错误:\n{}'.format(e))
            page = 1
        # 3,从数据库拿数据，用select_related,only进行查询优化
        news_queryset = models.News.objects.select_related('tag', 'author').only('title', 'digest', 'update_time',
                                                                                 'image_url', 'tag__name', 'author__username')
        # 若tag_id正确获取，则返回对应标签下的文章，若为0，则返回按更改时间和id排序的文章
        news = news_queryset.filter(is_delete=False, tag_id=tag_id) or news_queryset.filter(is_delete=False)
        # 4,分页,第一个参数是数据，第二个参数是每页多少个
        paginator = Paginator(news, PER_PAGE_NEWS_COUNT)
        # 拿到某一页的信息
        try:
            news_info = paginator.page(page)
        except EmptyPage:
            logger.error('用户访问的页数大于总页数！')
            # 超过页码，则返回最后一页的数据
            news_info = paginator.page(paginator.num_pages)
        # 序列化输出
        news_info_list = []
        for i in news_info:
            news_info_list.append({
                'id': i.id,
                'title': i.title,
                'digest': i.digest,
                'image_url': i.image_url,
                'update_time': i.update_time.strftime('%Y年%m月%d日 %H:%M'),
                'tag_name': i.tag.name,
                'author': i.author.username
            })
        data = {
            'news': news_info_list,
            'total_pages': paginator.num_pages
        }
        # 返回数据给前端
        return to_json_data(data=data)


class NewsBanner(View):     # 首页轮播图
    def get(self, request):
        # 从数据库中获取轮播图数据对象
        banners = models.Banner.objects.select_related('news').\
            only('news_id', 'news__title', 'image_url').\
            filter(is_delete=False).order_by('priority')[0:SHOW_BANNER_COUNT]
        # 序列化输出
        banners_info_list = []
        for b in banners:
            banners_info_list.append({
                'image_url': b.image_url,
                'news_title': b.news.title,
                'news_id': b.news.id
            })
        # 创建返回给前端的数据
        data = {
            'banners': banners_info_list
        }
        return to_json_data(data=data)


class NewsDetailView(View):     # 文章详情视图
    def get(self, request, news_id):
        # 根据前端传过来的news_id从数据库中拿到对应的文章信息
        news = models.News.objects. select_related('tag', 'author').\
            only('author__username', 'update_time', 'tag__name', 'title', 'content').\
            filter(id=news_id, is_delete=False).first()
        if news:
            # 加载该文章的评论
            comments = models.Comments.objects.select_related('author', 'parent').\
                only('author__username', 'content', 'update_time', 'parent__content',
                     'parent__author__username', 'parent__update_time').filter(is_delete=False, news_id=news_id)
            # 序列化输出评论
            comments_list = []
            for comm in comments:
                comments_list.append(comm.to_dict_data())
            return render(request, 'news/news_detail.html', locals())
        else:
            raise Http404('新闻{}不存在！'.format(news_id))


class NewsCommentView(View):    # 文章多级评论视图
    def post(self, request, news_id):
        # 判断用户是否登录
        if not request.user.is_authenticated:
            # 若没有登录，则返回用户未登录信息给前端
            return to_json_data(errno=Code.SESSIONERR, errmsg=error_map[Code.SESSIONERR])
        # 根据news_id判断该文章是否存在
        if not models.News.objects.only('id').filter(is_delete=False, id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='新闻不存在！')
        # 从前端获取参数
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        # 获取评论内容
        content = dict_data.get('content')
        if not content:
            return to_json_data(errno=Code.PARAMERR, errmsg='评论内容不能为空！')
        # 父评论的验证
        parent_id = dict_data.get('parent_id')
        try:
            # 判断有无父评论
            if parent_id:
                # parent_id必须为数字
                parent_id = int(parent_id)
                # 判断数据库中是否存在该父评论并判断父评论的新闻id是否跟传过来的news_id一致
                if not models.Comments.objects.only('id').filter(is_delete=False, id=parent_id,
                                                                 news_id=news_id).exists():
                    return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        except Exception as e:
            logger.info('前端传的parent_id异常{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg="未知异常")
        # 存入数据库
        new_comment = models.Comments()
        new_comment.content = content
        new_comment.news_id = news_id
        new_comment.author = request.user
        new_comment.parent_id = parent_id if parent_id else None
        new_comment.save()
        # 返回数据给前端展示
        return to_json_data(data=new_comment.to_dict_data())


class SearchView(_SearchView):
    # 模版文件
    template = 'news/search.html'

    # 重写响应方式，如果请求参数q为空，返回模型News的热门新闻数据，否则根据参数q搜索相关数据
    def create_response(self):
        kw = self.request.GET.get('q', '')
        if not kw:
            show_all = True
            hot_news = models.HotNews.objects.select_related('news'). \
                only('news__title', 'news__image_url', 'news__id'). \
                filter(is_delete=False).order_by('priority', '-news__clicks')

            paginator = Paginator(hot_news, settings.HAYSTACK_SEARCH_RESULTS_PER_PAGE)
            try:
                page = paginator.page(int(self.request.GET.get('page', 1)))
            except PageNotAnInteger:
                # 如果参数page的数据类型不是整型，则返回第一页数据
                page = paginator.page(1)
            except EmptyPage:
                # 用户访问的页数大于实际页数，则返回最后一页的数据
                page = paginator.page(paginator.num_pages)
            return render(self.request, self.template, locals())
        else:
            show_all = False
            qs = super(SearchView, self).create_response()
            return qs



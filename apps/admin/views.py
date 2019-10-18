import json
import logging
import qiniu
from datetime import datetime
from urllib.parse import urlencode
from django.http import JsonResponse
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from news import models
from doc.models import Doc
from course.models import Course, Teacher, CourseCategory
from django.contrib.auth.models import Group, Permission
from users.models import Users
from .forms import NewsPubForm, DocPubForm, CoursePubForm
from utils import paginator_script
from utils.res_code import  Code, error_map
from utils.json_fun import to_json_data
from utils.fastdfs.client import FDFS_Client
from utils.qiniu_secrets import qiniu_secrets_info
from mysite.settings import FASTDFS_SERVER_DOMAIN
from .constants import SHOW_HOT_NEWS_COUNT, PER_PAGE_NEWS_COUNT, SHOW_BANNER_COUNT


logger = logging.getLogger('django')


class IndexView(LoginRequiredMixin, View):
    """
    admin后台首页类视图
    路径：127.0.0.1：8000/admin/
    """
    redirect_field_name = 'next'
    def get(self, request):
        return render(request, 'admin/index/index.html')

class TagsManageView(PermissionRequiredMixin, View):
    """
    标签管理页类视图    路径：/tag/
    实现管理页面渲染以及添加标签的功能
    """
    permission_required = ('news.view_tag', 'news.add_tag')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method == 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限！')
        else:
            return super(TagsManageView, self).handle_no_permission()

    def get(self, request):
        # 分组查询，根据tag_id去查找出对应的news数量，values返回一个字典
        tags = models.Tag.objects.select_related('news').values('id', 'name').\
            annotate(num_news = Count('news')).\
            filter(is_delete=False).order_by('-num_news', 'update_time')
        return render(request, 'admin/news/tags_manage.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        tag_name = dict_data.get('name')
        if tag_name:
            tag_name = tag_name.strip()     # 去除前后空格
            # get_or_create:获得一个二元组，第一个为一个实例对象，第二个为boolean类型
            # 创建成功则为True，否则为False
            tag_tuple = models.Tag.objects.get_or_create(name=tag_name)
            tag, status = tag_tuple     # 拆包
            if status:
                return to_json_data(errmsg='标签创建成功！')
            else:
                return to_json_data(errno=Code.DATAEXIST, errmsg='标签已存在！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='标签名不能为空！')

class TagEditView(PermissionRequiredMixin, View):
    """
    实现标签删除，标签修改功能的类视图
    路径:/tag/<int:tag_id>/
    """
    permission_required = ('news.change_tag', 'nes.delete_tag')
    raise_exception = True
    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')

    def delete(self, request, tag_id):
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            tag.is_delete = True
            tag.save(update_fields=['is_delete'])
            return to_json_data(errmsg='标签删除成功！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的标签不存在！')

    def put(self, request, tag_id):
        # 从前端获取参数
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 转为字典格式
        dict_data = json.loads(json_data.decode('utf8'))
        # 获取用户输入的标签名
        tag_name = dict_data.get('name')
        # 从数据库中获取需要更改的标签
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            if tag_name:
                tag_name = tag_name.strip()  # 去除前后空格
                # 判断数据库中是否已存在该标签名
                if not models.Tag.objects.only('id').filter(name=tag_name).exists():
                    tag.name = tag_name
                    tag.save(update_fields=['name', 'update_time'])
                    return to_json_data(errmsg='标签修改成功！')
                else:
                    return to_json_data(errno=Code.DATAEXIST, errmsg='此标签已存在！')
            else:
                return to_json_data(errno=Code.PARAMERR, errmsg='标签名不能为空！')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要修改的标签不存在！')

class HotNewsManageView(PermissionRequiredMixin, View):
    """
    热门文章管理页面类视图，负责渲染页面
    路径: /hotnews/
    """
    permission_required = ('news.view_hotnews')
    raise_exception = True
    def get(self, request):
        hot_news = models.HotNews.objects.select_related('news__tag').\
            only('news_id', 'news__title', 'news__tag__name', 'priority').\
            filter(is_delete=False).order_by('priority', '-news__clicks')[0:SHOW_HOT_NEWS_COUNT]
        return render(request, 'admin/news/news_hot.html', locals())

class HotNewsEditView(PermissionRequiredMixin, View):
    """
    热门文章编辑类视图，负责删除以及更新热门文章
    路径：hotnews/<int:hotnews_id>/
    """
    permission_required = ('news.delete_hotnews', 'news.change_hotnews')
    raise_exception = True
    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')

    def delete(self, request, hotnews_id):
        hot_news = models.HotNews.objects.only('id').filter(id=hotnews_id, is_delete=False).first()
        if hot_news:
            hot_news.is_delete = True
            hot_news.save(update_fields = ['is_delete', 'update_time'])
            return to_json_data(errmsg='该热门文章删除成功！')
        return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的热门文章不存在！')

    def put(self, request, hotnews_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i,_ in models.HotNews.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='优先级设置错误！')
        except Exception as e:
            logger.info('获取热门文章优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        hot_news = models.HotNews.objects.only('id').filter(is_delete=False, id=hotnews_id).first()
        if hot_news:
            if hot_news.priority == priority:
                return to_json_data(errno=Code.PARAMERR, errmsg='该热门文章的优先级未改变！')
            hot_news.priority = priority
            hot_news.save(update_fields = ['priority', 'update_time'])
            return to_json_data(errmsg='热门文章更新成功！')
        return to_json_data(errno=Code.PARAMERR, errmsg='该热门文章不存在！')

class HotNewsAddView(PermissionRequiredMixin, View):
    """
    热门文章添加类视图，负责添加热门文章
    路径：/hotnews/add/
    """
    permission_required = ('news.add_hotnews')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限！')
        else:
            return super(HotNewsAddView, self).handle_no_permission()

    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')).\
            filter(is_delete=False).order_by('-num_news', 'update_time')
        priority_dict = dict(models.HotNews.PRI_CHOICES)
        return render(request, 'admin/news/news_hot_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        # 对前端传过来的news_id做验证
        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('文章id出现异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        if not models.News.objects.filter(is_delete=False, id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='该文章不存在！')
        # 对优先级做验证
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='优先级设置错误！')
        except Exception as e:
            logger.info('获取热门文章优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 存入数据库
        hotnews_tuple = models.HotNews.objects.get_or_create(news_id=news_id)
        hot_news, status = hotnews_tuple
        hot_news.priority = priority
        hot_news.save()
        return to_json_data(errmsg='热门文章创建成功！')

class NewsByTagIdView(View):
    """
    通过tag_id找到该标签下所对应的文章
    路径：/tags/<int:tag_id>/news/
    """
    def get(self, request, tag_id):
        newes = models.News.objects.values('id', 'title').filter(is_delete=False, tag_id=tag_id)
        news_list = [i for i in newes]
        return to_json_data(data={
            'news': news_list
        })

class NewsManageView(PermissionRequiredMixin, View):
    permission_required = ('news.view_news', 'news.view_tag')
    raise_exception = True
    def get(self, request):
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        newses = models.News.objects.select_related('tag', 'author').\
            only('id', 'title', 'update_time', 'tag__name', 'author__username').filter(is_delete=False)
        # 根据所选的标签进行过滤
        try:
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.info('标签错误：{}'.format(e))
            tag_id = 0
        # 如果有则返回对应标签下的文章，若没有则返回所有数据
        newses = newses.filter(tag_id=tag_id) or newses.filter(is_delete=False)
        # 通过时间进行过滤
        try:
            start_time = request.GET.get('start_time', '')
            start_time = datetime.strptime(start_time, '%Y/%m/%d') if start_time else ''
            end_time = request.GET.get('end_time', '')
            end_time = datetime.strptime(end_time, '%Y/%m/%d') if end_time else ''
        except Exception as e:
            logger.info('时间出错：{}'.format(e))
            start_time = end_time = ''
        if start_time and not end_time:
            newses = newses.filter(update_time__gte=start_time)
        if end_time and not start_time:
            newses = newses.filter(update_time__lte=end_time)
        if start_time and end_time:
            newses = newses.filter(update_time__range=(start_time, end_time))
        # 通过文章标题进行过滤
        title = request.GET.get('title', '')
        if title:
            newses = newses.filter(title__icontains=title)
        # 通过作者进行过滤
        author_name = request.GET.get('author_name', '')
        if author_name:
            newses = newses.filter(author__username__icontains=author_name)

        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.info('获取页码出错：{}'.format(e))
            page = 1
        # 创建分页，第一个参数是数据，第二个参数是每页显示的新闻数
        paginator = Paginator(newses, PER_PAGE_NEWS_COUNT)
        try:
            news_info = paginator.page(page)
        except EmptyPage as e:
            logger.info('用户访问的页数大于总页数！')
            # 当访问页数大于总页数时，则返回最后一页的数据
            news_info = paginator.page(paginator.num_pages)
        # 传入分页数据
        paginator_data = paginator_script.get_paginator_data(paginator, news_info)
        # 时间转字符串
        start_time = start_time.strftime('%Y/%m/%d') if start_time else ''
        end_time = end_time.strftime('%Y/%m/%d') if start_time else ''
        context = {
            'news_info': news_info,
            'tags': tags,
            'start_time': start_time,
            "end_time": end_time,
            "title": title,
            "author_name": author_name,
            "tag_id": tag_id,
            "other_param": urlencode({
                "start_time": start_time,
                "end_time": end_time,
                "title": title,
                "author_name": author_name,
                "tag_id": tag_id,
            })
        }
        context.update(paginator_data)
        return render(request, 'admin/news/news_manage.html', context=context)

class NewsEditView(PermissionRequiredMixin, View):
    """
    负责渲染修改文章的页面以及修改，删除文章功能的实现
    路由：/admin/news/<int:news_id>/
    """
    permission_required = ('news.change_news', 'news.delete_news')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限！')
        else:
            return super(NewsEditView, self).handle_no_permission()

    def get(self, request, news_id):     # 获取待编辑的文章
        news = models.News.objects.filter(id=news_id, is_delete=False).first()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要编辑的文章不存在！')
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/news/news_pub.html', locals())

    def put(self, request, news_id):     # 修改或发布新文章
        news = models.News.objects.only('id').filter(id=news_id).first()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要编辑的文章不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form = NewsPubForm(data=dict_data)
        if form.is_valid():
            news.title = form.cleaned_data.get('title')
            news.digest = form.cleaned_data.get('digest')
            news.content = form.cleaned_data.get('content')
            news.image_url = form.cleaned_data.get('image_url')
            news.tag = form.cleaned_data.get('tag')
            news.save()
            return to_json_data(errmsg='文章更新成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

    def delete(self, request, news_id):  # 删除文章
        news = models.News.objects.only('id').filter(id=news_id).first()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg='要删除的文章不存在！')
        news.is_delete = True
        news.save(update_fields = ['is_delete', 'update_time'])
        return to_json_data(errmsg='文章删除成功！')

class NewsPubView(PermissionRequiredMixin, View):
    permission_required = ('news.view_news', 'news.add_news')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限！')
        else:
            return super(NewsPubView, self).handle_no_permission()

    def get(self, request):
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        return render(request, 'admin/news/news_pub.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form = NewsPubForm(data=dict_data)
        if form.is_valid():
            # form.save():创建一个新的news对象，commit=False:延缓提交
            news_instance = form.save(commit=False)
            # 指定文章作者即当前登录用户
            news_instance.author_id = request.user.id
            news_instance.save()
            return to_json_data(errmsg='文章发布成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

class NewsUploadImage(View):
    """上传图片至FastDFS服务器"""
    def post(self, request):
        image_file = request.FILES.get('image_file', '')
        if not image_file:
            logger.info('从前端获取图片失败！')
            return to_json_data(errno=Code.PARAMERR, errmsg='未选择图片！')
        if image_file.content_type not in ['image/jpg', 'image/png', 'image/jpeg', 'image/gif']:
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非图片文件！')
        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片扩展名异常：{}'.format(e))
            image_ext_name = 'jpg'
        # image_file.read():读取文件
        result = FDFS_Client.upload_by_buffer(image_file.read(), image_ext_name)
        if result['Status'] == 'Upload successed.':
            image_url = FASTDFS_SERVER_DOMAIN + result['Remote file_id']
            return to_json_data(data={'image_url': image_url}, errmsg='图片上传成功！')
        else:
            logger.info('图片上传到FastDFS服务器失败')
            return to_json_data(errno=Code.UNKOWNERR, errmsg='上传图片到服务器失败！')

class UploadToken(View):
    """七牛云上传图片需要调用token"""
    def get(self, request):
        access_key = qiniu_secrets_info.QI_NIU_ACCESS_KEY
        secret_key = qiniu_secrets_info.QI_NIU_SECRET_KEY
        bucket_name = qiniu_secrets_info.QI_NIU_BUCKET_NAME
        # 构建鉴权对象
        q = qiniu.Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)
        return JsonResponse({'uptoken': token})


@method_decorator(csrf_exempt, name='dispatch')
class MarkDownUploadImage(View):
    """markdown上传图片"""
    def post(self, request):
        image_file = request.FILES.get('editormd-image-file')
        if not image_file:
            logger.info('从前端获取图片失败')
            return JsonResponse({'success': 0, 'message': '从前端获取图片失败'})
        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif', 'image/jpg'):
            return JsonResponse({'success': 0, 'message': '不能上传非图片文件'})
        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'
        try:
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.error('图片上传出现异常：{}'.format(e))
            return JsonResponse({'success': 0, 'message': '图片上传异常'})
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FastDFS服务器失败')
                return JsonResponse({'success': 0, 'message': '图片上传到服务器失败'})
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = FASTDFS_SERVER_DOMAIN + image_name
                return JsonResponse({'success': 1, 'message': '图片上传成功', 'url': image_url})


class BannerManageView(PermissionRequiredMixin, View):
    """轮播图管理页面渲染类视图"""
    permission_required = ('news.view_banner')
    raise_exception = True
    def get(self, request):
        banners = models.Banner.objects.only('id', 'image_url', 'priority').filter(is_delete=False).\
            order_by('priority', 'id')[0:SHOW_BANNER_COUNT]
        priority_dict = dict(models.Banner.PRI_CHOICES)
        return render(request, 'admin/news/news_banner.html', locals())

class BannerEditView(PermissionRequiredMixin, View):
    """轮播图编辑页面，负责删除以及更新功能的实现"""
    permission_required = ('news.delete_banner', 'news.change_banner')
    raise_exception = True
    def handle_no_permission(self):
        return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限！')

    def delete(self, request, banner_id):
        banner = models.Banner.objects.only('id').filter(id=banner_id, is_delete=False).first()
        if not banner:
            return to_json_data(errno=Code.PARAMERR, errmsg='要删除的轮播图不存在！')
        banner.is_delete = True
        banner.save(update_fields = ['is_delete', 'update_time'])
        return to_json_data(errmsg='删除成功！')

    def put(self, request, banner_id):
        banner = models.Banner.objects.only('id').filter(id=banner_id, is_delete=False).first()
        if not banner:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的轮播图不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='未上传轮播图图片')
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i,_ in models.Banner.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误！')
        except Exception as e:
            logger.info('轮播图优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误！')
        if priority == banner.priority and image_url == banner.image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图参数未修改！')
        banner.image_url = image_url
        banner.priority = priority
        banner.save(update_fields = ['image_url', 'priority', 'update_time'])
        return to_json_data(errmsg='轮播图更新成功！')

class BannerAddView(PermissionRequiredMixin, View):
    """负责轮播图添加页面的渲染以及添加轮播图"""
    permission_required = ('news.add_banner')
    raise_exception = True
    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news = Count('news')).\
            filter(is_delete=False).order_by('-num_news', 'update_time')
        priority_dict = dict(models.Banner.PRI_CHOICES)
        return render(request, 'admin/news/news_banner_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i,_ in models.Banner.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误！')
        except Exception as e:
            logger.info('轮播图优先级异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图优先级设置错误！')
        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('文章id异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='文章id异常！')
        if not models.News.objects.filter(id=news_id, is_delete=False).exists():
            return to_json_data(errno=Code.NODATA, errmsg='文章不存在！')
        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='未上传轮播图图片！')
        banner = models.Banner.objects.create(news_id=news_id, image_url=image_url, priority=priority)
        banner.save()
        return to_json_data(errmsg='轮播图创建成功！')

class DocManageView(PermissionRequiredMixin, View):
    """文档管理类视图，负责文档管理页面的渲染"""
    permission_required = ('doc.view_doc')
    raise_exception = True
    def get(self, request):
        docs = Doc.objects.only('id', 'title', 'update_time').filter(is_delete=False)
        return render(request, 'admin/doc/docs_manage.html', locals())

class DocEditView(PermissionRequiredMixin, View):
    """文档编辑类视图，负责渲染编辑页面以及删除和更新文档功能的实现"""
    permission_required = ('doc.view_doc', 'doc.delete_doc', 'doc.change_doc')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(DocEditView, self).handle_no_permission()

    def get(self, request, doc_id):
        doc = Doc.objects.only('title', 'desc', 'image_url', 'file_url').filter(id=doc_id, is_delete=False).first()
        if doc:
            return render(request, 'admin/doc/docs_pub.html', locals())
        return to_json_data(errno=Code.NODATA, errmsg='需要更新的文档不存在！')

    def delete(self, request, doc_id):
        doc = Doc.objects.only('id').filter(id=doc_id, is_delete=False).first()
        if doc:
            doc.is_delete = True
            doc.save(update_fields = ['is_delete', 'update_time'])
            return to_json_data(errmsg='文档删除成功！')
        return to_json_data(errno=Code.NODATA, errmsg='要删除的文档不存在！')

    def put(self, request, doc_id):
        doc = Doc.objects.only('id').filter(id=doc_id, is_delete=False).first()
        if not doc:
            return to_json_data(errno=Code.NODATA, errmsg='要更新的文档不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form = DocPubForm(data=dict_data)
        if form.is_valid():
            for attr, value in form.cleaned_data.items():
                setattr(doc, attr, value)
            doc.save()
            return to_json_data(errmsg='文档更新成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

class DocPubView(PermissionRequiredMixin, View):
    """文档发布类视图，负责渲染文档发布页面以及发布新文档"""
    permission_required = ('doc.view_doc', 'doc.add_doc')
    raise_exception = True
    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(DocPubView, self).handle_no_permission()

    def get(self, request):
        return render(request, 'admin/doc/docs_pub.html')

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form = DocPubForm(data=dict_data)
        if form.is_valid():
            doc_instance = form.save(commit=False)
            doc_instance.author = request.user
            doc_instance.save()
            return to_json_data(errmsg='文档添加成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

class DocUploadFile(View):
    """上传文档至FastDFS服务器"""
    def post(self, request):
        text_file = request.FILES.get('text_file')
        if not text_file:
            logger.info('从前端获取文件失败！')
            return to_json_data(errno=Code.PARAMERR, errmsg='未选择文件！')
        logger.info(text_file.content_type)
        if text_file.content_type not in ('application/octet-stream', 'application/pdf', 'application/msword',
                                          'application/zip', 'text/plain', 'application/x-rar'):
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非文件类型！')
        try:
            file_ext_name = text_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片扩展名异常：{}'.format(e))
            file_ext_name = 'pdf'
        try:
            # image_file.read():读取文件
            result = FDFS_Client.upload_by_buffer(text_file.read(), file_ext_name)
        except Exception as e:
            logger.error('文件上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='文件上传异常')
        if result['Status'] == 'Upload successed.':
            file_url = FASTDFS_SERVER_DOMAIN + result['Remote file_id']
            return to_json_data(data={'text_file': file_url}, errmsg='文件上传成功！')
        else:
            logger.info('文件上传到FastDFS服务器失败')
            return to_json_data(errno=Code.UNKOWNERR, errmsg='上传文件到服务器失败！')

class CourseManageView(PermissionRequiredMixin, View):
    permission_required = ('course.view_course')
    raise_exception = True
    def get(self, request):
        courses = Course.objects.select_related('teacher', 'category').\
            only('title', 'teacher__name', 'category__name').filter(is_delete=False)
        return render(request, 'admin/course/courses_manage.html', locals())

class CourseEditView(PermissionRequiredMixin, View):
    """课程编辑类视图，负责渲染编辑页面以及删除和更新课程功能的实现"""
    permission_required = ('course.view_course', 'course.delete_course', 'course.change_course')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(CourseEditView, self).handle_no_permission()

    def get(self, request, course_id):
        course = Course.objects.filter(id=course_id, is_delete=False).first()
        if course:
            teachers = Teacher.objects.only('name').filter(is_delete=False)
            categories = CourseCategory.objects.only('name').filter(is_delete=False)
            return render(request, 'admin/course/courses_pub.html', locals())
        return to_json_data(errno=Code.PARAMERR, errmsg='要更新的课程不存在！')

    def delete(self, request, course_id):
        course = Course.objects.only('id').filter(id=course_id, is_delete=False).first()
        if course:
            course.is_delete = True
            course.save(update_fields=['is_delete', 'update_time'])
            return to_json_data(errmsg='课程删除成功！')
        return to_json_data(errno=Code.NODATA, errmsg='要删除的课程不存在！')

    def put(self, request, course_id):
        course = Course.objects.only('id').filter(id=course_id, is_delete=False).first()
        if not course:
            return to_json_data(errno=Code.NODATA, errmsg='要更新的课程不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form = CoursePubForm(data=dict_data)
        if form.is_valid():
            for attr, value in form.cleaned_data.items():
                setattr(course, attr, value)
            course.save()
            return to_json_data(errmsg='课程更新成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

class CoursePubView(PermissionRequiredMixin, View):
    """课程发布类视图，负责发布页面的渲染以及发布新课程功能的实现"""
    permission_required = ('course.view_course', 'course.add_course')
    raise_exception = True

    def get(self, request):
        teachers = Teacher.objects.only('name').filter(is_delete=False)
        categories = CourseCategory.objects.only('name').filter(is_delete=False)
        return render(request, 'admin/course/courses_pub.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        form = CoursePubForm(data=dict_data)
        if form.is_valid():
            form.save()
            return to_json_data(errmsg='课程发布成功！')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)

class GroupManageView(PermissionRequiredMixin, View):
    permission_required = ('auth.view_group')
    raise_exception = True

    def get(self, request):
        groups = Group.objects.values('id', 'name').annotate(num_users=Count('user')).order_by('-num_users', 'id')
        return render(request, 'admin/user/groups_manage.html', locals())

class GroupEditView(PermissionRequiredMixin, View):
    permission_required = ('auth.view_group', 'auth.delete_group', 'auth.change_group')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(GroupEditView, self).handle_no_permission()

    def get(self, request, group_id):
        group = Group.objects.filter(id=group_id).first()
        if group:
            permissions = Permission.objects.only('id').all()
            return render(request, 'admin/user/groups_add.html', locals())
        return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的用户组不存在！')

    def delete(self, request, group_id):
        group = Group.objects.filter(id=group_id).first()
        if group:
            group.permissions.clear()   # 清空权限
            group.delete()    # 物理删除
            return to_json_data(errmsg='用户组删除成功！')
        return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的用户组不存在！')

    def put(self, request, group_id):
        group = Group.objects.filter(id=group_id).first()
        if not group:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的用户组不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.NODATA, errmsg='组名为空！')
        if group_name != group.name and Group.objects.filter(name=group_name).exists():
            return to_json_data(errno=Code.DATAEXIST, errmsg='此组名已存在！')
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空！')
        try:
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('权限参数异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常！')
        all_permission_set = set(j.id for j in Permission.objects.only('id').all())
        if not permissions_set.issubset(all_permission_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的权限参数！')
        exists_permissions_set = set(i.id for i in group.permissions.all())
        if group.name == group_name and permissions_set == exists_permissions_set:
            return to_json_data(errno=Code.DATAEXIST, errmsg='用户组信息未修改')
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            group.permissions.add(p)
        group.name = group_name
        group.save()
        return to_json_data(errmsg='用户组更新成功！')

class GroupAddView(PermissionRequiredMixin, View):
    permission_required = ('auth.view_group', 'auth.add_group')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(GroupAddView, self).handle_no_permission()

    def get(self, request):
        permissions = Permission.objects.only('id').all()
        return render(request, 'admin/user/groups_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.NODATA, errmsg='组名为空！')
        group_tuple = Group.objects.get_or_create(name=group_name)
        group, status = group_tuple
        if not status:  # 创建成功时返回True,没有创建成功时说明数据库中存在该组名
            return to_json_data(errno=Code.DATAEXIST, errmsg='此组名已存在！')
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空！')
        try:
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('权限参数异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常！')
        all_permission_set = set(j.id for j in Permission.objects.only('id').all())
        if not permissions_set.issubset(all_permission_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的权限参数！')
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            group.permissions.add(p)
        group.save()
        return to_json_data(errmsg='用户组添加成功！')

class UsersManageView(PermissionRequiredMixin, View):
    permission_required = ('users.view_users')
    raise_exception = True

    def get(self, request):
        users = Users.objects.only('username', 'is_staff', 'is_superuser').filter(is_active=True)
        return render(request, 'admin/user/users_manage.html', locals())

class UsersEditView(PermissionRequiredMixin, View):
    permission_required = ('user.view_users', 'user.change_users', 'user.delete_users')
    raise_exception = True

    def handle_no_permission(self):
        if self.request.method.lower() != 'get':
            return to_json_data(errno=Code.ROLEERR, errmsg='没有操作权限')
        else:
            return super(UsersEditView, self).handle_no_permission()

    def get(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if user_instance:
            groups = Group.objects.only('name').all()
            return render(request, 'admin/user/users_edit.html', locals())
        return to_json_data(errno=Code.NODATA, errmsg='要更新的用户不存在！')

    def delete(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if user_instance:
            # 逻辑删除需要清空组和权限
            user_instance.groups.clear()  # 清除用户组
            user_instance.user_permissions.clear()  # 清除用户权限
            user_instance.is_active = False
            user_instance.save()
            return to_json_data(errmsg='用户删除成功！')
        return to_json_data(errno=Code.NODATA, errmsg='要删除的用户不存在！')

    def put(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if not user_instance:
            return to_json_data(errno=Code.NODATA, errmsg='要更新的用户不存在！')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))
        try:
            is_staff = int(dict_data.get('is_staff'))
            is_superuser = int(dict_data.get('is_superuser'))
            is_active = int(dict_data.get('is_active'))
            params = (is_staff, is_superuser, is_active)
            if not all([p in (0, 1) for p in params]):
                return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的参数！')
        except Exception as e:
            logger.info('参数错误：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误！')
        groups = dict_data.get('groups')
        if not groups:
            return to_json_data(errno=Code.PARAMERR, errmsg='未选择组！')
        try:
            groups_set = set(int(i) for i in groups)
        except Exception as e:
            logger.info('组id参数异常：{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='组参数异常！')
        groups_set_all = set(i.id for i in Group.objects.only('id').all())
        if not groups_set.issubset(groups_set_all):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的组！')
        gs = Group.objects.filter(id__in=groups_set)
        # 先清空组
        user_instance.groups.clear()
        # set可一次添加多个
        user_instance.groups.set(gs)
        user_instance.is_staff = bool(is_staff)
        user_instance.is_superuser = bool(is_superuser)
        user_instance.is_active = bool(is_active)
        user_instance.save()
        return to_json_data(errmsg='用户信息修改成功！')





























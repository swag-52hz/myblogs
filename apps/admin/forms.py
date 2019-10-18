from django import forms
from news.models import News, Tag
from doc.models import Doc
from course.models import Course


class NewsPubForm(forms.ModelForm):
    image_url = forms.URLField(label='文章图片url', error_messages={'required': '文章图片url不能为空'})
    tag = forms.ModelChoiceField(queryset=Tag.objects.only('id').filter(is_delete=False),
                                 error_messages={'required': '文章标签id不能为空', 'invalid_choice': '文章标签id不存在'})

    class Meta:
        # 指定关联的表
        model = News
        fields = ['title', 'digest', 'content', 'tag', 'image_url']
        error_messages = {
            'title': {
                'max_length': '文章标题最大长度不能超过150',
                'min_length': '文章标题最小长度为1',
                'required': '标题不能为空'
            },
            'digest': {
                'max_length': '文章摘要最大长度不能超过200',
                'min_length': '文章摘要最小长度为1',
                'required': '摘要不能为空'
            },
            'content': {
                'required': '文章内容不能为空'
            }
        }

class DocPubForm(forms.ModelForm):
    image_url = forms.URLField(label='文档缩略图url', error_messages={'required': '文档缩略图url不能为空'})
    file_url = forms.URLField(label='文档url', error_messages={'required': '文档url不能为空'})

    class Meta:
        model = Doc
        fields = ['title', 'image_url', 'file_url', 'desc']
        error_messages = {
            'title': {
                'max_length': '最大长度不能超过150',
                'min_length': '最小长度不能小于1',
                'required': '文档标题不能为空！'
            },
            'desc': {
                'max_length': "文档描述长度不能超过200",
                'min_length': "文档描述长度大于1",
                'required': '文档描述不能为空！'
            }
        }

class CoursePubForm(forms.ModelForm):
    cover_url = forms.URLField(label='课程封面图url',
                               error_messages={"required": "课程封面图url不能为空"})
    video_url = forms.URLField(label='课程视频url',
                               error_messages={"required": "课程视频url不能为空"})

    class Meta:
        model = Course
        exclude = ['update_time', 'create_time', 'is_delete']
        error_messages = {
            'title': {
                'max_length': "课程标题长度不能超过150",
                'min_length': "课程标题长度大于1",
                'required': '课程标题不能为空',
            },
        }
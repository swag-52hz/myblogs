from django.urls import path
from . import views


app_name = 'admin'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('tags/', views.TagsManageView.as_view(), name='tags'),
    path('tags/<int:tag_id>/', views.TagEditView.as_view(), name='tag_edit'),
    path('hotnews/', views.HotNewsManageView.as_view(), name='hotnews_manage'),
    path('hotnews/<int:hotnews_id>/', views.HotNewsEditView.as_view(), name='hotnews_edit'),
    path('hotnews/add/', views.HotNewsAddView.as_view(), name='hotnews_add'),
    path('tags/<int:tag_id>/news/', views.NewsByTagIdView.as_view(), name='news_by_tag_id'),
    path('news/', views.NewsManageView.as_view(), name='news_manage'),
    path('news/<int:news_id>/', views.NewsEditView.as_view(), name='news_edit'),
    path('news/pub/', views.NewsPubView.as_view(), name='news_pub'),
    path('news/images/', views.NewsUploadImage.as_view(), name='upload_image'),
    path('token/', views.UploadToken.as_view(), name='upload_token'),  # 七牛云上传图片需要调用token
    path('markdown/images/', views.MarkDownUploadImage.as_view(), name='markdown_image_upload'),
    path('banners/', views.BannerManageView.as_view(), name='banner_manage'),
    path('banners/<int:banner_id>/', views.BannerEditView.as_view(), name='banner_edit'),
    path('banners/add/', views.BannerAddView.as_view(), name='banner_add'),
    path('docs/', views.DocManageView.as_view(), name='docs_manage'),
    path('docs/<int:doc_id>/', views.DocEditView.as_view(), name='docs_edit'),
    path('docs/pub/', views.DocPubView.as_view(), name='docs_pub'),
    path('docs/files/', views.DocUploadFile.as_view(), name='upload_file'),
    path('courses/', views.CourseManageView.as_view(), name='course_manage'),
    path('courses/<int:course_id>/', views.CourseEditView.as_view(), name='course_edit'),
    path('courses/pub/', views.CoursePubView.as_view(), name='course_pub'),
    path('groups/', views.GroupManageView.as_view(), name='groups_manage'),
    path('groups/<int:group_id>/', views.GroupEditView.as_view(), name='groups_edit'),
    path('groups/add/', views.GroupAddView.as_view(), name='group_add'),
    path('users/', views.UsersManageView.as_view(), name='users_manage'),
    path('users/<int:user_id>/', views.UsersEditView.as_view(), name='users_edit'),
]
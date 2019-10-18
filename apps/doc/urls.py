from django.urls import path
from doc import views


app_name = 'doc'
urlpatterns = [
    path('', views.doc_index, name='index'),
    path('<int:doc_id>/', views.DocDownload.as_view(), name='doc_download')
]
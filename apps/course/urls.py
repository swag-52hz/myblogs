from django.urls import path
from course import views


app_name = 'course'
urlpatterns = [
    path('', views.course_list, name='index'),
    path('<int:course_id>/', views.CourseDetailView.as_view(), name='course_detail')
]
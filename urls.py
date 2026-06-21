from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_user, name='logout'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('event/create/', views.create_event, name='create_event'),
    path('event/<int:event_id>/register/', views.register_for_event, name='register_for_event'),
    path('event/<int:event_id>/approve/', views.approve_event_view, name='approve_event'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
]

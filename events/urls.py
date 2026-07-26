from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_user, name='logout'),
    path('my-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('event/create/', views.create_event, name='create_event'),
    path('event/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('event/<int:event_id>/register/', views.register_for_event, name='register_for_event'),
    path('event/<int:event_id>/unregister/', views.unregister_from_event, name='unregister_from_event'),
    path('event/<int:event_id>/approve/', views.approve_event_view, name='approve_event'),
    path('event/<int:event_id>/reject/', views.reject_event_view, name='reject_event'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('registration/<int:registration_id>/ticket/', views.view_ticket, name='view_ticket'),
    path('contact/', views.contact_inquiry, name='contact_inquiry'),
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
]


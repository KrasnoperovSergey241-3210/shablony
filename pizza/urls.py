from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('constructor/', views.constructor, name='constructor'),
    path('favorites/', views.favorites, name='favorites'),
    path('create_order/', views.create_order, name='create_order'),
    path('my_orders/', views.my_orders, name='my_orders'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('kitchen/', views.kitchen, name='kitchen'),
    path('api/update_status/<int:order_id>/', views.update_status, name='update_status'),
    path('courier/', views.courier_view, name='courier'),
    path('init_data/', views.init_data, name='init_data'),
]
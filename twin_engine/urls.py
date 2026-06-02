from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.twin_dashboard, name='twin_dashboard'),
    
    path('register/', views.register, name='register'),
   
    path('logout/', views.logout_view, name='logout'),  

]
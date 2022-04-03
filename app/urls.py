from django.urls import path
from . import views

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('user_details/', views.user_details, name='user_details'),
    path('signup/', views.signup, name='signup'),
    path('wallet/', views.wallet, name='wallet'),
    path('sell_new/', views.sell_new, name='sell_new'),
    path('buy_new/', views.buy_new, name='buy_new'),
    path('transaction_new/', views.transaction_new, name='transaction_new'),
    path('transaction/<str:pk>/', views.transaction_detail, name='transaction_detail'),
    path('transaction_active_list/', views.transaction_active_list, name='transaction_active_list'),
    path('earn_lose/', views.earn_lose, name='earn_lose'),
    path('transaction/<pk>/remove/', views.transaction_remove, name='transaction_remove'),
    path('welcome/', views.welcome, name='welcome'),
]
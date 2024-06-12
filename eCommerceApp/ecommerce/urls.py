from django.urls import path, re_path, include
from django.shortcuts import redirect
from rest_framework import routers
from . import views
from .views import ProductDetailView, ShopCategoriesApiView

r = routers.DefaultRouter()

# api
# r.register('confirmationshop', views.ConfirmationShop)
r.register('users', views.UserViewSet, basename='users')
r.register('categories', views.CategoryViewset, basename='categories')
r.register('products', views.ProductViewSet, basename='products')
r.register('comments', views.CommentViewSet, basename='comments')
r.register('shops', views.ShopViewSet, basename='shops')
# r.register('login', views.LoginWithPasswordViewSet, basename='login-with-password')

urlpatterns = [
    path('', include(r.urls)),  # tạo api

    path('accounts/login/', views.user_login, name='login'),
    path('accounts/login-with-sms/', views.login_with_sms, name='login_with_sms'),
    # Still not handle enter wrong OTP, expired OTP, Resend
    path('accounts/login-with-google/', views.login_with_google, name='login_with_google'),
    path('accounts/signup/', views.user_signup, name='signup'),
    # path('accounts/profile/', views.profile_view, name='profile'),
    path('accounts/basic-setup-profile/', views.basic_setup_profile, name='basic_setup_profile'),
    path('accounts/logout/', views.log_out, name='logout'),
    path('accounts/verify-otp/', views.verify_otp, name='verify_otp'),

    # api
    path('products/<int:product_id>/', ProductDetailView.as_view(), name='product_detail'),
    path('shop/<int:shop_id>/categories/', ShopCategoriesApiView.as_view(), name='category_shop'),
    path('products/<int:product_id>/replyParentComment/<int:replyComment_id>/replyChildComments/',
         views.ReplyChildCommentView.as_view(),
         name='reply_parent_comment'),
    path('users/<int:user_id>/addresses/<int:user_address_id>/default/', views.UserDefaultAddressView.as_view(),
         name='default_address'),

    # vn pay api
    path('index', views.index, name='index'),
    path('payment', views.payment, name='payment'),
    path('payment_ipn', views.payment_ipn, name='payment_ipn'),
    path('payment_return', views.payment_return, name='payment_return'),
    path('query', views.query, name='query'),
    path('refund', views.refund, name='refund'),
]

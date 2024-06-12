import hashlib
import hmac
import json
import random
from datetime import datetime

import cloudinary.uploader
import requests
from django.conf import settings
from django.contrib.auth import logout, authenticate
from django.core.cache import cache
from django.db.models import Q, Count
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from oauth2_provider.models import AccessToken, RefreshToken
from rest_framework import viewsets, generics, status, parsers, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from . import serializers, perms, pagination
from .models import *
from .vnpay import vnpay
import re
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

import os
from google.oauth2 import id_token
from google.auth.transport import requests as auth_requests


def extract_first_number_from_string(s):
    # Tìm số đầu tiên trong chuỗi s
    match = re.search(r'\d+', s)
    if match:
        return match.group(0)
    return None


# from django.utils.http import urlquote
# django.utils.http.urlquote = quote


# in adpater.py
# def get_app(self, request, provider, client_id=None):
#     from allauth.socialaccount.models import SocialApp
#
#     apps = self.list_apps(request, provider=provider, client_id=client_id)
#     if len(apps) > 1:
#         # raise MultipleObjectsReturned
#         pass
#     elif len(apps) == 0:
#         raise SocialApp.DoesNotExist()
#     return apps[0]
def get_access_token_login(user):
    access_token = AccessToken.objects.filter(user_id=user.id).first()
    if access_token and access_token.expires > timezone.now():
        return access_token
    else:
        refresh_token = RefreshToken.objects.filter(user_id=user.id).first()
        if not access_token or not refresh_token:
            return None
        if refresh_token:
            access_token = AccessToken.objects.filter(id=refresh_token.access_token_id).first()
            access_token.expires = timezone.now() + timezone.timedelta(hours=1)
            access_token.save()
            return access_token


@api_view(['POST', 'GET'])
def user_login(request):
    if request.method == 'GET':
        return Response({'success': 'Get form to login successfully'}, status=status.HTTP_200_OK)
    if request.method == 'POST':
        serializer = serializers.UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data.get('phone')
            password = serializer.validated_data.get('password')

            users_with_phone = User.objects.filter(phone=phone, is_active=1)
            if users_with_phone.exists():
                user = authenticate(request, username=users_with_phone.first().username, password=password)
                if user is not None:
                    access_token = get_access_token_login(user)
                    return Response({'success': 'Login successfully', 'access_token': access_token.token},
                                    status=status.HTTP_200_OK)

            return Response({'error': 'Invalid phone or password.'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def log_out(request):
    if request.method == 'POST':
        logout(request)
    return Response({'success': 'Logout successfully'}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def user_signup(request):
    if request.method == 'GET':
        return Response({'success': 'Get form to signup successfully'}, status=status.HTTP_200_OK)

    if request.method == 'POST':  # post phone + PW + rePW
        serializer = serializers.UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data.get('phone')
            password = serializer.validated_data.get('password')

            request.session['phone'] = phone  # Tạo session_phone_loginWithSms để verify
            otp = generate_otp()  # Tạo cache_otp_signup
            cache.set('password', password, timeout=OTP_EXPIRY_SECONDS)  # Tạo cache_password_signup
            print('sup_PW', cache.get('password'))
            cache.set(phone, otp, timeout=OTP_EXPIRY_SECONDS)  # Lưu mã OTP vào cache với khóa là số điện thoại
            cache.set('is_signup', True, timeout=OTP_EXPIRY_SECONDS)  # Tạo cache_is_signup để verify

            # Kiểm tra phone used
            existing_user = User.objects.filter(phone=phone, is_active=1).first()
            if existing_user:  # existing_user chuyen den verify_otp
                cache.set('existing_user', existing_user.username)

            # Gửi mã OTP đến số điện thoại bằng Twilio
            # account_sid = 'ACf3bd63d2afda19fdcb1a7ab22793a8b8'
            # auth_token = '[AuthToken]'
            # client = Client(account_sid, auth_token)
            # message_body = f'DJANGO: Nhập mã xác minh {otp} để đăng ký tài khoản. Mã có hiệu lực trong 5 phút.'
            # message = client.messages.create(
            #     from_='+12513090557',
            #     body=message_body,
            #     to=phone_number
            # )
            return Response({'message': f'Mã OTP của bạn là {otp}.'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid phone or password.'}, status=status.HTTP_401_UNAUTHORIZED)


# Thời gian hết hạn của mã OTP (đơn vị: giây)
OTP_EXPIRY_SECONDS = 300  # 5 phút


def generate_otp():
    return str(random.randint(100000, 999999))


@api_view(['GET', 'POST'])
def login_with_sms(request):
    if request.method == 'GET':  # post len loginWithSms -> verifyOTP
        return Response({'success': 'Get form to login with SMS successfully'}, status=status.HTTP_200_OK)
    if request.method == 'POST':  # post phone + generate otp
        serializer = serializers.UserLoginWithSMSSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data.get('phone')
            request.session['phone'] = phone  # Tạo session_phone_loginWithSms để verify
            otp = generate_otp()
            cache.set(phone, otp, timeout=OTP_EXPIRY_SECONDS)  # Lưu mã OTP vào cache với khóa là số điện thoại
            cache.set('is_login', True, timeout=OTP_EXPIRY_SECONDS)  # Tạo cache_is_login để verify
            # Gửi mã OTP đến số điện thoại bằng Twilio
            # account_sid = 'ACf3bd63d2afda19fdcb1a7ab22793a8b8'
            # auth_token = '[AuthToken]'
            # client = Client(account_sid, auth_token)
            # message_body = f'DJANGO: Nhập mã xác minh {otp} để đăng ký tài khoản. Mã có hiệu lực trong 5 phút.'
            # message = client.messages.create(
            # from_='+12513090557',
            # body=message_body,
            # to=phone_number
            # )
            return Response({'message': f'Mã OTP của bạn là {otp}.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def verify_otp(request):
    if request.method == 'GET':
        phone = request.session.get('phone')  # lấy phone từ session_phone_loginWithSms | session_phone_signup
        if cache.get('is_login'):  # Nếu là login
            is_login = cache.get('is_login')  # Lấy is_login từ cache_is_login
            return Response({'success': 'Get form to login successfully', 'is_login': is_login, 'phone': phone},
                            status=status.HTTP_200_OK)
        if cache.get('is_signup'):  # Nếu là signup
            is_signup = cache.get('is_signup')
            # Kiểm tra existing_user $$$$$$$$$$$$$$$$$$4
            if cache.get('existing_user'):
                existing_user = cache.get('existing_user')
                cache.delete('existing_user')
                return Response({'success': f'{phone} was used for {existing_user} user',
                                 'phone': phone,
                                 'existing_user': existing_user}, status=status.HTTP_200_OK)
            return Response({'success': 'Get form to signup successfully', 'is_signup': is_signup, 'phone': phone},
                            status=status.HTTP_200_OK)

    if request.method == 'POST':  # post phone + otp
        serializer = serializers.VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = request.session.get('phone')  # lấy phone từ session_phone_loginWithSms | session_phone_signup
            otp = serializer.validated_data.get('otp')

            cached_otp = cache.get(phone)  # Lấy mã OTP từ cache
            if cached_otp is None:
                return Response({'message': 'Mã OTP đã hết hạn.'}, status=status.HTTP_400_BAD_REQUEST)
            print('otp_cotp', otp == cached_otp)
            if otp == cached_otp:
                cache.delete(phone)  # Xóa mã OTP từ cache sau khi đã sử dụng
                if cache.get('is_login'):  # Xóa cache_is_login
                    cache.delete('is_login')
                    user = User.objects.get(phone=phone, is_active=1)
                    del request.session['phone']
                    access_token = get_access_token_login(user)
                    return Response({'success': 'Login successfully', 'access_token': access_token.token},
                                    status=status.HTTP_200_OK)
                print(cache.get('is_signup'))
                if cache.get('is_signup'):  # Xóa cache_is_signup
                    cache.delete('is_signup')
                    return Response({'success': 'Continue to setup profile to finish'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Mã OTP không hợp lệ.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_access_token(username, password):
    data = {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'client_id': os.getenv('APP_CLIENT_ID'),
        'client_secret': os.getenv('APP_CLIENT_SECRET')
    }

    response = requests.post('http://127.0.0.1:8000/o/token/', data=data)

    if response.status_code == 200:
        access_token = response.json().get('access_token')
        return access_token
    else:
        return None


@api_view(['POST', 'GET'])
def basic_setup_profile(request):  # Đều dùng cho signup cũ và mới
    if request.method == 'GET':
        return Response({'success': 'Enter username and choose avatar'}, status=status.HTTP_200_OK)

    if request.method == 'POST':
        serializer = serializers.UserSignupSerializer(data=request.data)
        # Create signup (with email)
        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            avatar = serializer.validated_data.get('avatar')
            email = serializer.validated_data.get('email')
            first_name = serializer.validated_data.get('first_name')
            last_name = serializer.validated_data.get('last_name')

            if User.objects.filter(username=username).exists():  # Check if the username is already taken
                return Response({'error': 'Username already taken.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                print('re_data ', serializer)
                if avatar:
                    response = cloudinary.uploader.upload(avatar)
                    avatar_url = response.get('secure_url')
                    # is_active=0 vs user has used phone be4 & create new user
                    User.objects.filter(phone=request.session.get('phone'), is_active=1).update(is_active=0)
                    if not email:
                        user = User.objects.create_user(username=username, password=cache.get('password'),
                                                        phone=request.session.get('phone'), avatar=avatar_url)
                        user.is_active = 1
                        user.save()
                    elif email:
                        print('email ',  email)
                        user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                                        email=email, password=cache.get('password'),
                                                        phone=request.session.get('phone'), avatar=avatar_url)
                        user.is_active = 1
                        user.save()

                    token = get_access_token(username, cache.get('password'))
                    cache.delete('password')  # Delete cache_password_signup
                    if 'phone' in request.session:
                        del request.session['phone']  # Delete session_phone_signup
                    # Redirect to another page after profile setup
                    return Response({'success': 'User created successfully', 'access_token': token},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'File upload failed'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def login_with_google(request):
    if request.method == 'POST':
        try:
            # decodeIdToken
            decodeIdToken = id_token.verify_oauth2_token(request.data['idToken'], auth_requests.Request(),
                                                         os.getenv('WEB_CLIENT_ID'))
            # Check expiredToken
            if int(timezone.now().timestamp()) > decodeIdToken['exp']:
                return Response({'error': 'Token has expired'}, status=status.HTTP_400_BAD_REQUEST)
            # Compare tokenInfo & userInfo
            id_token_user_info = {
                "email": decodeIdToken['email'],
                "familyName": decodeIdToken.get('family_name', ''),
                "givenName": decodeIdToken.get('given_name', ''),
                "id": decodeIdToken['sub'],
                "name": decodeIdToken['name'],
                "photo": decodeIdToken.get('picture', '')
            }
            request_user_info = request.data['user']
            if id_token_user_info != request_user_info:
                return Response({'error': 'User information mismatch'}, status=status.HTTP_400_BAD_REQUEST)

            # Serialize and validate the email
            serializer = serializers.UserLoginWithGoogleSerializer(data={'email': request_user_info['email']})
            if serializer.is_valid():
                email = serializer.validated_data.get('email')

                users_with_email = User.objects.filter(email=email, is_active=1)
                if users_with_email.exists():
                    access_token = get_access_token_login(users_with_email.first())
                    return Response({'success': 'Login successfully', 'access_token': access_token.token},
                                    status=status.HTTP_200_OK)
                else:
                    # Store data to session
                    return Response({'success': 'Continue to setup profile to finish'}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'error': 'Login with Google failed'}, status=status.HTTP_400_BAD_REQUEST)

#
# from .models import User, Place, Purpose, Meeting, GuestMeeting
#
#
#
# class PlaceViewset(viewsets.ViewSet, generics.ListAPIView):
#     queryset = Place.objects.all()
#     serializer_class = serializers.PlaceSerializer


########################################### View của darklord0710 ######################################################

class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer

    def get_permissions(self):
        if self.action in ['get_current_user', 'get_post_patch_confirmationshop', 'get_shop', 'get_user_ratings',
                           'get_post_addresses', 'get_post_orders']:
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny(), ]

    @action(methods=['get', 'patch'], url_path='current-user', detail=False)  # /users/current-user/
    def get_current_user(self, request):
        user = request.user
        if request.method.__eq__('PATCH'):  # PATCH này phải viết hoa
            for k, v in request.data.items():
                setattr(user, k, v)
            user.save()

        return Response(serializers.UserSerializer(user).data)

    @action(methods=['get', 'post', 'patch'], url_path='confirmationshop', detail=True)  # /users/{id}/confirmationshop/
    def get_post_patch_confirmationshop(self, request, pk):
        self.parser_classes = [parsers.MultiPartParser]

        if request.user.id != int(pk):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.method.__eq__('PATCH'):  # Patch vẫn cập nhật đc 2 dòng ảnh và status
            citizen_identification_image_data = request.data.get('citizen_identification_image')
            # confirmationShops = self.get_object().confirmationshop_set.get(user=request.user.id)
            confirmationShops = ConfirmationShop.objects.get(user_id=pk)
            confirmationShops.citizen_identification_image = citizen_identification_image_data
            confirmationShops.status = StatusConfirmationShop.objects.get(
                id=4)  # chỗ này phải sửa cả object , ko thể sửa mỗi id khóa ngoại
            confirmationShops.save()
            return Response(serializers.ConfirmationShopSerializer(confirmationShops).data,
                            status=status.HTTP_200_OK)  # nếu gắn many=True ở đây sẽ bị lỗi not iterable

        elif request.method.__eq__('POST'):
            citizen_identification_image_data = request.data.get('citizen_identification_image')
            status_confirm_shop = StatusConfirmationShop.objects.get(id=4)
            c = self.get_object().confirmationshop_set.create(user=request.user, status=status_confirm_shop,
                                                              citizen_identification_image=citizen_identification_image_data)

            return Response(serializers.ConfirmationShopSerializer(c).data, status=status.HTTP_201_CREATED)

        confirmationShop = ConfirmationShop.objects.filter(user_id=pk).exists()
        if not confirmationShop:
            return Response(status=status.HTTP_204_NO_CONTENT)
        confirmationShop = ConfirmationShop.objects.filter(user_id=pk).first()
        # confirmationShops = self.get_object().confirmationshop_set.select_related(
        #     'user').first()  # chỉ join khi có quan hệ 1-1 # .all() hay không có đều đc ????
        return Response(serializers.ConfirmationShopSerializer(confirmationShop).data,
                        status=status.HTTP_200_OK)

    @action(methods=['get'], url_path="shop", detail=True)  # /users/{id}/shop/
    def get_shop(self, request, pk):
        shop = self.get_object().shop_set.filter(active=True, user_id=pk).first()
        # shop = Shop.objects.get(active=True, user_id=pk)
        return Response(serializers.ShopSerializer(shop).data, status=status.HTTP_200_OK)

    # Lấy tất cả rating của user hiện tại
    @action(methods=['get'], url_path="ratings", detail=True)  # /users/{user_id}/ratings/
    def get_user_ratings(self, request, pk):
        if request.user.id != int(pk):
            return Response(status=status.HTTP_403_FORBIDDEN)
        ratings = self.get_object().rating_set.select_related('user').order_by("-id")  # user nằm trong rating
        return Response(serializers.RatingSerializer(ratings, many=True).data, status=status.HTTP_200_OK)

    # GET,POST /users/{user_id}/addresses/
    @action(methods=['get', 'post', 'patch'], url_path="addresses", detail=True)
    def get_post_addresses(self, request, pk):

        if request.method == "POST":
            name = request.data.get('name')
            phone = request.data.get('phone_number')
            address = request.data.get('address')
            user = request.user

            user_addresses = UserAddresses.objects.filter(user_id=user.id, default=True).first()
            if user_addresses is not None:
                user_address = self.get_object().useraddresses_set.create(name=name, phone_number=phone,
                                                                          address=address,
                                                                          user=user)
            else:
                user_address = self.get_object().useraddresses_set.create(name=name, phone_number=phone,
                                                                          address=address,
                                                                          user=user,
                                                                          default=True)

            return Response(serializers.UserAddressSerializer(user_address).data, status=status.HTTP_201_CREATED)
        if request.method == "PATCH":
            name = request.data.get('name')
            phone = request.data.get('phone_number')
            address = request.data.get('address')
            user_address_id = request.data.get('user_address_id')
            user_address = self.get_object().useraddresses_set.filter(user_id=pk, id=user_address_id).first()
            user_address.name = name
            user_address.phone_number = phone
            user_address.address = address
            user_address.save()
            return Response(serializers.UserAddressSerializer(user_address).data, status=status.HTTP_200_OK)

        user_addresses = self.get_object().useraddresses_set.select_related('user')
        return Response(serializers.UserAddressSerializer(user_addresses, many=True).data, status=status.HTTP_200_OK)

    @action(methods=['get', 'post'], url_path="orders", detail=True)  # now
    def get_post_orders(self, request, pk):
        if request.method == "POST":
            order_data = {}

            final_amount = request.data.get('final_amount')
            quantity = request.data.get('quantity')
            product_id = request.data.get('product_id')
            product_color_id = request.data.get('product_color_id')
            # USER
            user = request.user
            # USER ADDRESS
            user_address = self.get_object().useraddresses_set.filter(user_id=pk, default=True).first()
            if user_address is None:
                user_address = self.get_object().useraddresses_set.create(name=user.name, phone_number=user.phone,
                                                                          address="",
                                                                          user=user,
                                                                          default=True)
            # ORDER STATUS
            statusOrder = StatusOrder.objects.get(id=2)
            # PRODUCT
            product = Product.objects.get(id=product_id)
            # ORDER
            order = self.get_object().order_set.create(user=user, status=statusOrder, product=product,
                                                       final_amount=final_amount)
            order_data['order'] = order
            order_detail = OrderDetail.objects.create(quantity=quantity, userAddresses=user_address, order=order)
            order_data['order_detail'] = order_detail
            # PRODUCT COLOR
            if product_color_id:
                product_color = ProductImagesColors.objects.get(id=product_color_id)
                order_product_color = OrderProductColor.objects.create(product_colors=product_color, order=order)
                order_data['order_product_color'] = product_color.name_color

            product_sell = ProductSell.objects.filter(product_id=product_id).first()
            product_sell.sold_quantity = product_sell.sold_quantity + 1
            product_sell.save()

            return Response(serializers.OrderFinalSerializer(order_data).data, status=status.HTTP_201_CREATED)

        orders = self.get_object().order_set.select_related('user')
        return Response(serializers.OrderSummaryItemSerializer(orders, many=True).data, status=status.HTTP_200_OK)


# PATCH users/<int:user_id>/addresses/<int:user_address_id>/default
class UserDefaultAddressView(APIView):
    def patch(self, request, user_id, user_address_id):
        user_address_default = UserAddresses.objects.filter(user_id=user_id, default=True).first()
        user_address_default.default = False
        user_address_default.save()

        user_address = UserAddresses.objects.filter(user_id=user_id, default=True).exists()
        if not user_address:
            user_address = UserAddresses.objects.filter(user_id=user_id, id=user_address_id).first()
            user_address.default = True
            user_address.save()
        return Response(serializers.UserAddressSerializer(user_address).data, status=status.HTTP_200_OK)


# =============================== (^3^) =============================== #

# POST compare/ (receive name_product & name_shop)
# GET compare/?page=?&q= (q is name_product;
# Return product with name_product, price_product, name_shop,
# *location_shop, *shipping unit, ratings, 1st latest comments)


class ShopViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    queryset = Shop.objects.filter(active=True)
    serializer_class = serializers.ShopSerializer

    # GET /shops/{shop_id}/
    @action(methods=['get'], url_path="shop", detail=True)
    def get_shop_by_id(self, request, pk):
        shop = self.queryset.filter(id=pk).first()
        return Response(serializers.ShopSerializer(shop).data, status=status.HTTP_200_OK)

    # GET /shops/{shop_id}/products
    @action(methods=['get'], url_path="products", detail=True)
    def get_product_by_shop(self, request, pk):
        product = Product.objects.filter(shop_id=pk).all()
        return Response(serializers.ProductSerializer(product, many=True).data, status=status.HTTP_200_OK)


class ShopCategoriesApiView(APIView):
    def get(self, request, shop_id):
        result = Category.objects.filter(product__shop_id=shop_id).annotate(product_count=Count('product__id')).values(
            'name', 'product_count')
        serialized_data = serializers.ShopCategoriesSerializer(result, many=True).data
        return JsonResponse(serialized_data, safe=False)


class ProductViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    pagination_class = pagination.ProductPaginator
    # GET products/
    queryset = Product.objects.filter(active=True)
    serializer_class = serializers.ProductSerializer

    # GET products/?page=?&product_name=&shop_name=&price_from=&price_to=
    # -> getByName/Price/Shop , arrangeByName/Price, paginate 5 products/page

    def get_permissions(self):
        if self.action in ['create_update_rating', 'update_delete_comment', 'get_post_replyComment_product',
                           'post_confirm_order', 'get_post_all_rating_comment_product']:
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny(), ]

    def get_queryset(self):
        queries = self.queryset

        n = self.request.query_params.get("n")  # name product
        pmn = self.request.query_params.get("pmn")  # price min
        pmx = self.request.query_params.get("pmx")  # price max
        opi = self.request.query_params.get("opi")  # order price increase
        opd = self.request.query_params.get("opd")  # order price decrease
        oni = self.request.query_params.get("oni")  # order name increase
        ond = self.request.query_params.get("ond")  # order name decrease
        cate_name = self.request.query_params.get('cate_name')  # filter by category name
        if self.action == 'list':
            if n:
                queries = queries.filter(Q(name__icontains=n) | Q(shop__name__icontains=n))
            if pmn:
                queries = queries.filter(price__gte=pmn)
            if pmx:
                queries = queries.filter(price__lte=pmx)
            if opi is not None:
                queries = queries.order_by('price')
            if opd is not None:
                queries = queries.order_by('-price')
            if oni is not None:
                queries = queries.order_by('name')
            if ond is not None:
                queries = queries.order_by('-name')
            if cate_name:
                queries = queries.filter(category__name=cate_name)

        return queries

    # GET /products/{product_id}/
    @action(methods=['get'], url_path="product_detail", detail=True)
    def get_product_by_id(self, request, pk):
        product = self.queryset.filter(id=pk).first()
        return Response(serializers.ProductSerializer(product).data, status=status.HTTP_200_OK)

    # POST/products/{product_id}/rating/  <Bear Token is owner>
    # Patch/products/{product_id}/rating/  <Bear Token is owner>

    @action(methods=['post', 'patch'], url_path="rating", detail=True)
    def create_update_rating(self, request, pk):
        ratedShop = request.data.get('ratedShop')
        ratedProduct = request.data.get('ratedProduct')
        product = self.queryset.filter(id=pk).first()
        user = request.user
        if request.method == 'POST':

            productSell = ProductSell.objects.filter(product_id=product.id).first()
            shop = Shop.objects.get(id=product.shop_id)

            r = self.get_object().rating_set.create(ratedShop=ratedShop, ratedProduct=ratedProduct, user=user,
                                                    product=product)
            rated_products_len = Rating.objects.filter(product_id=r.product_id)
            if rated_products_len == 0:
                productSell.rating = ratedProduct
                shop.rated = ratedShop
            else:
                totalPointPro = rated_products_len.aggregate(total_sum=Sum('ratedProduct'))['total_sum']
                productSell.rating = totalPointPro / len(rated_products_len)
                productSell.save()

                totalPointShop = rated_products_len.aggregate(total_sum=Sum('ratedShop'))['total_sum']
                shop.rated = totalPointShop / len(rated_products_len)
                shop.save()
            # Tạo sẵn comment tại đây để tạo 1 hàng ManyToMany
            comment = Comment.objects.create(user=user, contentShop="", contentProduct="", product=product)
            comment.save()
            rating_comment = Rating_Comment.objects.create(rating=r, comment=comment, product=product, user=user)
            rating_comment.save()
            return Response(serializers.RatingSerializer(r).data, status=status.HTTP_201_CREATED)
        elif request.method == 'PATCH':
            # Xử lý yêu cầu PATCH cho đánh giá
            productSell = ProductSell.objects.filter(product_id=product.id).first()

            shop = Shop.objects.get(id=product.shop_id)

            rating = Rating.objects.get(id=request.data.get('ratingId'))  # lấy rating từ dữ liệu JSON request lên
            rating.ratedShop = ratedShop
            rating.ratedProduct = ratedProduct
            rating.save()

            rated_products_len = Rating.objects.filter(product_id=rating.product_id)

            totalPointPro = rated_products_len.aggregate(total_sum=Sum('ratedProduct'))['total_sum']
            productSell.rating = totalPointPro / len(rated_products_len)
            productSell.save()

            totalPointShop = rated_products_len.aggregate(total_sum=Sum('ratedShop'))['total_sum']
            shop.rated = totalPointShop / len(rated_products_len)
            shop.save()

            return Response(serializers.RatingSerializer(rating).data, status=status.HTTP_200_OK)

    # GET products/{product_id}/ratings
    @action(methods=['get'], url_path="ratings", detail=True)
    def get_product_ratings(self, request, pk):
        ratings = self.get_object().rating_set.select_related('user').order_by("-id")  # user,product nằm trong rating
        print(ratings.query)
        return Response(serializers.RatingSerializer(ratings, many=True).data, status=status.HTTP_200_OK)

    # PATCH/DELETE products/{product_id}/comments  <Bear Token is owner>
    # Chỉ dùng sau khi vừa đánh giá sản phẩm xong , muốn cập nhật xài cái /comments/{comment_id}/
    @action(methods=['post', 'patch', 'delete'], url_path="comment", detail=True)
    def update_delete_comment(self, request, pk):
        if request.method == 'PATCH':
            product = self.queryset.filter(id=pk).first()
            contentShop = request.data.get('contentShop')
            contentProduct = request.data.get('contentProduct')
            comment = self.get_object().comment_set.filter(user_id=request.user.id, product_id=product.id).last()
            comment.contentShop = contentShop
            comment.contentProduct = contentProduct
            comment.save()

        return Response(serializers.CommentSerializer(comment).data, status=status.HTTP_200_OK)

    # GET products/{product_id}/ratings_comments/
    # POST products/{product_id}/ratings_comments/
    @action(methods=['get', 'post'], url_path="rating_comment", detail=True)
    def get_post_all_rating_comment_product(self, request, pk):
        if request.method == 'POST':
            ratedShop = request.data.get('ratedShop')
            ratedProduct = request.data.get('ratedProduct')
            contentShop = request.data.get('contentShop')
            contentProduct = request.data.get('contentProduct')
            order_id = request.data.get('order_id')
            product = self.queryset.filter(id=pk).first()
            order = Order.objects.get(id=order_id)
            user = request.user

            productSell = ProductSell.objects.filter(product_id=product.id).first()
            shop = Shop.objects.get(id=product.shop_id)

            r = self.get_object().rating_set.create(ratedShop=ratedShop, ratedProduct=ratedProduct, user=user,
                                                    product=product)
            rated_products_len = Rating.objects.filter(product_id=r.product_id)
            if rated_products_len == 0:
                productSell.rating = ratedProduct
                shop.rated = ratedShop
            else:
                totalPointPro = rated_products_len.aggregate(total_sum=Sum('ratedProduct'))['total_sum']
                productSell.rating = totalPointPro / len(rated_products_len)
                productSell.save()

                totalPointShop = rated_products_len.aggregate(total_sum=Sum('ratedShop'))['total_sum']
                shop.rated = totalPointShop / len(rated_products_len)
                shop.save()

            comment = Comment.objects.create(user=user, contentShop=contentShop, contentProduct=contentProduct,
                                             product=product)
            comment.save()
            rating_comment = Rating_Comment.objects.create(rating=r, comment=comment, product=product, user=user,
                                                           order=order)
            rating_comment.save()
            return Response(serializers.Rating_Comment_Serializer(rating_comment).data,
                            status=status.HTTP_201_CREATED)

        rating_comment = Rating_Comment.objects.prefetch_related('comment').filter(product_id=pk).filter(
            active=True).order_by("-id")
        return Response(serializers.Rating_Comment_Serializer(rating_comment, many=True).data,
                        status=status.HTTP_200_OK)

    @action(methods=['get', 'post'], url_path='replyComment', detail=True)
    def get_post_replyComment_product(self, request, pk):
        product = Product.objects.get(id=pk)
        if request.method == 'POST':
            user = request.user
            content = request.data.get('content')
            parent_comment_id = request.data.get('parent_comment_id')

            if parent_comment_id:
                parent_comment = ReplyComment.objects.filter(id=parent_comment_id).first()
                parent_comment_order = parent_comment.order
                replyComment = ReplyComment.objects.create(user=user, content=content, parent_comment=parent_comment,
                                                           product=product, order=parent_comment_order)
                replyComment.save()
            else:
                parent_comment_order = ReplyComment.objects.filter(isParentComment=True).count()

                replyComment = ReplyComment.objects.create(user=user, content=content, product=product,
                                                           isParentComment=True, order=parent_comment_order)
                replyComment.save()

            return Response(serializers.ReplyCommentSerializer(replyComment).data, status=status.HTTP_200_OK)

        replyComments = ReplyComment.objects.filter(product_id=pk, active=True)

        return Response(serializers.ReplyCommentSerializer(replyComments, many=True).data, )

    @action(methods=['get'], url_path='replyParentComment', detail=True)
    def get_replyParentComment_product(self, request, pk):
        replyParentComments = ReplyComment.objects.filter(product_id=pk, active=True, isParentComment=True).order_by(
            "-id")

        return Response(serializers.ReplyCommentSerializer(replyParentComments, many=True).data,
                        status=status.HTTP_200_OK)

    @action(methods=['post'], url_path='confirm_order', detail=True)
    def post_confirm_order(self, request, pk):
        if request.method == 'POST':
            confirm_order_data = {}

            product = self.queryset.filter(id=pk).first()
            confirm_order_data['product'] = product

            color_id = request.data.get('color_id')
            if color_id:
                product_color = ProductImagesColors.objects.get(product_id=product.id, id=color_id)
                confirm_order_data['product_color'] = product_color

            user = request.user
            user_address = UserAddresses.objects.filter(user_id=user.id, default=True).first()
            confirm_order_data['user_address'] = user_address

            quantity = request.data.get("quantity")
            confirm_order_data['quantity'] = quantity

            return Response(serializers.OrderConfirmationSerializer(confirm_order_data).data, status=status.HTTP_200_OK)


# GET products/{product_id}/replyParentComment/{replyComment_id}/replyChildComments/
class ReplyChildCommentView(APIView):
    def get(self, request, product_id, replyComment_id):
        product = Product.objects.get(id=product_id)
        parent_comment = ReplyComment.objects.filter(id=replyComment_id).first()
        order = parent_comment.order

        replyChildComments = ReplyComment.objects.filter(isParentComment=False, order=order).exists()

        if not replyChildComments:
            return Response(status=status.HTTP_204_NO_CONTENT)

        replyChildComments = ReplyComment.objects.filter(isParentComment=False,
                                                         order=order)
        return Response(serializers.ReplyCommentSerializer(replyChildComments, many=True).data,
                        status=status.HTTP_200_OK)


# GET products/{product_id}/
class ProductDetailView(APIView):
    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            shop = Shop.objects.get(id=product.shop_id)

        except Product.DoesNotExist:
            return Response({"message": "Product not found"}, status=404)

        # Lấy tất cả thông tin liên quan đến sản phẩm
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            # Thêm các trường từ các bảng liên quan
            "info": product.productinfo_set.filter(product_id=product.id).values("id", "origin", "material",
                                                                                 "description", "manufacture").first(),
            "images": product.productimagedetail_set.filter(product_id=product.id),
            # cần custom url Cloudinary nên ko cần lấy values trước
            "colors": product.productimagescolors_set.filter(product_id=product.id),
            "videos": product.productvideos_set.filter(product_id=product.id),
            "sell": product.productsell_set.filter(product_id=product.id).values("id", "sold_quantity", "percent_sale",
                                                                                 "rating", "delivery_price").first(),
            "shop": shop,
            "category": product.category
        }
        return Response(serializers.ProductDetailSerializer(product_data).data, status=status.HTTP_200_OK)


# PATCH/DELETE comments/{comment_id}  <Bear Token is owner> <permission_classes>
class CommentViewSet(viewsets.ViewSet, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = Comment.objects.all()
    serializer_class = serializers.CommentSerializer
    permission_classes = [perms.CommentOwner]

    def get_permissions(self):
        if self.action in ['like_comment']:
            return [permissions.IsAuthenticated(), ]

        return super().get_permissions()

    # POST /comments/{comment_id}/like/  <Bear Token is owner> <permission_classes>
    # @action(methods=['post'], url_path="like", detail=True)
    # def like_comment(self, request, pk):
    #     like, created = Like.objects.get_or_create(user=request.user, comment=self.get_object())
    #     if not created:
    #         like.active = not like.active
    #         like.save()
    #
    #     return Response(status=status.HTTP_200_OK)


# =============================== (^3^) =============================== #


class CategoryViewset(viewsets.ViewSet, generics.ListAPIView):
    queryset = Category.objects.filter(active=True)
    serializer_class = serializers.CategorySerializer

    # GET categories/
    @action(methods=['get'], url_path="products", detail=True)
    def get_products_by_category(self, request, pk):
        print(self.queryset)
        products = Product.objects.filter(category_id=pk, active=True)
        return Response(serializers.ProductSerializer(products, many=True).data,
                        status=status.HTTP_200_OK)


# =============================== (^3^) =============================== #

# =============================== (^3^) =============================== #
# GET payment/
# POST payment/{id_method} <Bear Token is owner>

def index(request):
    return render(request, "payment/index.html", {"title": "Danh sách demo"})


def hmacsha512(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()


@api_view(['GET', 'POST'])
def payment(request):
    if request.method == 'POST':
        order_ecommerce_id = request.data.get('order_ecommerce_id')
        order_type = "billpayment"
        order_id = int(timezone.now().strftime('%Y%m%d%H%M%S'))
        amount = request.data.get('amount')
        order_desc = 'Thanh toan hoa don ecommerce co ma la ' + str(order_ecommerce_id) + ' qua VN PAY'
        bank_code = ""
        language = "vn"
        ipaddr = get_client_ip(request)
        # Build URL Payment
        vnp = vnpay()
        vnp.requestData['vnp_Version'] = '2.1.0'
        vnp.requestData['vnp_Command'] = 'pay'
        vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
        vnp.requestData['vnp_Amount'] = amount * 100
        vnp.requestData['vnp_CurrCode'] = 'VND'
        vnp.requestData['vnp_TxnRef'] = order_id
        vnp.requestData['vnp_OrderInfo'] = order_desc
        vnp.requestData['vnp_OrderType'] = order_type

        # Check language, default: vn
        if language and language != '':
            vnp.requestData['vnp_Locale'] = language
        else:
            vnp.requestData['vnp_Locale'] = 'vn'
            # Check bank_code, if bank_code is empty, customer will be selected bank on VNPAY
        if bank_code and bank_code != "":
            vnp.requestData['vnp_BankCode'] = bank_code

        vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')
        vnp.requestData['vnp_IpAddr'] = ipaddr
        vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
        vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)
        vnpay_data = {
            'url': vnpay_payment_url,
        }

        return Response(serializers.PaymentVnPaySerializer(vnpay_data).data, status=status.HTTP_200_OK)
    else:
        context = {
            "title": "Thanh toán"
        }
        return render(request, "payment/payment.html", context)


def payment_ipn(request):
    inputData = request.GET
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.dict()
        order_id = inputData['vnp_TxnRef']
        amount = inputData['vnp_Amount']
        order_desc = inputData['vnp_OrderInfo']
        vnp_TransactionNo = inputData['vnp_TransactionNo']
        vnp_ResponseCode = inputData['vnp_ResponseCode']
        vnp_TmnCode = inputData['vnp_TmnCode']
        vnp_PayDate = inputData['vnp_PayDate']
        vnp_BankCode = inputData['vnp_BankCode']
        vnp_CardType = inputData['vnp_CardType']

        if vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            # Check & Update Order Status in your Database
            # Your code here
            firstTimeUpdate = True
            totalamount = True
            if totalamount:
                if firstTimeUpdate:
                    if vnp_ResponseCode == '00':
                        print('Payment Success. Your code implement here')
                    else:
                        print('Payment Error. Your code implement here')

                    # Return VNPAY: Merchant update success
                    result = JsonResponse({'RspCode': '00', 'Message': 'Confirm Success'})
                else:
                    # Already Update
                    result = JsonResponse({'RspCode': '02', 'Message': 'Order Already Update'})
            else:
                # invalid amount
                result = JsonResponse({'RspCode': '04', 'Message': 'invalid amount'})
        else:
            # Invalid Signature
            result = JsonResponse({'RspCode': '97', 'Message': 'Invalid Signature'})
    else:
        result = JsonResponse({'RspCode': '99', 'Message': 'Invalid request'})

    return result


def payment_return(request):
    inputData = request.GET
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.dict()
        order_id = inputData['vnp_TxnRef']
        amount = int(inputData['vnp_Amount']) / 100
        order_desc = inputData['vnp_OrderInfo']
        vnp_TransactionNo = inputData['vnp_TransactionNo']
        vnp_ResponseCode = inputData['vnp_ResponseCode']
        vnp_TmnCode = inputData['vnp_TmnCode']
        vnp_PayDate = inputData['vnp_PayDate']
        vnp_BankCode = inputData['vnp_BankCode']
        vnp_CardType = inputData['vnp_CardType']

        order_ecommerce_id = int(extract_first_number_from_string(order_desc))
        order_ecommerce = None
        if order_ecommerce_id > 0:
            order_ecommerce = Order.objects.filter(id=order_ecommerce_id).first()
            if order_ecommerce is None:
                return JsonResponse({"title": "Kết quả thanh toán",
                                     "result": "Loi vi khong ton tai don hang nay trong ecommerce app !",
                                     "order_id": order_id,
                                     "amount": amount,
                                     "order_desc": order_desc,
                                     "vnp_TransactionNo": vnp_TransactionNo}, status=status.HTTP_400_BAD_REQUEST)
            if order_ecommerce and order_ecommerce.status.id == 1:
                return JsonResponse({"title": "Kết quả thanh toán",
                                     "result": "Loi vi don hang nay da duoc thanh toan !", "order_id": order_id,
                                     "amount": amount,
                                     "order_desc": order_desc,
                                     "vnp_TransactionNo": vnp_TransactionNo}, status=status.HTTP_208_ALREADY_REPORTED)

        payment_vnpay_detail = PaymentVNPAYDetail.objects.create(order_id=order_id, amount=amount,
                                                                 order_desc=order_desc,
                                                                 vnp_TransactionNo=vnp_TransactionNo,
                                                                 vnp_ResponseCode=vnp_ResponseCode,
                                                                 orderEcommerce=order_ecommerce)
        payment_vnpay_detail.save()
        order_id = int(inputData['vnp_TxnRef'])

        if vnp.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            if vnp_ResponseCode == "00":
                status_order = StatusOrder.objects.get(id=1)
                order_ecommerce.status = status_order
                order_ecommerce.save()
                return JsonResponse({"title": "Kết quả thanh toán",
                                     "result": "Thanh cong", "order_id": order_id,
                                     "amount": amount,
                                     "order_desc": order_desc,
                                     "vnp_TransactionNo": vnp_TransactionNo,
                                     "vnp_ResponseCode": vnp_ResponseCode}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({"title": "Kết quả thanh toán",
                                     "result": "Lỗi", "order_id": order_id,
                                     "amount": amount,
                                     "order_desc": order_desc,
                                     "vnp_TransactionNo": vnp_TransactionNo,
                                     "vnp_ResponseCode": vnp_ResponseCode}, status=status.HTTP_200_OK)
        else:
            return JsonResponse(
                {"title": "Kết quả thanh toán", "result": "Lỗi", "order_id": order_id, "amount": amount,
                 "order_desc": order_desc, "vnp_TransactionNo": vnp_TransactionNo,
                 "vnp_ResponseCode": vnp_ResponseCode, "msg": "Sai checksum"}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse({"title": "Kết quả thanh toán", "result": ""})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


n = random.randint(10 ** 11, 10 ** 12 - 1)
n_str = str(n)
while len(n_str) < 12:
    n_str = '0' + n_str


def query(request):
    if request.method == 'GET':
        return JsonResponse({"title": "Kiểm tra kết quả giao dịch"})

    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_Version = '2.1.0'

    vnp_RequestId = n_str
    vnp_Command = 'querydr'
    vnp_TxnRef = request.POST['order_id']
    vnp_OrderInfo = 'kiem tra gd'
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_IpAddr = get_client_ip(request)

    hash_data = "|".join([
        vnp_RequestId, vnp_Version, vnp_Command, vnp_TmnCode,
        vnp_TxnRef, vnp_TransactionDate, vnp_CreateDate,
        vnp_IpAddr, vnp_OrderInfo
    ])

    secure_hash = hmac.new(secret_key.encode(), hash_data.encode(), hashlib.sha512).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return JsonResponse(
        {"title": "Kiểm tra kết quả giao dịch", "response_json": response_json})


def refund(request):
    if request.method == 'GET':
        return render(request, "payment/refund.html", {"title": "Hoàn tiền giao dịch"})

    url = settings.VNPAY_API_URL
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = settings.VNPAY_TMN_CODE
    vnp_RequestId = n_str
    vnp_Version = '2.1.0'
    vnp_Command = 'refund'
    vnp_TransactionType = request.POST['TransactionType']
    vnp_TxnRef = request.POST['order_id']
    vnp_Amount = request.POST['amount']
    vnp_OrderInfo = request.POST['order_desc']
    vnp_TransactionNo = '0'
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_CreateBy = 'user01'
    vnp_IpAddr = get_client_ip(request)

    hash_data = "|".join([
        vnp_RequestId, vnp_Version, vnp_Command, vnp_TmnCode, vnp_TransactionType, vnp_TxnRef,
        vnp_Amount, vnp_TransactionNo, vnp_TransactionDate, vnp_CreateBy, vnp_CreateDate,
        vnp_IpAddr, vnp_OrderInfo
    ])

    secure_hash = hmac.new(secret_key.encode(), hash_data.encode(), hashlib.sha512).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_Amount": vnp_Amount,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_TransactionType": vnp_TransactionType,
        "vnp_TransactionNo": vnp_TransactionNo,
        "vnp_CreateBy": vnp_CreateBy,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return JsonResponse(
        {"title": "Kết quả hoàn tiền giao dịch", "response_json": response_json})

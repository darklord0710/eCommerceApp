import requests
import cloudinary.uploader, random
from django.core.serializers import serialize
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import logout, authenticate, login
from oauth2_provider.models import AccessToken, RefreshToken
from django.utils import timezone
from rest_framework.views import APIView

from .models import Category, User, Product, Shop, ProductInfo, ProductImageDetail, ProductImagesColors, ProductVideos, \
    ProductSell, ConfirmationShop, \
    StatusConfirmationShop, Rating, Comment, Rating_Comment, Like
from rest_framework import viewsets, generics, status, parsers, permissions
from . import serializers, perms, pagination
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from django.core.cache import cache
from django.db.models import Q, Count, F
from django.db.models import Sum


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


def log_out(request):
    logout(request)
    return render(request, 'login.html')


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
            return Response({'message': f'Mã OTP của bạn là {otp}.'})
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
            return Response({'message': f'Mã OTP của bạn là {otp}.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def verify_otp(request):
    if request.method == 'GET':
        phone = request.session.get('phone')  # lấy phone từ session_phone_loginWithSms | session_phone_signup
        if cache.get('is_login'):  # Nếu là login
            is_login = cache.get('is_login')  # Lấy is_login từ cache_is_login
            return Response({'success': 'Get form to login successfully'},
                            {'is_login': is_login, 'phone': phone})
        if cache.get('is_signup'):  # Nếu là signup
            is_signup = cache.get('is_signup')
            # Kiểm tra existing_user $$$$$$$$$$$$$$$$$$4
            if cache.get('existing_user'):
                existing_user = cache.get('existing_user')
                cache.delete('existing_user')
                return Response({'success': f'{phone} was used for {existing_user} user'}, status=status.HTTP_200_OK)
            return Response({'success': 'Get form to signup successfully'}, {'is_signup': is_signup, 'phone': phone})

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
        'client_id': 'huSwBrzoYojItzHqIKGClwAMrbTp9Tb9ktTmOofY',
        'client_secret': 'VX7Ow4UvEOYY8mOxq9CJ6tput695aR4UcILjxKyZsHVOuCnaH1JhDer19KFiDYh3bH8hkefKy3r5TqfOU4rt4JDgTpG36C9kvlQciXfmYpS2ooivSkyyxSS1aJCGAnBQ',
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
        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            avatar = serializer.validated_data.get('avatar')

            if User.objects.filter(username=username).exists():  # Check if the username is already taken
                return Response({'error': 'Username already taken.'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                if avatar:
                    response = cloudinary.uploader.upload(avatar)
                    avatar_url = response.get('url')
                    # is_active=0 vs user has used phone be4 & create new user
                    User.objects.filter(phone=request.session.get('phone'), is_active=1).update(is_active=0)
                    user = User.objects.create_user(username=username, password=cache.get('password'),
                                                    phone=request.session.get('phone'), avatar=avatar_url)
                    user.is_active = 1
                    user.save()

                    token = get_access_token(username, cache.get('password'))
                    cache.delete('password')  # Xóa cache_password_signup
                    if 'phone' in request.session:
                        del request.session['phone']  # Xóa session_phone_signup
                    # Redirect to another page after profile setup
                    return Response({'success': 'User created successfully', 'access_token': token},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'File upload failed'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# For login with Google
# def profile_view(request):
#     picture_url = None
#     if request.user.is_authenticated:
#         user = request.user
#         if not user.avatar:
#             try:
#                 social_account = SocialAccount.objects.get(user=user)
#                 extra_data = social_account.extra_data
#                 picture_url = extra_data.get('picture')
#                 if picture_url:
#                     # Tải hình ảnh từ URL và lưu vào CloudinaryField
#                     upload_result = cloudinary.uploader.upload(picture_url)
#                     user.avatar = upload_result['url']
#                     user.save()
#                     print(f"URL mới được lưu trong Cloudinary: {user.avatar}")
#             except SocialAccount.DoesNotExist:
#                 print("Không có thông tin SocialAccount tương ứng.")
#         else:
#             print(f"Hình ảnh hiện tại từ Cloudinary: {user.avatar.url}")
#             picture_url = user.avatar.url
#             return render(request, 'noti.html', {'picture_url': picture_url})
#     else:
#         print("User not authenticated")
#     return render(request, 'noti.html', {'picture_url': picture_url})


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
    parser_classes = [parsers.MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['get_current_user', 'get_post_patch_confirmationshop', 'get_shop', 'get_user_ratings']:
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

        # confirmationShops = ConfirmationShop.objects.get(user_id=pk)
        confirmationShops = self.get_object().confirmationshop_set.select_related(
            'user')  # chỉ join khi có quan hệ 1-1 # .all() hay không có đều đc ????
        return Response(serializers.ConfirmationShopSerializer(confirmationShops, many=True).data,
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


class ProductViewSet(viewsets.ViewSet, generics.ListCreateAPIView):
    pagination_class = pagination.ProductPaginator
    # GET products/
    queryset = Product.objects.filter(active=True)
    serializer_class = serializers.ProductSerializer

    # GET products/?page=?&product_name=&shop_name=&price_from=&price_to=
    # -> getByName/Price/Shop , arrangeByName/Price, paginate 5 products/page

    def get_permissions(self):
        if self.action in ['create_update_rating', 'update_delete_comment']:
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
        cate_id = self.request.query_params.get('cate_id')  # filter by category id
        if self.action == 'list':
            if n:
                queries = queries.filter(Q(name__icontains=n) | Q(shop__name__icontains=n))
                queries = queries.filter()
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
            if cate_id:
                queries = queries.filter(category_id=cate_id)

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
            comment = Comment.objects.create(user=user, content="", product=product)
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
        ratings = self.get_object().rating_set.select_related('user').order_by("-id")  # user nằm trong rating
        return Response(serializers.RatingSerializer(ratings, many=True).data, status=status.HTTP_200_OK)

    # PATCH/DELETE products/{product_id}/comments  <Bear Token is owner>
    @action(methods=['post', 'patch', 'delete'], url_path="comment", detail=True)
    def update_delete_comment(self, request, pk):
        if request.method == 'PATCH':
            product = self.queryset.filter(id=pk).first()
            content = request.data.get('content')
            comment = self.get_object().comment_set.filter(user_id=request.user.id, product_id=product.id).last()
            comment.content = content
            comment.save()

        return Response(serializers.CommentSerializer(comment).data, status=status.HTTP_200_OK)

    # GET products/{product_id}/ratings_comments
    @action(methods=['get'], url_path="rating_comment", detail=True)
    def get_all_rating_comment_product(self, request, pk):
        rating_comment = Rating_Comment.objects.prefetch_related('comment').filter(product_id=pk).filter(
            active=True).order_by("-id")
        return Response(serializers.Rating_Comment_Serializer(rating_comment, many=True).data,
                        status=status.HTTP_200_OK)


# GET /products/{product_id}/
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
        }
        return Response(serializers.ProductDetailSerializer(product_data).data, status=status.HTTP_200_OK)


class ShopCategoriesApiView(APIView):
    def get(self, request, shop_id):
        result = Category.objects.filter(product__shop_id=shop_id).annotate(product_count=Count('product__id')).values(
            'name', 'product_count')
        serialized_data = serializers.ShopCategoriesSerializer(result, many=True).data
        return JsonResponse(serialized_data, safe=False)


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
    @action(methods=['post'], url_path="like", detail=True)
    def like_comment(self, request, pk):
        like, created = Like.objects.get_or_create(user=request.user, comment=self.get_object())
        if not created:
            like.active = not like.active
            like.save()

        return Response(status=status.HTTP_200_OK)


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
# GET payment/
# POST payment/{id_method} <Bear Token is owner>

# =============================== (^3^) =============================== #
# GET statistics/revenue/?category_id=&?product_id=?q= (q = mm/qq/yyyy) <Bear Token is owner>
# GET statistics/{shop_id}/?q= (mm/qq/yyyy) <Bear Token is owner> (return the number of products sold in every category)

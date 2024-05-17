from cloudinary.models import CloudinaryField
from cloudinary.templatetags import cloudinary

from .models import Category, User, Product, Shop, ProductInfo, ProductImageDetail, ProductImagesColors, ProductVideos, \
    ProductSell, ConfirmationShop, StatusConfirmationShop, BaseModel, Rating, \
    Comment, Rating_Comment, Interaction, ReplyComment, UserAddresses, Order, StatusOrder, OrderDetail, \
    OrderProductColor

from rest_framework.serializers import ModelSerializer
from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseModel

    def to_representation(self, instance):  # ghi đè 1 trường trong fields
        rep = super().to_representation(instance)
        rep['img'] = instance.img.url

        return rep


class UserSerializer(ModelSerializer):
    def create(self, validated_data):  # hash password be4 store in database
        data = validated_data.copy()
        user = User(**data)  # unpacking dict and pass them as arg into init model User
        user.set_password(user.password)
        user.save()

        return user

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'avatar', 'first_name', 'last_name', 'email', 'birthday', 'phone']
        # 'is_staff', 'is_vendor', 'is_superuser', 'is_active'] Dont need to return, to affect to create a user with no oauth
        extra_kwargs = {  # prevent the password field returned when creating a new user
            'password': {
                'write_only': 'true'
            }
        }

    def to_representation(self, instance):  # ghi đè 1 trường trong fields
        rep = super().to_representation(instance)
        rep['avatar'] = instance.avatar.url if instance.avatar and hasattr(instance.avatar, 'url') else None
        return rep


class UserAddressSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserAddresses
        fields = ['id', 'name', 'phone_number', 'address', 'default', 'user']


##################### UserAddressesSerializer Dto ####################


class UserAddressSerializerDto(serializers.ModelSerializer):
    class Meta:
        model = UserAddresses
        fields = ['id', 'name', 'phone_number', 'address']


##################### Confirmation Shop ####################


class StatusConfirmationShop(ModelSerializer):
    class Meta:
        model = StatusConfirmationShop
        fields = '__all__'


class ConfirmationShopSerializer(ModelSerializer):
    user = UserSerializer()
    status = StatusConfirmationShop()  # nếu ko serializer những khóa ngoại vẫn đc , nhưng ko ra đầy đủ thông tin

    class Meta:
        model = ConfirmationShop
        fields = ['id', 'user', 'status', 'citizen_identification_image', 'note']

    def to_representation(self, instance):  # ghi đè 1 trường trong fields
        rep = super().to_representation(instance)
        rep['citizen_identification_image'] = instance.citizen_identification_image.url

        return rep


#####################   Category and Product and Shop  #####################

class ShopSerializer(BaseSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'img', 'name', 'following', 'followed', 'rated']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductInfoSerializer(ModelSerializer):
    class Meta:
        model = ProductInfo
        fields = ["id", "origin", "material", "description", "manufacture"]


class ProductImageDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImageDetail
        fields = ['id', 'image']

    def to_representation(self, instance):  # ghi đè 1 trường trong fields
        rep = super().to_representation(instance)
        rep['image'] = instance.image.url

        return rep


class ProductImagesColorsSerializer(ModelSerializer):
    class Meta:
        model = ProductImagesColors
        fields = ["id", "name_color", "url_image"]

    def to_representation(self, instance):  # ghi đè 1 trường trong fields
        rep = super().to_representation(instance)
        rep['url_image'] = instance.url_image.url

        return rep


class ProductVideoSerializer(ModelSerializer):
    class Meta:
        model = ProductVideos
        fields = ["id", "url_video"]

    def to_representation(self, instance):  # ghi đè 1 trường trong fields
        rep = super().to_representation(instance)
        rep['url_video'] = instance.url_video.url

        return rep


class ProductSellSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSell
        fields = ['id', 'sold_quantity', 'percent_sale', 'rating', 'delivery_price']


class ProductSerializer(BaseSerializer):
    sold_quantity = serializers.IntegerField(source='productsell.sold_quantity', read_only=True)
    rating = serializers.FloatField(source='productsell.rating', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'img', 'name', 'price', 'sold_quantity', 'rating', ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            product_sell = ProductSell.objects.get(product=instance)
            product_sell_data = ProductSellSerializer(product_sell).data
            representation.update(product_sell_data)
            representation['img'] = instance.img.url

        except ProductSell.DoesNotExist:
            representation['sold_quantity'] = 0
            representation['rating'] = 0.0
        return representation


class ProductDetailSerializer(serializers.ModelSerializer):
    info = ProductInfoSerializer()
    images = ProductImageDetailSerializer(many=True)
    colors = ProductImagesColorsSerializer(many=True)
    videos = ProductVideoSerializer(many=True)
    sell = ProductSellSerializer()
    shop = ShopSerializer()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'info', 'images', 'colors', 'videos', 'sell', 'shop']


class ShopCategoriesSerializer(serializers.Serializer):
    name = serializers.CharField()
    product_count = serializers.IntegerField()


#####################   UserLogin   #######################

class UserLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        phone = data.get('phone')
        password = data.get('password')
        if not phone or not password:
            raise serializers.ValidationError("Both phone and password are required.")
        return data


class UserLoginWithSMSSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate(self, data):
        phone = data.get('phone')
        if not phone:
            raise serializers.ValidationError("Phone number is required.")
        return data


class VerifyOTPSerializer(serializers.Serializer):
    otp = serializers.CharField()

    def validate(self, data):
        otp = data.get('otp')
        if not otp:
            raise serializers.ValidationError("OTP is required.")
        return data


class UserSignupSerializer(serializers.Serializer):
    username = serializers.CharField()
    avatar = serializers.ImageField()

    def validate(self, data):
        username = data.get('username')
        avatar = data.get('avatar')
        if not username:
            raise serializers.ValidationError("Username is required.")
        if not avatar:
            raise serializers.ValidationError("Avatar image is required.")
        return data


##################### Rating and Comment BASE ####################


class RatingSerializer(serializers.ModelSerializer):
    # user = UserSerializer()
    product = ProductSerializer()

    class Meta:
        model = Rating
        fields = ['id', 'created_date', 'ratedShop', 'ratedProduct', 'user_id', 'product']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    product = ProductSerializer()

    class Meta:
        model = Comment
        fields = ['id', 'created_date', 'contentShop', 'contentProduct', 'user', 'product']


##################### Rating and Comment Dto ####################

class User_RatingCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar', ]


class Rating_RatingCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'created_date', 'ratedProduct', 'ratedShop']


class Comment_RatingCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'created_date', 'contentShop', 'contentProduct']


class Rating_Comment_Serializer(serializers.ModelSerializer):
    user = User_RatingCommentSerializer()
    comment = Comment_RatingCommentSerializer()
    rating = Rating_RatingCommentSerializer()

    class Meta:
        model = Rating_Comment
        fields = ['id', 'comment', 'user', 'rating']


class ReplyCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    isParentCommentReply = serializers.SerializerMethodField()

    class Meta:
        model = ReplyComment
        fields = ['id', 'created_date', 'content', 'parent_comment_id', 'product_id', 'user', 'isParentCommentReply']

    def get_isParentCommentReply(self, obj):
        return ReplyComment.objects.filter(parent_comment_id=obj.id).exists()


################## Order ####################

class StatusOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusOrder
        fields = ['status']


class OrderConfirmationSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()
    product = ProductSerializer()
    user_address = UserAddressSerializerDto()
    product_color = ProductImagesColorsSerializer(required=False)


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    product = ProductSerializer()
    status = StatusOrderSerializer()

    class Meta:
        model = Order
        fields = ['id', 'user', 'product', 'status', 'final_amount']


class OrderDetailSerializer(serializers.ModelSerializer):
    userAddresses = UserAddressSerializerDto()

    class Meta:
        model = OrderDetail
        fields = ['id', 'order_date', 'quantity', 'userAddresses']


class OrderFinalSerializer(serializers.Serializer):
    order = OrderSerializer()
    order_detail = OrderDetailSerializer()
    order_product_color = serializers.CharField(required=False)


###################### Payment VNPAY ################
class PaymentVnPaySerializer(serializers.Serializer):
    url = serializers.CharField()

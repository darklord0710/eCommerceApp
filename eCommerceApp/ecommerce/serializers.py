from .models import Category, User, Product, Shop, ProductInfo, ProductImageDetail, ProductImagesColors, ProductVideos, \
    ProductSell, Voucher, VoucherCondition, VoucherType, ConfirmationShop, StatusConfirmationShop, BaseModel, Rating, \
    Comment

from rest_framework.serializers import ModelSerializer
from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseModel


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


class ShopSerializer(ModelSerializer):
    # user = UserSerializer()

    class Meta:
        model = Shop
        fields = ['name', 'following', 'followed', 'rating']


class StatusConfirmationShop(ModelSerializer):
    class Meta:
        model = StatusConfirmationShop
        fields = '__all__'


class ConfirmationShopSerializer(ModelSerializer):
    user = UserSerializer()
    status = StatusConfirmationShop()  # nếu ko serializer những khóa ngoại vẫn đc , nhưng ko ra đầy đủ thông tin

    class Meta:
        model = ConfirmationShop
        fields = ['id', 'user', 'status', 'citizen_identification_image']

    def to_representation(self, instance):  # ghi đè 1 trường trong fields
        rep = super().to_representation(instance)
        rep['citizen_identification_image'] = instance.citizen_identification_image.url

        return rep


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSellSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSell
        fields = ['sold_quantity', 'percent_sale', 'rating']


class ProductSerializer(BaseSerializer):
    sold_quantity = serializers.IntegerField(source='productsell.sold_quantity', read_only=True)
    percent_sale = serializers.IntegerField(source='productsell.percent_sale', read_only=True)
    rating = serializers.FloatField(source='productsell.rating', read_only=True)

    class Meta:
        model = Product
        fields = ['img', 'name', 'price', 'shop_id', 'category_id', 'sold_quantity', 'percent_sale', 'rating']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            product_sell = ProductSell.objects.get(product=instance)
            product_sell_data = ProductSellSerializer(product_sell).data
            representation.update(product_sell_data)
            representation['img'] = instance.img.url

        except ProductSell.DoesNotExist:
            representation['sold_quantity'] = 0
            representation['percent_sale'] = 0
            representation['rating'] = 0.0
        return representation


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


class RatingSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    product = ProductSerializer()

    class Meta:
        model = Rating
        fields = ['created_date', 'ratedShop', 'ratedProduct', 'user', 'product']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    product = ProductSerializer()

    class Meta:
        model = Comment
        fields = ['created_date', 'content', 'user', 'product']

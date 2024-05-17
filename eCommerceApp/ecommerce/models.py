from enum import unique

from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField
from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError
from django import forms


class User(AbstractUser):
    avatar = CloudinaryField('image', default=None, null=True, blank=True)
    is_vendor = models.BooleanField(default=False)
    birthday = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=10, null=False, blank=True)


class UserAddresses(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=10, null=False)
    address = models.CharField(max_length=100, null=False)
    default = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class BaseModel(models.Model):
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)
    active = models.BooleanField(default=True)
    img = CloudinaryField(null=True)

    class Meta:
        abstract = True
        ordering = ['-id']


class Category(models.Model):
    name = models.CharField(max_length=50)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Shop(BaseModel):
    name = models.CharField(max_length=100)
    following = models.IntegerField(default=0)
    followed = models.IntegerField(default=0)
    rated = models.FloatField(null=True, default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.id}/ {self.name}"


class Product(BaseModel):
    name = models.CharField(max_length=150)
    price = models.FloatField(null=False)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=False)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=False, default=None)

    def __str__(self):
        return f"{self.category.name}/ {self.name}"


class ProductImageDetail(models.Model):
    image = CloudinaryField(default=None)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None)


class ProductImagesColors(models.Model):
    name_color = models.CharField(max_length=50)
    url_image = CloudinaryField(default=None)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None)


def validate_video_size(value):
    max_size = 30 * 1024 * 1024  # 30MB
    if str(value).endswith(".mp4"):
        if value.size > max_size:
            raise ValidationError("Hông được đăng video quá 30MB !")


class ProductVideos(models.Model):
    url_video = CloudinaryField(resource_type='video', allowed_formats=['mp4', 'webm'],
                                validators=[validate_video_size], blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None)


class ProductInfo(models.Model):
    origin = models.CharField(max_length=50)
    material = models.CharField(max_length=100)
    description = RichTextField(null=True)
    manufacture = models.CharField(max_length=255)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None)


class ProductSell(models.Model):
    delivery_price = models.FloatField(null=False, default=0)
    sold_quantity = models.IntegerField(null=False, default=0)
    percent_sale = models.IntegerField(default=0, null=False)
    rating = models.FloatField(null=False, default=0)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=None)


# class VoucherType(models.Model):
#     name = models.CharField(max_length=30, unique=True, null=False)
#     key = models.CharField(max_length=10, unique=True, null=False)


# class Voucher(BaseModel):
#     name = models.CharField(max_length=100)
#     code = models.CharField(max_length=10, unique=True, null=False)
#     description = RichTextField()
#     maximum_time_used = models.IntegerField(default=0)
#     voucher_type = models.ForeignKey(VoucherType, on_delete=models.CASCADE, default=None)


# class VoucherCondition(models.Model):
#     order_fee_min = models.FloatField(default=0)
#     voucher_sale = models.FloatField(default=0)
#     voucher_sale_max = models.FloatField(default=0)
#     time_usable = models.DateTimeField()
#     time_expired = models.DateTimeField()
#     voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, default=None)


# class User_Voucher(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
#     voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, default=None)
#     time_used = models.IntegerField(default=0)


class StatusOrder(models.Model):
    status = models.CharField(max_length=20, null=False)


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    status = models.ForeignKey(StatusOrder, on_delete=models.PROTECT)
    final_amount = models.FloatField(null=False, default=0)


class OrderDetail(models.Model):
    order_date = models.DateField(auto_now_add=True)
    recieved_date = models.DateField(null=True)
    quantity = models.IntegerField(null=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    userAddresses = models.ForeignKey(UserAddresses, on_delete=models.CASCADE)


class OrderProductColor(models.Model):
    product_colors = models.ForeignKey(ProductImagesColors, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)


# class Orders_Vouchers(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.PROTECT)
#     voucher = models.ForeignKey(Voucher, on_delete=models.PROTECT)


class Interaction(models.Model):
    created_date = models.DateField(auto_now_add=True, )
    updated_date = models.DateField(auto_now=True, )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Rating(Interaction):
    ratedShop = models.FloatField()
    ratedProduct = models.FloatField()


class Comment(Interaction):
    contentProduct = RichTextField(null=True)
    contentShop = RichTextField(null=True)
    active = models.BooleanField(default=True)


class Rating_Comment(Interaction):
    rating = models.ForeignKey(Rating, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)


class ReplyComment(models.Model):
    created_date = models.DateField(auto_now_add=True, )
    content = RichTextField(null=False)
    active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    order = models.IntegerField(null=False, default=0)
    isParentComment = models.BooleanField(default=False)


class StatusConfirmationShop(models.Model):
    status_content = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.status_content


class ConfirmationShop(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    citizen_identification_image = CloudinaryField()
    status = models.ForeignKey(StatusConfirmationShop, on_delete=models.PROTECT)
    note = RichTextField(default=None, null=True)


class PaymentVNPAYDetail(models.Model):
    order_id = models.CharField(max_length=20)
    amount = models.FloatField(null=False, default=0)
    order_desc = models.CharField(max_length=100)
    vnp_TransactionNo = models.CharField(null=True, blank=True, max_length=255)
    vnp_ResponseCode = models.CharField(null=True, blank=True, max_length=255)
    orderEcommerce = models.ForeignKey(Order, on_delete=models.CASCADE)

# class Like(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
#     active = models.BooleanField(default=True)
#
#     class Meta:
#         unique_together = ('user', 'comment')

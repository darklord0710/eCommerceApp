from django.contrib import admin
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.utils.html import mark_safe
from .models import Category, User, Product, Shop, ProductInfo, ProductImageDetail, ProductImagesColors, ProductVideos, \
    ProductSell, Voucher, VoucherCondition, VoucherType, ConfirmationShop, StatusConfirmationShop
from django.contrib.auth.models import Group
from django.db.models import QuerySet

APP_NAME = "ecommerce"


class BasePermissionChecker:
    @staticmethod
    def has_permission(request, group_name, method):
        if (request.user.groups.filter(name=group_name).exists()
                and f"{APP_NAME}.{method}_{group_name[:-8].lower()}" in request.user.get_user_permissions()
                or request.user.is_superuser):
            return True
        return False


class CustomGroupAdmin(admin.ModelAdmin):
    def has_view_permission(self, request, obj=None):
        # Kiểm tra nếu người dùng không phải là superuser
        if not request.user.is_superuser:
            # Nếu không phải là superuser, không cho phép xem bảng Group
            return False
        # Trả về giá trị mặc định nếu là superuser
        return True

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return False


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'active']
    search_fields = ['id', 'name']
    list_filter = ['id', 'name']

    def has_view_permission(self, request, obj=None):
        if (request.user.groups.filter(
                name='CATEGORY_MANAGER').exists() and "ecommerce.view_category" in request.user.get_user_permissions()
                or request.user.is_superuser):
            return True
        return False

    def has_add_permission(self, request):
        if request.user.groups.filter(
                name='CATEGORY_MANAGER').exists() and "ecommerce.add_category" in request.user.get_user_permissions() or request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.groups.filter(
                name='CATEGORY_MANAGER').exists() and "ecommerce.change_category" in request.user.get_user_permissions() or request.user.is_superuser:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.groups.filter(
                name='CATEGORY_MANAGER').exists() and "ecommerce.delete_category" in request.user.get_user_permissions() or request.user.is_superuser:
            return True
        return False


class CustomUserAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'phone', 'birthday', 'is_active', 'is_vendor',
                    'is_superuser',
                    'my_image']
    search_fields = ['id', 'username']
    list_filter = ['id', 'is_active', 'is_vendor', 'is_superuser']

    fieldsets = (
        (None, {'fields': ('username', 'avatar', 'password')}),
        ('Login info', {'fields': ('date_joined', 'last_login')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'birthday', 'phone')}),
        ('Permissions',
         {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_vendor', 'groups', 'user_permissions')}),
    )

    def my_image(self, user):
        if user.avatar:
            return mark_safe(f"<img width='200' height='100' src='{user.avatar.url}' />")

    def save_model(self, request, obj, form, change):

        if change and "pbkdf2_sha256" in form.cleaned_data['password']:
            super().save_model(request, obj, form, change)
        else:
            password = form.cleaned_data['password']
            # Mã hóa mật khẩu trước khi lưu
            if password:
                obj.set_password(password)
                super().save_model(request, obj, form, change)

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'USER_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'USER_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'USER_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'USER_MANAGER', 'delete')


class ShopAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'name', 'following', 'followed', 'rating', 'user_id', 'my_image', 'active']
    search_fields = ['id', 'name']
    list_filter = ['active', 'rating']
    readonly_fields = ['following', 'followed', 'rating', 'user_id', 'user']

    def my_image(self, shop):
        if shop.img:
            return mark_safe(f"<img width='200' height='200' src='{shop.img.url}' />")

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'SHOP_MANAGER', 'view')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        shop = Shop.objects.filter(user_id=request.user.id).first()
        if request.user.groups.filter(name="VENDOR_MANAGER").exists():
            # Lấy queryset mặc định
            if shop:
                queryset = queryset.filter(user=request.user)
                return queryset
            return Shop.objects.none()
        return queryset

    def has_add_permission(self, request):
        return self.has_permission(request, 'SHOP_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'SHOP_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'SHOP_MANAGER', 'delete')


class ProductInfoInline(admin.StackedInline):  # Hoặc InlineModelAdmin tùy thuộc vào giao diện bạn muốn
    model = ProductInfo
    extra = 1  # Số lượng form tạo mới ban đầu
    max_num = 1


class ProductImageDetailInline(admin.StackedInline):
    model = ProductImageDetail
    extra = 1
    max_num = 20


class ProductImagesColorInline(admin.StackedInline):
    model = ProductImagesColors
    extra = 1
    max_num = 20


class ProductVideosInline(admin.StackedInline):
    model = ProductVideos
    extra = 1
    max_num = 10


class ProductSellInline(admin.StackedInline):
    model = ProductSell
    extra = 1
    max_num = 1
    readonly_fields = ['sold_quantity', 'rating']


class ProductAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'shop_id', 'category_name', 'my_image', 'active']
    search_fields = ['id', 'name']
    list_filter = ['category_id', 'price']

    readonly_fields = ['shop']

    inlines = [ProductInfoInline, ProductImageDetailInline, ProductImagesColorInline, ProductVideosInline,
               ProductSellInline]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        # Kiểm tra xem người dùng có quyền admin không
        if request.user.is_superuser:
            readonly_fields.remove('shop')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        if request.user.is_superuser:
            obj.shop = Shop.objects.get(id=obj.shop_id)
        # Lấy shop từ người dùng hiện tại
        obj.shop = Shop.objects.get(user_id=request.user.id)
        super().save_model(request, obj, form, change)

    def my_image(self, product):
        if product.img:
            return mark_safe(f"<img width='200' height='200' src='{product.img.url}' />")

    def category_name(self, product):
        category = Category.objects.get(id=product.category_id)
        return category.name

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCT_MANAGER', 'view')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        products = None
        shop = Shop.objects.filter(user_id=request.user.id).first()  # .first() để chuyển từ dạng query sang object
        if shop:
            products = Product.objects.filter(shop_id=shop.id)

        if request.user.groups.filter(name="VENDOR_MANAGER").exists():
            if products:
                queryset = queryset.filter(shop__user=request.user)
                return queryset
            return Product.objects.none()

        return queryset

    def has_add_permission(self, request):
        return self.has_permission(request, 'PRODUCT_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCT_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCT_MANAGER', 'delete')


class ProductInfoAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'product_id', 'product_name', 'origin', 'material', 'manufacture']
    search_fields = ['id', 'manufacture']
    list_filter = ['origin', 'material', 'manufacture']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        products = None
        shop = Shop.objects.filter(user_id=request.user.id).first()  # .first() để chuyển từ dạng query sang object
        if shop:
            products = Product.objects.filter(shop_id=shop.id).all()

        if request.user.groups.filter(name="VENDOR_MANAGER").exists():
            if products:
                queryset = queryset.filter(product__shop=shop)
                return queryset
            return ProductInfo.objects.none()

        return queryset

    def product_name(self, obj):
        return obj.product.name

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTINFO_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'PRODUCTINFO_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTINFO_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTINFO_MANAGER', 'delete')


class ProductImageDetailAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'product_id', 'my_image']
    search_fields = ['id', 'product_id']
    list_filter = ['product_id']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        products = None
        shop = Shop.objects.filter(user_id=request.user.id).first()  # .first() để chuyển từ dạng query sang object
        if shop:
            products = Product.objects.filter(shop_id=shop.id).all()

        if request.user.groups.filter(name="VENDOR_MANAGER").exists():
            if products:
                queryset = queryset.filter(product__shop=shop)
                return queryset
            return ProductImageDetail.objects.none()

        return queryset

    def my_image(self, product):
        if product.image:
            return mark_safe(f"<img width='200' height='200' src='{product.image.url}' />")

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTIMAGEDETAIL_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'PRODUCTIMAGEDETAIL_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTIMAGEDETAIL_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTIMAGEDETAIL_MANAGER', 'delete')


class ProductImagesColorsAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'product_id', 'name_color', 'my_image']
    search_fields = ['id', 'name_color']
    list_filter = ['product_id']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        products = None
        shop = Shop.objects.filter(user_id=request.user.id).first()  # .first() để chuyển từ dạng query sang object
        if shop:
            products = Product.objects.filter(shop_id=shop.id).all()

        if request.user.groups.filter(name="VENDOR_MANAGER").exists():
            if products:
                queryset = queryset.filter(product__shop=shop)
                return queryset
            return ProductImagesColors.objects.none()

        return queryset

    def my_image(self, product):
        if product.url_image:
            return mark_safe(f"<img width='200' height='200' src='{product.url_image.url}' />")

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTIMAGESCOLORS_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'PRODUCTIMAGESCOLORS_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTIMAGESCOLORS_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTIMAGESCOLORS_MANAGER', 'delete')


class ProductVideosAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'product_id', 'my_video']
    search_fields = ['id']
    list_filter = ['product_id']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        products = None
        shop = Shop.objects.filter(user_id=request.user.id).first()  # .first() để chuyển từ dạng query sang object
        if shop:
            products = Product.objects.filter(shop_id=shop.id).all()

        if request.user.groups.filter(name="VENDOR_MANAGER").exists():
            if products:
                queryset = queryset.filter(product__shop=shop)
                return queryset
            return ProductVideos.objects.none()

        return queryset

    def my_video(self, product):
        if product.url_video:
            return mark_safe(f"<img width='200' height='200' src='{product.url_video.url}' />")

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTVIDEOS_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'PRODUCTVIDEOS_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTVIDEOS_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTVIDEOS_MANAGER', 'delete')


class VoucherConditionInline(admin.StackedInline):
    model = VoucherCondition
    extra = 1
    max_num = 1


class VoucherTypeAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'name', 'key']
    search_fields = ['id', 'name', 'key']
    list_filter = ['name']

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHERTYPE_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'VOUCHERTYPE_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHERTYPE_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHERTYPE_MANAGER', 'delete')


class VoucherAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'my_image', 'name', 'code', 'maximum_time_used', 'description', 'active']
    search_fields = ['id', 'name', 'code']
    list_filter = ['name']

    inlines = [VoucherConditionInline]

    def my_image(self, voucher):
        if voucher.img:
            return mark_safe(f"<img width='100' height='100' src='{voucher.img.url}' />")

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHER_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'VOUCHER_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHER_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHER_MANAGER', 'delete')


class VoucherConditionAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'voucher_id', 'order_fee_min', 'voucher_sale', 'voucher_sale_max', 'time_usable',
                    'time_expired']
    search_fields = ['id', 'time_usable', 'time_expired']
    list_filter = ['id', 'order_fee_min', 'voucher_sale_max', 'time_usable', 'time_expired']

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHERCONDITION_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'VOUCHERCONDITION_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHERCONDITION_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'VOUCHERCONDITION_MANAGER', 'delete')


class StatusConfirmationShopAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'status_content']
    search_fields = ['id', 'status_content']
    list_filter = ['status_content']

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'STATUSCONFIRMATIONSHOP_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'STATUSCONFIRMATIONSHOP_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'STATUSCONFIRMATIONSHOP_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'STATUSCONFIRMATIONSHOP_MANAGER', 'delete')


class ConfirmationShopAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['id', 'citizen_identification_image1', 'avatar', 'username', 'birthday', 'phone', 'status_content1',
                    'note']
    search_fields = ['username', 'phone']
    list_filter = ['status_id']

    fieldsets = (
        ("Results", {'fields': ('status', 'note',)}),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        confirmationshop = ConfirmationShop.objects.filter(user_id=request.user.id)
        if confirmationshop and not request.user.is_superuser:
            # Lấy queryset mặc định
            queryset = queryset.filter(user=request.user)
            return queryset

        return queryset

    def avatar(self, confirmationshop):
        user = User.objects.get(id=confirmationshop.user_id)
        if user.avatar:
            return mark_safe(
                f"<img width='100' height='100' src='{user.avatar.url}' />")

    def citizen_identification_image1(self, confirmationshop):
        if confirmationshop.citizen_identification_image:
            return mark_safe(
                f"<img width='200' height='100' src='{confirmationshop.citizen_identification_image.url}' />")

    def status_content1(self, confirmationshop):
        status = StatusConfirmationShop.objects.get(id=confirmationshop.status_id)
        return status.status_content

    def username(self, confirmationshop):
        user = User.objects.get(id=confirmationshop.user_id)
        return user.username

    def birthday(self, confirmationshop):
        user = User.objects.get(id=confirmationshop.user_id)
        return user.birthday

    def phone(self, confirmationshop):
        user = User.objects.get(id=confirmationshop.user_id)
        return user.phone

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'CONFIRMATIONSHOP_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'CONFIRMATIONSHOP_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'CONFIRMATIONSHOP_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'CONFIRMATIONSHOP_MANAGER', 'delete')


admin.site.register([User], CustomUserAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Shop, ShopAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductInfo, ProductInfoAdmin)
admin.site.register(ProductImageDetail, ProductImageDetailAdmin)
admin.site.register(ProductImagesColors, ProductImagesColorsAdmin)
admin.site.register(ProductVideos, ProductVideosAdmin)
admin.site.register(VoucherType, VoucherTypeAdmin)
admin.site.register(Voucher, VoucherAdmin)
admin.site.register(VoucherCondition, VoucherConditionAdmin)
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(StatusConfirmationShop, StatusConfirmationShopAdmin)
admin.site.register(ConfirmationShop, ConfirmationShopAdmin)
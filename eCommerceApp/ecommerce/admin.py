from django.contrib import admin
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.utils.html import mark_safe
from .models import *
from django.contrib.auth.models import Group, Permission
from django.db.models import QuerySet
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Count, Sum
from django.db.models.functions import ExtractYear, ExtractMonth, ExtractQuarter

APP_NAME = "ecommerce"


class MyAdminSite(admin.AdminSite):
    site_header = 'eCommerce'

    def get_urls(self):
        return [path('ecommerce-stats', self.stats_view)] + super().get_urls()

    def stats_view(self, request):
        year = request.GET.get('year')
        period = request.GET.get('period')
        stats = OrderDetail.objects.annotate(i1=ExtractYear('order_date')).values('i1').annotate(
            i2=Count('order__product')).values('i1', 'i2').order_by('i1')
        stats2 = OrderDetail.objects.annotate(i1=ExtractYear('order_date')).values('i1').annotate(
            i2=Sum('order__final_amount')).values('i1', 'i2').order_by('i1')
        if year and not period:
            stats = OrderDetail.objects.annotate(i1=ExtractYear('order_date')).filter(i1=year).values(
                'i1').annotate(
                i2=Count('order__product')).values('i1', 'i2').order_by('i1')
            stats2 = OrderDetail.objects.annotate(i1=ExtractYear('order_date')).filter(i1=year).values(
                'i1').annotate(
                i2=Sum('order__final_amount')).values('i1', 'i2').order_by('i1')
        elif year and period == "MONTH":
            stats = OrderDetail.objects.annotate(i1=ExtractMonth('order_date')).filter(order_date__year=year).values(
                'i1').annotate(i2=Count('order__product_id')).values('i1', 'i2').order_by('i1')
            stats2 = OrderDetail.objects.annotate(i1=ExtractMonth('order_date')).filter(order_date__year=year).values(
                'i1').annotate(i2=Sum('order__final_amount')).values('i1', 'i2').order_by('i1')
        elif year and period == "QUARTER":
            stats = OrderDetail.objects.annotate(i1=ExtractQuarter('order_date')).filter(order_date__year=year).values(
                'i1').annotate(i2=Count('order__product_id')).values('i1', 'i2').order_by('i1')
            stats2 = OrderDetail.objects.annotate(i1=ExtractQuarter('order_date')).filter(order_date__year=year).values(
                'i1').annotate(i2=Sum('order__final_amount')).values('i1', 'i2').order_by('i1')

        return TemplateResponse(request, 'admin/stats.html', {
            'stats': stats,
            'stats2': stats2
        })


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
    list_display = ['id', 'name', 'following', 'followed', 'rated', 'user_id', 'my_image', 'active']
    search_fields = ['id', 'name']
    list_filter = ['active', 'rated']
    readonly_fields = ['following', 'followed', 'rated', 'user_id', 'user']

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
    min_num = 1
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
    min_num = 1
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product" and not request.user.is_superuser:
            shop = Shop.objects.filter(user_id=request.user.id).first()
            kwargs["queryset"] = Product.objects.filter(shop_id=shop.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product" and not request.user.is_superuser:
            shop = Shop.objects.filter(user_id=request.user.id).first()
            kwargs["queryset"] = Product.objects.filter(shop_id=shop.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product" and not request.user.is_superuser:
            shop = Shop.objects.filter(user_id=request.user.id).first()
            kwargs["queryset"] = Product.objects.filter(shop_id=shop.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product" and not request.user.is_superuser:
            shop = Shop.objects.filter(user_id=request.user.id).first()
            kwargs["queryset"] = Product.objects.filter(shop_id=shop.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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


class ProductSellAdmin(BasePermissionChecker, admin.ModelAdmin):
    list_display = ['sold_quantity', 'percent_sale', 'rating', ]
    search_fields = ['sold_quantity', 'percent_sale', 'rating', ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product" and not request.user.is_superuser:
            shop = Shop.objects.filter(user_id=request.user.id).first()
            kwargs["queryset"] = Product.objects.filter(shop_id=shop.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
            return ProductSell.objects.none()

        return queryset

    def has_view_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTSELL_MANAGER', 'view')

    def has_add_permission(self, request):
        return self.has_permission(request, 'PRODUCTSELL_MANAGER', 'add')

    def has_change_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTSELL_MANAGER', 'change')

    def has_delete_permission(self, request, obj=None):
        return self.has_permission(request, 'PRODUCTSELL_MANAGER', 'delete')


# class VoucherConditionInline(admin.StackedInline):
#     model = VoucherCondition
#     extra = 1
#     max_num = 1


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


# class VoucherAdmin(BasePermissionChecker, admin.ModelAdmin):
#     list_display = ['id', 'my_image', 'name', 'code', 'maximum_time_used', 'description', 'active']
#     search_fields = ['id', 'name', 'code']
#     list_filter = ['name']
#
#     inlines = [VoucherConditionInline]
#
#     def my_image(self, voucher):
#         if voucher.img:
#             return mark_safe(f"<img width='100' height='100' src='{voucher.img.url}' />")
#
#     def has_view_permission(self, request, obj=None):
#         return self.has_permission(request, 'VOUCHER_MANAGER', 'view')
#
#     def has_add_permission(self, request):
#         return self.has_permission(request, 'VOUCHER_MANAGER', 'add')
#
#     def has_change_permission(self, request, obj=None):
#         return self.has_permission(request, 'VOUCHER_MANAGER', 'change')
#
#     def has_delete_permission(self, request, obj=None):
#         return self.has_permission(request, 'VOUCHER_MANAGER', 'delete')


# class VoucherConditionAdmin(BasePermissionChecker, admin.ModelAdmin):
#     list_display = ['id', 'voucher_id', 'order_fee_min', 'voucher_sale', 'voucher_sale_max', 'time_usable',
#                     'time_expired']
#     search_fields = ['id', 'time_usable', 'time_expired']
#     list_filter = ['id', 'order_fee_min', 'voucher_sale_max', 'time_usable', 'time_expired']
#
#     def has_view_permission(self, request, obj=None):
#         return self.has_permission(request, 'VOUCHERCONDITION_MANAGER', 'view')
#
#     def has_add_permission(self, request):
#         return self.has_permission(request, 'VOUCHERCONDITION_MANAGER', 'add')
#
#     def has_change_permission(self, request, obj=None):
#         return self.has_permission(request, 'VOUCHERCONDITION_MANAGER', 'change')
#
#     def has_delete_permission(self, request, obj=None):
#         return self.has_permission(request, 'VOUCHERCONDITION_MANAGER', 'delete')


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

    actions = ['confirm_and_assign_permission']

    def confirm_and_assign_permission(self, request, queryset):
        # Danh sách các tên nhóm cần gán quyền
        group_names = ['CATEGORY_MANAGER', 'PRODUCT_MANAGER', 'PRODUCTIMAGEDETAIL_MANAGER',
                       'PRODUCTIMAGESCOLORS_MANAGER', 'PRODUCTINFO_MANAGER', 'PRODUCTVIDEOS_MANAGER',
                       'PRODUCTSELL_MANAGER', 'SHOP_MANAGER', 'VENDOR_MANAGER', ]

        # Danh sách các tên quyền cần gán
        permissions_to_assign = ['view_category', 'view_product', 'add_product', 'change_product', 'delete_product',
                                 'view_shop',
                                 'change_shop', 'view_productinfo', 'add_productinfo', 'change_productinfo',
                                 'delete_productinfo', 'view_productvideos', 'add_productvideos',
                                 'change_productvideos',
                                 'delete_productvideos', 'view_productimagedetail', 'add_productimagedetail',
                                 'change_productimagedetail', 'delete_productimagedetail', 'view_productimagescolors',
                                 'add_productimagescolors', 'change_productimagescolors',
                                 'delete_productimagescolors', 'view_productsell', 'add_productsell',
                                 'change_productsell', 'delete_productsell']

        # Lặp qua từng người dùng trong queryset
        for obj in queryset:

            if obj.status_id == 1:
                return

            # Lặp qua từng nhóm và thêm người dùng vào từng nhóm
            user = User.objects.get(id=obj.user_id)

            user.is_vendor = True
            user.is_staff = True

            shop = Shop()
            shop.img = 'https://res.cloudinary.com/diwxda8bi/image/upload/v1712904005/default-avatar-icon-of-social-media-user-vector_nr0hob.jpg'
            shop.active = True
            shop.name = user.username
            shop.user_id = user.id
            try:
                for group_name in group_names:
                    # Lấy nhóm
                    group = Group.objects.get(name=group_name)
                    # Thêm người dùng vào nhóm
                    group.user_set.add(user)

                # Gán quyền cá nhân cho người dùng từ danh sách tên quyền
                for permission_name in permissions_to_assign:
                    permission = Permission.objects.get(codename=permission_name)
                    user.user_permissions.add(permission)
            except Exception as ex:
                print(ex)

            user.save()
            shop.save()

        # Cập nhật trường status của các đối tượng được chọn thành Status có id là 1
        queryset.update(status_id=1)

    confirm_and_assign_permission.short_description = "Phê duyệt thành công"

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


admin.site = MyAdminSite(name='eCommerceApp')

admin.site.register([User], CustomUserAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Shop, ShopAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductInfo, ProductInfoAdmin)
admin.site.register(ProductImageDetail, ProductImageDetailAdmin)
admin.site.register(ProductImagesColors, ProductImagesColorsAdmin)
admin.site.register(ProductVideos, ProductVideosAdmin)
admin.site.register(ProductSell, ProductSellAdmin)
# admin.site.register(VoucherType, VoucherTypeAdmin)
# admin.site.register(Voucher, VoucherAdmin)
# admin.site.register(VoucherCondition, VoucherConditionAdmin)
# admin.site.unregister(Group) # khi custom stats thì ko cần nữa
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(StatusConfirmationShop, StatusConfirmationShopAdmin)
admin.site.register(ConfirmationShop, ConfirmationShopAdmin)

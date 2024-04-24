from rest_framework import permissions


class ShopOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, shop):
        return super().has_permission(request, view) and request.user == shop.user
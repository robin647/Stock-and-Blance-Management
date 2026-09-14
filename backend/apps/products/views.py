from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied

from .models import Product, ProductCategory
from .serializers import ProductCategorySerializer, ProductSerializer


class ProductCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in permissions.SAFE_METHODS and request.user.role != "admin":
            raise PermissionDenied("Only Admin can manage product categories.")


class ProductViewSet(viewsets.ModelViewSet):
    """
    Admin: full CRUD over all products (active + inactive).
    Showroom user: read-only, active products only (they need this list to
    log daily stock/sales but must not be able to edit product data).
    """

    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["category", "is_active"]

    def get_queryset(self):
        qs = Product.objects.select_related("category").all()
        if self.request.user.role != "admin":
            qs = qs.filter(is_active=True)
        return qs

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in permissions.SAFE_METHODS and request.user.role != "admin":
            raise PermissionDenied("Only Admin can manage products.")

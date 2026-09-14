from rest_framework import serializers

from .models import DailyBalance, DailyStock, FactoryStock, ShowroomStock, StockTransfer
from .services import InsufficientStock, record_stock_transfer


class FactoryStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = FactoryStock
        fields = ["id", "product", "product_name", "quantity", "updated_at"]
        read_only_fields = ["id", "quantity", "updated_at"]


class ShowroomStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = ShowroomStock
        fields = ["id", "showroom", "showroom_name", "product", "product_name", "quantity", "updated_at"]
        read_only_fields = ["id", "quantity", "updated_at"]


class StockTransferSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    from_location = serializers.SerializerMethodField()
    to_location = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = StockTransfer
        fields = [
            "id", "showroom", "showroom_name", "product", "product_name",
            "transfer_type", "quantity", "date", "notes",
            "created_by", "created_by_username", "created_at",
            "from_location", "to_location", "status",
        ]
        read_only_fields = ["id", "created_by", "created_at"]
        # A showroom user is always assigned to their own showroom by the
        # view/create method, so this field must not be required in the
        # request payload.  Admin users still have to provide it (enforced in
        # StockTransferViewSet.perform_create).
        extra_kwargs = {"showroom": {"required": False}}

    def get_from_location(self, transfer):
        return "Factory/Main Stock" if transfer.transfer_type == "receive" else transfer.showroom.name

    def get_to_location(self, transfer):
        if transfer.transfer_type == "receive":
            return transfer.showroom.name
        if transfer.transfer_type == "return":
            return "Factory/Main Stock"
        return "Customer"

    def get_status(self, transfer):
        return "Completed"

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate(self, attrs):
        showroom = attrs.get("showroom")

        # The showroom UI deliberately does not send a showroom id.  Resolve
        # it from the authenticated user before stock validation so receive,
        # sale, and return all validate against the correct location.
        request = self.context.get("request")
        if request and request.user.role == "showroom_user":
            showroom = request.user.showroom
            attrs["showroom"] = showroom

        return attrs

    def create(self, validated_data):
        # Automatically set showroom for non-admin users
        request = self.context.get("request")
        if request and request.user.role == "showroom_user":
            validated_data["showroom"] = request.user.showroom

        # Set the user who created this transfer
        validated_data["created_by"] = self.context["request"].user
        # The database field is optional, but the transactional service uses
        # an explicit value so API clients may safely omit notes.
        validated_data.setdefault("notes", "")

        try:
            return record_stock_transfer(**validated_data)
        except InsufficientStock as error:
            raise serializers.ValidationError({"quantity": str(error)})


class DailyStockSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = DailyStock
        fields = [
            "id", "showroom", "showroom_name", "product", "product_name", "date",
            "opening_qty", "received_qty", "sold_qty", "return_qty", "closing_qty",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "opening_qty", "closing_qty", "created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        showroom = attrs.get("showroom") or getattr(self.instance, "showroom", None)
        product = attrs.get("product") or getattr(self.instance, "product", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)

        # Ensure product and date are available
        if not product or not date or not showroom:
            raise serializers.ValidationError(
                "Showroom, product, and date are required."
            )

        if DailyStock.objects.filter(showroom=showroom, product=product, date=date).exclude(
            pk=getattr(self.instance, "pk", None)
        ).exists():
            raise serializers.ValidationError(
                "A stock entry for this product on this date already exists for this showroom."
            )
        return attrs

    def create(self, validated_data):
        showroom = validated_data["showroom"]
        product = validated_data["product"]
        date = validated_data["date"]

        previous_entry = (
            DailyStock.objects.filter(showroom=showroom, product=product, date__lt=date)
            .order_by("-date")
            .first()
        )
        validated_data["opening_qty"] = previous_entry.closing_qty if previous_entry else 0
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class DailyBalanceSerializer(serializers.ModelSerializer):
    showroom_name = serializers.CharField(source="showroom.name", read_only=True)

    class Meta:
        model = DailyBalance
        fields = [
            "id", "showroom", "showroom_name", "date",
            "opening_balance", "cash_sale", "card_sale", "total_sale",
            "expense", "salary", "deposit", "closing_balance",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "opening_balance", "total_sale", "closing_balance",
            "created_by", "created_at", "updated_at",
        ]
        # A showroom user is assigned from the authenticated account, not
        # from a client-provided id.
        extra_kwargs = {"showroom": {"required": False}}
        # validate() below checks the same constraint after it resolves the
        # showroom from the authenticated user.
        validators = []

    def validate(self, attrs):
        showroom = attrs.get("showroom") or getattr(self.instance, "showroom", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)

        request = self.context.get("request")
        if request and request.user.role == "showroom_user":
            showroom = request.user.showroom
            attrs["showroom"] = showroom

        if DailyBalance.objects.filter(showroom=showroom, date=date).exclude(
            pk=getattr(self.instance, "pk", None)
        ).exists():
            raise serializers.ValidationError(
                "A balance entry for this date already exists for this showroom."
            )
        return attrs

    def create(self, validated_data):
        showroom = validated_data["showroom"]
        date = validated_data["date"]

        previous_entry = (
            DailyBalance.objects.filter(showroom=showroom, date__lt=date).order_by("-date").first()
        )
        validated_data["opening_balance"] = previous_entry.closing_balance if previous_entry else 0
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

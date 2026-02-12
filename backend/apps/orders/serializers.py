from rest_framework import serializers
from .models import Order, OrderItem
from apps.products.serializers import ProductListSerializer
from apps.shipping.models import ShippingMethod


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_method_name = serializers.CharField(source='shipping_method.name', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status', 'payment_method',
            'subtotal', 'shipping_price', 'tax_amount', 'total', 'items',
            'shipping_method_name', 'created_at', 'updated_at'
        ]


class CreateOrderItemSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CreateOrderSerializer(serializers.ModelSerializer):
    items = CreateOrderItemSerializer(many=True, write_only=True)
    shipping_method = serializers.PrimaryKeyRelatedField(
        queryset=ShippingMethod.objects.filter(is_active=True)
    )

    class Meta:
        model = Order
        fields = [
            'shipping_address', 'billing_address', 'shipping_method',
            'payment_method', 'items', 'subtotal', 'tax_amount', 'total'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        order = Order.objects.create(user=user, **validated_data)

        # Créer les OrderItems
        order_items = []
        for item_data in items_data:
            order_items.append(OrderItem(
                order=order,
                product_id=item_data['product'],
                quantity=item_data['quantity'],
                price=item_data['price']
            ))

        OrderItem.objects.bulk_create(order_items)
        return order
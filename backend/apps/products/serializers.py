# backend/apps/products/serializers.py
from rest_framework import serializers
from .models import Category, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'alt_text', 'is_primary', 'order']

    def get_image_url(self, obj):
        """Retourne l'URL complète de l'image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                # URL absolue avec le domaine
                return request.build_absolute_uri(obj.image.url)
            # Fallback si pas de request
            return obj.image.url
        return None


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'is_active']


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    discount_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'short_description', 'price', 'compare_price',
            'category', 'primary_image', 'discount_percentage', 'in_stock',
            'is_featured', 'created_at'
        ]

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            # Passer le contexte pour avoir les URLs absolues
            return ProductImageSerializer(primary_image, context=self.context).data
        first_image = obj.images.first()
        if first_image:
            return ProductImageSerializer(first_image, context=self.context).data
        return None


class ProductDetailSerializer(ProductListSerializer):
    images = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            'description', 'quantity', 'weight', 'images', 'sku'
        ]

    def get_images(self, obj):
        # S'assurer que les images ont les URLs absolues
        images = obj.images.all()
        return ProductImageSerializer(images, many=True, context=self.context).data
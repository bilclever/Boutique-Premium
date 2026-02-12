# backend/create_sample_data.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.products.models import Category, Product, ProductImage
from apps.shipping.models import ShippingZone, ShippingMethod
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


def create_sample_data():
    print("Création des données de test...")

    # Créer un utilisateur test
    user, created = CustomUser.objects.get_or_create(
        email='test@example.com',
        defaults={
            'username': 'testuser',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'password': 'testpass123'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()

    # Créer des catégories
    categories_data = [
        {'name': 'Électronique', 'slug': 'electronique'},
        {'name': 'Vêtements', 'slug': 'vetements'},
        {'name': 'Maison', 'slug': 'maison'},
        {'name': 'Sport', 'slug': 'sport'},
    ]

    categories = {}
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            slug=cat_data['slug'],
            defaults=cat_data
        )
        categories[cat_data['slug']] = category
        print(f"Catégorie créée: {category.name}")

    # Créer des produits
    products_data = [
        {
            'name': 'Smartphone Premium',
            'slug': 'smartphone-premium',
            'description': 'Un smartphone haut de gamme avec écran AMOLED et triple appareil photo.',
            'short_description': 'Smartphone flagship avec les dernières technologies',
            'price': 899.99,
            'compare_price': 999.99,
            'category': categories['electronique'],
            'sku': 'SMART001',
            'quantity': 50,
            'is_published': True,
            'is_featured': True,
            'weight': 0.2
        },
        {
            'name': 'Casque Audio Bluetooth',
            'slug': 'casque-audio-bluetooth',
            'description': 'Casque audio sans fil avec réduction de bruit active et autonomie de 30h.',
            'short_description': 'Casque sans fil haute performance',
            'price': 199.99,
            'compare_price': 249.99,
            'category': categories['electronique'],
            'sku': 'AUDIO001',
            'quantity': 25,
            'is_published': True,
            'is_featured': True,
            'weight': 0.3
        },
        {
            'name': 'T-shirt Cotton',
            'slug': 't-shirt-cotton',
            'description': 'T-shirt 100% coton biologique, confortable et durable.',
            'short_description': 'T-shirt premium en coton bio',
            'price': 29.99,
            'compare_price': 39.99,
            'category': categories['vetements'],
            'sku': 'TSHIRT001',
            'quantity': 100,
            'is_published': True,
            'is_featured': False,
            'weight': 0.15
        },
        {
            'name': 'Sac à Dos Urbain',
            'slug': 'sac-a-dos-urbain',
            'description': 'Sac à dos design avec compartiment pour ordinateur portable et espace de rangement organisé.',
            'short_description': 'Sac à dos fonctionnel et stylé',
            'price': 79.99,
            'compare_price': 89.99,
            'category': categories['vetements'],
            'sku': 'BAG001',
            'quantity': 30,
            'is_published': True,
            'is_featured': True,
            'weight': 0.8
        }
    ]

    for prod_data in products_data:
        product, created = Product.objects.get_or_create(
            slug=prod_data['slug'],
            defaults=prod_data
        )
        if created:
            print(f"Produit créé: {product.name}")

    # Créer des zones de livraison
    france_zone, created = ShippingZone.objects.get_or_create(
        name='France',
        defaults={'countries': ['FR']}
    )

    # Créer des méthodes de livraison
    shipping_methods = [
        {'name': 'Livraison Standard', 'method_type': 'standard', 'price': 4.99, 'min_days': 3, 'max_days': 5},
        {'name': 'Livraison Express', 'method_type': 'express', 'price': 9.99, 'min_days': 1, 'max_days': 2},
        {'name': 'Livraison Gratuite', 'method_type': 'standard', 'price': 0, 'min_days': 4, 'max_days': 7},
    ]

    for method_data in shipping_methods:
        method, created = ShippingMethod.objects.get_or_create(
            name=method_data['name'],
            zone=france_zone,
            defaults=method_data
        )
        if created:
            print(f"Méthode de livraison créée: {method.name}")

    print("Données de test créées avec succès!")


if __name__ == '__main__':
    create_sample_data()
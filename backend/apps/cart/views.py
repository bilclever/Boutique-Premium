# backend/apps/cart/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from apps.products.models import Product


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # S'assurer qu'on filtre par l'utilisateur connecté
        return Cart.objects.filter(user=self.request.user).prefetch_related('items__product')

    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        """Récupérer le panier de l'utilisateur connecté"""
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(cart)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la récupération du panier: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Ajouter un article au panier"""
        try:
            # Vérifier l'authentification
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Utilisateur non authentifié'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            product_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1)

            # Validation des données
            if not product_id:
                return Response(
                    {'error': 'product_id est requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return Response(
                    {'error': 'quantity doit être un nombre'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Récupérer ou créer le panier
            cart, created = Cart.objects.get_or_create(user=request.user)

            # Vérifier que le produit existe
            from apps.products.models import Product
            try:
                product = Product.objects.get(id=product_id, is_published=True)
            except Product.DoesNotExist:
                return Response(
                    {'error': 'Produit non trouvé'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Vérifier le stock
            if product.quantity < quantity:
                return Response(
                    {'error': 'Stock insuffisant'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Ajouter ou mettre à jour l'article
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            # Retourner le panier mis à jour
            serializer = CartSerializer(cart, context={'request': request})

            return Response(serializer.data)

        except Exception as e:
            return Response(
                {'error': f'Erreur serveur: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """Mettre à jour la quantité d'un article"""
        try:
            cart = Cart.objects.get(user=request.user)
            product_id = request.data.get('product_id')
            quantity = int(request.data.get('quantity', 1))

            try:
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
                if quantity <= 0:
                    cart_item.delete()
                else:
                    cart_item.quantity = quantity
                    cart_item.save()

                serializer = CartSerializer(cart)
                return Response(serializer.data)

            except CartItem.DoesNotExist:
                return Response(
                    {'error': 'Article non trouvé dans le panier'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Cart.DoesNotExist:
            return Response(
                {'error': 'Panier non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la mise à jour: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """Supprimer un article du panier"""
        try:
            cart = Cart.objects.get(user=request.user)
            product_id = request.data.get('product_id')

            try:
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
                cart_item.delete()

                serializer = CartSerializer(cart)
                return Response(serializer.data)

            except CartItem.DoesNotExist:
                return Response(
                    {'error': 'Article non trouvé dans le panier'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Cart.DoesNotExist:
            return Response(
                {'error': 'Panier non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Vider le panier"""
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()

            serializer = CartSerializer(cart)
            return Response(serializer.data)

        except Cart.DoesNotExist:
            return Response(
                {'error': 'Panier non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
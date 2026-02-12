# backend/apps/users/views.py
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser
from .serializers import UserSerializer, RegisterSerializer

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

@swagger_auto_schema(
    method='post',
    operation_description="Login to get authentication token",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'password'],
        properties={
            'email': openapi.Schema(
                type=openapi.TYPE_STRING,
                format='email',
                example="bil@gmail.com"
            ),
            'password': openapi.Schema(
                type=openapi.TYPE_STRING,
                format='password',
                example="sanoussi"
            ),
        },
    ),
    responses={
        200: openapi.Response(
            description="Login successful",
            examples={
                "application/json": {
                    "token": "abc123def456",
                    "user_id": 1,
                    "email": "bil@gmail.com"
                }
            }
        ),
    }
)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    # Accepter soit 'email' soit 'username'
    email = request.data.get('email')
    username = request.data.get('username')
    password = request.data.get('password')

    # Utiliser l'email comme username si c'est ce qui est envoyé
    login_username = username or email

    if not login_username or not password:
        return Response(
            {'error': 'Identifiants requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=login_username, password=password)

    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })
    else:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh_token')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(status=status.HTTP_205_RESET_CONTENT)
    except Exception as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)
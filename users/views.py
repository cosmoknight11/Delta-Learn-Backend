from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .serializers import RegisterSerializer, UserSerializer


@extend_schema(tags=['Auth'])
class RegisterView(generics.CreateAPIView):
    """Create a new user account."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=['Auth'])
class MeView(APIView):
    """Get the currently authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import Society, Block, Flat, ResidentFlatMapping
from .serializers import (
    SocietySerializer,
    BlockSerializer,
    FlatSerializer,
    ResidentFlatMappingSerializer,
)
from users.permissions import IsAdminRole, IsAdminOrReadOnly


# ──────────────────────────── Society ────────────────────────────

class SocietyListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/society/          — list all societies (authenticated users)
    POST /api/society/          — register a new society (admin only)
    """
    queryset = Society.objects.filter(is_active=True)
    serializer_class = SocietySerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'city', 'registration_number']


class SocietyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/society/<pk>/   — retrieve a society
    PATCH  /api/society/<pk>/   — update (admin only)
    DELETE /api/society/<pk>/   — soft delete by marking is_active=False (admin only)
    """
    queryset = Society.objects.all()
    serializer_class = SocietySerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()


# ──────────────────────────── Block ────────────────────────────

class BlockListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/society/<society_pk>/blocks/   — list blocks
    POST /api/society/<society_pk>/blocks/   — add a block (admin only)
    """
    serializer_class = BlockSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        return Block.objects.filter(
            society_id=self.kwargs['society_pk']
        )

    def perform_create(self, serializer):
        serializer.save(society_id=self.kwargs['society_pk'])


class BlockDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/blocks/<pk>/
    PATCH  /api/blocks/<pk>/
    DELETE /api/blocks/<pk>/
    """
    queryset = Block.objects.all()
    serializer_class = BlockSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]


# ──────────────────────────── Flat ────────────────────────────

class FlatListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/blocks/<block_pk>/flats/   — list flats in a block
    POST /api/blocks/<block_pk>/flats/   — add a flat (admin only)
    """
    serializer_class = FlatSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        return Flat.objects.filter(block_id=self.kwargs['block_pk'])

    def perform_create(self, serializer):
        serializer.save(block_id=self.kwargs['block_pk'])


class FlatDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/flats/<pk>/
    PATCH  /api/flats/<pk>/
    DELETE /api/flats/<pk>/
    """
    queryset = Flat.objects.all()
    serializer_class = FlatSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]


# ──────────────────────────── Resident–Flat Mapping ────────────────────────────

class ResidentFlatMappingListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/mappings/   — list mappings (admin sees all; residents see own)
    POST /api/mappings/   — map a resident to a flat (admin only)
    """
    serializer_class = ResidentFlatMappingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return ResidentFlatMapping.objects.all()
        return ResidentFlatMapping.objects.filter(user=user)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]


class ResidentFlatMappingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/mappings/<pk>/
    PATCH  /api/mappings/<pk>/
    DELETE /api/mappings/<pk>/
    """
    queryset = ResidentFlatMapping.objects.all()
    serializer_class = ResidentFlatMappingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def perform_update(self, serializer):
        instance = serializer.save()
        # Sync is_occupied on the flat
        flat = instance.flat
        flat.is_occupied = flat.residents.filter(is_active=True).exists()
        flat.save()

    def perform_destroy(self, instance):
        flat = instance.flat
        instance.delete()
        flat.is_occupied = flat.residents.filter(is_active=True).exists()
        flat.save()

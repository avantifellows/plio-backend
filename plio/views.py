from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from plio.models import Video, Plio, Item, Question
from plio.serializers import (
    VideoSerializer,
    PlioSerializer,
    ItemSerializer,
    QuestionSerializer,
)


class VideoViewSet(viewsets.ModelViewSet):
    """
    Video ViewSet description

    list: List all videos
    retrieve: Retrieve a video
    update: Update a video
    create: Create a video
    partial_update: Patch a video
    destroy: Soft delete a video
    """

    queryset = Video.objects.all()
    serializer_class = VideoSerializer


class PlioViewSet(viewsets.ModelViewSet):
    """
    Plio ViewSet description

    list: List all plios
    retrieve: Retrieve a plio's details based on authenticated user
    update: Update a plio
    create: Create a plio
    partial_update: Patch a plio
    destroy: Soft delete a plio
    play: Retrieve a plio in order to play
    """

    serializer_class = PlioSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        queryset = Plio.objects.filter(created_by=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def list_uuid(self, request):
        """Retrieves a list of UUIDs for all the plios"""
        value_queryset = self.get_queryset().values_list("uuid", flat=True)
        return Response(list(value_queryset))

    @action(methods=["get"], detail=True, permission_classes=[IsAuthenticated])
    def play(self, request, uuid):
        queryset = Plio.objects.filter(uuid=uuid)
        queryset = queryset.filter(is_public=True) | queryset.filter(
            created_by=self.request.user
        )
        plio = queryset.first()
        if not plio:
            return Response(
                {"detail": "Plio not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(plio)
        return Response(serializer.data)

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    def duplicate(self, request, uuid):
        """Creates a clone of the plio with the given uuid"""
        plio = self.get_object()
        # django will auto-generate the key when the key is set to None
        plio.pk = None
        plio.uuid = None
        plio.status = "draft"  # a duplicated plio will always be in "draft" mode
        plio.save()
        return Response(self.get_serializer(plio).data)


class ItemViewSet(viewsets.ModelViewSet):
    """
    Item ViewSet description

    list: List all items
    retrieve: Retrieve an item
    update: Update an item
    create: Create an item
    partial_update: Patch an item
    destroy: Soft delete an item
    """

    serializer_class = ItemSerializer

    def get_queryset(self):
        queryset = Item.objects.all()
        plio_id = self.request.query_params.get("plio")
        if plio_id is not None:
            queryset = queryset.filter(plio__uuid=plio_id).order_by("time")
        return queryset

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    def duplicate(self, request, pk):
        """Creates a clone of the item with the given pk"""
        item = self.get_object()
        item.pk = None
        item.save()
        return Response(self.get_serializer(item).data)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    Question ViewSet description

    list: List all questions
    retrieve: Retrieve a question
    update: Update a question
    create: Create a question
    partial_update: Patch a question
    destroy: Soft delete a question
    """

    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    def duplicate(self, request, pk):
        """Creates a clone of the question with the given pk"""
        question = self.get_object()
        question.pk = None
        question.save()
        return Response(self.get_serializer(question).data)

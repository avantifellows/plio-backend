from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
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
    retrieve: Retrieve a plio
    update: Update a plio
    create: Create a plio
    partial_update: Patch a plio
    destroy: Soft delete a plio
    """

    serializer_class = PlioSerializer
    lookup_field = "uuid"

    @action(detail=False)
    def list_uuid(self, request):
        # retrieve a list of all plio uuids
        q = self.get_queryset().values_list("uuid", flat=True)
        return Response(list(q))

    def get_queryset(self):
        queryset = Plio.objects.all()
        user_id = self.request.query_params.get("user")
        if user_id is not None:
            queryset = queryset.filter(created_by__id=user_id)
        return queryset


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

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_tenants.utils import get_public_schema_name
from django.db.models import Count, Q
from plio.models import Video, Plio, Item, Question
from organizations.middleware import OrganizationTenantMiddleware
from users.models import OrganizationUser
from entries.models import Session
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
        organization_shortcode = OrganizationTenantMiddleware.get_organization(
            self.request
        )

        # personal workspace
        if organization_shortcode == get_public_schema_name():
            return Plio.objects.filter(created_by=self.request.user)

        # organizational workspace
        if (
            self.request.user.is_authenticated
            and OrganizationUser.objects.filter(
                organization__shortcode=organization_shortcode,
                user=self.request.user.id,
            ).exists()
        ):
            # user should be authenticated and a part of the org
            return Plio.objects.filter(
                Q(is_public=True)
                | (Q(is_public=False) & Q(created_by=self.request.user))
            )

        return None

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(created_by=self.get_object().created_by)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def list_uuid(self, request):
        """Retrieves a list of UUIDs for all the plios"""
        queryset = self.get_queryset()
        if not queryset or not queryset.exists():
            return Response([])
        return Response(list(queryset.values_list("uuid", flat=True)))

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

    @action(methods=["get"], detail=True, permission_classes=[IsAuthenticated])
    def unique_users(self, request, uuid):
        """Returns the number of unique users who have watched the specified plio"""
        session_queryset = Session.objects.filter(plio__uuid=uuid)
        return Response(
            session_queryset.aggregate(Count("user__id", distinct=True))[
                "user__id__count"
            ]
        )


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
        """
        Creates a clone of the item with the given pk and links it to the plio
        that's provided in the payload
        """
        item = self.get_object()
        item.pk = None
        plio_id = self.request.data.get("plioId")
        if not plio_id:
            return Response(
                {"detail": "Plio id not passed in the payload."},
                status=status.HTTP_404_NOT_FOUND,
            )

        plio = Plio.objects.filter(id=plio_id).first()
        if not plio:
            return Response(
                {"detail": "Specified plio not found"}, status=status.HTTP_404_NOT_FOUND
            )

        item.plio = plio
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
        """
        Creates a clone of the question with the given pk and links it to the item
        that is provided in the payload
        """
        question = self.get_object()
        question.pk = None
        item_id = self.request.data.get("itemId")
        if not item_id:
            return Response(
                {"details": "Item id not passed in the payload"},
                status=status.HTTP_404_NOT_FOUND,
            )
        item = Item.objects.filter(id=item_id).first()
        if not item:
            return Response(
                {"detail": "Specified item not found"}, status=status.HTTP_404_NOT_FOUND
            )

        question.item = item
        question.save()
        return Response(self.get_serializer(question).data)

import os
import shutil
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import connection
from django.db.models import Q
from django.http import FileResponse
import pandas as pd
from organizations.middleware import OrganizationTenantMiddleware
from users.models import OrganizationUser
from plio.models import Video, Plio, Item, Question
from plio.serializers import (
    VideoSerializer,
    PlioSerializer,
    ItemSerializer,
    QuestionSerializer,
)
from plio.settings import DEFAULT_TENANT_SHORTCODE
from plio.queries import (
    get_plio_details_query,
    get_sessions_dump_query,
    get_responses_dump_query,
    get_events_query,
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
        organization_shortcode = (
            OrganizationTenantMiddleware.get_organization_shortcode(self.request)
        )

        # personal workspace
        if organization_shortcode == DEFAULT_TENANT_SHORTCODE:
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
                {"detail": "Plio not found"}, status=status.HTTP_404_NOT_FOUND
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
    def download_data(self, request, uuid):
        # return 404 if user cannot access the object
        # else fetch the object
        plio = self.get_object()

        # handle draft plios
        if plio.status == "draft":
            return Response(
                {"detail": "Data dumps are not available for draft plios"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # define the directory which will hold the data dump
        data_dump_dir = f"/tmp/plio-{uuid}/user-{request.user.id}"

        # delete the directory if it exists and create a new one
        if os.path.exists(data_dump_dir):
            shutil.rmtree(data_dump_dir)
        os.makedirs(data_dump_dir)

        # schema name to query in
        schema_name = OrganizationTenantMiddleware().get_schema(self.request)

        def save_query_results(query_method, filename):
            # execute the query
            cursor.execute(query_method(uuid, schema=schema_name))
            # extract column names as cursor.description returns a tuple
            columns = [col[0] for col in cursor.description]
            # create a dataframe from the rows and the columns and save to csv
            df = pd.DataFrame(cursor.fetchall(), columns=columns)
            df.to_csv(os.path.join(data_dump_dir, filename), index=False)

        # create the individual dump files
        with connection.cursor() as cursor:
            save_query_results(get_sessions_dump_query, "sessions.csv")
            save_query_results(get_responses_dump_query, "responses.csv")
            save_query_results(get_plio_details_query, "plio-interaction-details.csv")
            save_query_results(get_events_query, "events.csv")

            df = pd.DataFrame(
                [[plio.uuid, plio.name, plio.video.url]],
                columns=["id", "name", "video"],
            )
            df.to_csv(os.path.join(data_dump_dir, "plio-meta-details.csv"), index=False)

        # create the zip
        shutil.make_archive(data_dump_dir, "zip", data_dump_dir)

        # read the zip
        zip_file = open(f"{data_dump_dir}.zip", "rb")

        # create the response
        response = FileResponse(zip_file, as_attachment=True)
        return response


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

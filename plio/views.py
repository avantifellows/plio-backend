import os
import shutil
from copy import deepcopy

from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db import connection
from django.db.models import Q
from django.http import FileResponse
import pandas as pd
from storages.backends.s3boto3 import S3Boto3Storage
from organizations.middleware import OrganizationTenantMiddleware
from users.models import OrganizationUser
from plio.models import Video, Plio, Item, Question, Image
from plio.serializers import (
    VideoSerializer,
    PlioSerializer,
    ItemSerializer,
    QuestionSerializer,
    ImageSerializer,
)
from plio.settings import DEFAULT_TENANT_SHORTCODE, AWS_STORAGE_BUCKET_NAME
from plio.queries import (
    get_plio_details_query,
    get_sessions_dump_query,
    get_responses_dump_query,
    get_events_query,
)
from plio.permissions import PlioPermission
from plio.ordering import CustomOrderingFilter


class StandardResultsSetPagination(PageNumberPagination):
    """
    Splits result sets into individual pages of data.
    Pagination links are provided as part of the content
    of the response.

    Reference: django-rest-framework.org/api-guide/pagination/
    """

    # number of results in a page
    page_size = 5

    def get_paginated_response(self, data):
        # a paginated response will follow this structure
        return Response(
            {
                "count": self.page.paginator.count,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
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

    permission_classes = [IsAuthenticated, PlioPermission]
    serializer_class = PlioSerializer
    lookup_field = "uuid"

    # set which pagination class to use, as no global pagination class is set
    pagination_class = StandardResultsSetPagination

    # define the filter backends to use
    # this inlcludes the search filtering and ordering
    filter_backends = [
        filters.SearchFilter,
        CustomOrderingFilter,
    ]

    # match the search query with the values of these fields
    search_fields = [
        "name",
        "status",
        "updated_at",
        "uuid",
    ]

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
        queryset = self.filter_queryset(self.get_queryset())
        uuid_list = queryset.values_list("uuid", flat=True)
        page = self.paginate_queryset(uuid_list)

        if page is not None:
            return self.get_paginated_response(page)

        # return an empty response in the paginated format if pagination fails
        return Response(
            {
                "count": 0,
                "page_size": self.get_page_size(self.request),
                "next": None,
                "previous": None,
                "results": [],
            }
        )

    @action(
        methods=["get"],
        detail=True,
        permission_classes=[IsAuthenticated, PlioPermission],
    )
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

    @action(
        methods=["post"],
        detail=True,
        permission_classes=[IsAuthenticated, PlioPermission],
    )
    def duplicate(self, request, uuid):
        """Creates a clone of the plio with the given uuid"""
        plio = self.get_object()
        # django will auto-generate the key when the key is set to None
        plio.pk = None
        plio.uuid = None
        plio.status = "draft"  # a duplicated plio will always be in "draft" mode
        plio.save()
        return Response(self.get_serializer(plio).data)

    @action(
        methods=["get"],
        detail=True,
        permission_classes=[IsAuthenticated, PlioPermission],
    )
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

        def save_query_results(cursor, query_method, filename):
            # execute the query
            cursor.execute(query_method(uuid, schema=schema_name))
            # extract column names as cursor.description returns a tuple
            columns = [col[0] for col in cursor.description]
            # create a dataframe from the rows and the columns and save to csv
            df = pd.DataFrame(cursor.fetchall(), columns=columns)
            df.to_csv(os.path.join(data_dump_dir, filename), index=False)

        # create the individual dump files
        with connection.cursor() as cursor:
            save_query_results(cursor, get_sessions_dump_query, "sessions.csv")
            save_query_results(cursor, get_responses_dump_query, "responses.csv")
            save_query_results(
                cursor, get_plio_details_query, "plio-interaction-details.csv"
            )
            save_query_results(cursor, get_events_query, "events.csv")

            df = pd.DataFrame(
                [[plio.uuid, plio.name, plio.video.url]],
                columns=["id", "name", "video"],
            )
            df.to_csv(os.path.join(data_dump_dir, "plio-meta-details.csv"), index=False)

            # move the README for the data dump to the directory
            shutil.copyfile(
                "./plio/static/plio/docs/download_csv_README.md",
                os.path.join(data_dump_dir, "README.md"),
            )

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
    permission_classes = [IsAuthenticated, PlioPermission]

    def get_queryset(self):
        organization_shortcode = (
            OrganizationTenantMiddleware.get_organization_shortcode(self.request)
        )

        # personal workspace
        if organization_shortcode == DEFAULT_TENANT_SHORTCODE:
            queryset = Item.objects.filter(plio__created_by=self.request.user)

        elif OrganizationUser.objects.filter(
            organization__shortcode=organization_shortcode,
            user=self.request.user.id,
        ).exists():
            # user should be authenticated and a part of the org
            queryset = Item.objects.all()

        else:
            return None

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
    permission_classes = [IsAuthenticated, PlioPermission]

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

        if question.image:
            # create duplicate for image if the question has an image
            duplicate_image_id = ImageViewSet.as_view({"post": "duplicate"})(
                request=request._request, pk=question.image.id
            ).data["id"]
            question.image = Image.objects.filter(id=duplicate_image_id).first()

        question.item = item
        question.save()
        return Response(self.get_serializer(question).data)


class ImageViewSet(viewsets.ModelViewSet):
    """
    Image ViewSet description

    list: List all image file entries
    retrieve: Retrieve an image file entry
    update: Update an image file entry
    create: Create an image file entry
    partial_update: Patch an image file entry
    destroy: Soft delete a image file entry
    """

    queryset = Image.objects.all()
    serializer_class = ImageSerializer

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    def duplicate(self, request, pk):
        """
        Creates a clone of the image with the given pk
        """
        image = self.get_object()

        # create new image object
        new_image = Image.objects.create(
            alt_text=image.alt_text, url=deepcopy(image.url)
        )
        new_image.save()

        # creating the image at the new path
        s3 = S3Boto3Storage()
        copy_source = {"Bucket": AWS_STORAGE_BUCKET_NAME, "Key": image.url.name}
        s3.bucket.meta.client.copy(
            copy_source, AWS_STORAGE_BUCKET_NAME, new_image.url.name
        )

        return Response(self.get_serializer(new_image).data)

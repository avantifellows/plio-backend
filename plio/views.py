import os
import shutil
from copy import deepcopy
import json

from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db import connection
from django.db.models import Q, Count, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.http import FileResponse

from django_tenants.utils import get_tenant_model

import pandas as pd
from storages.backends.s3boto3 import S3Boto3Storage

from organizations.middleware import OrganizationTenantMiddleware
from organizations.models import Organization
from users.models import OrganizationUser
from plio.models import Video, Plio, Item, Question, Image
from entries.models import Session
from plio.serializers import (
    VideoSerializer,
    PlioSerializer,
    ItemSerializer,
    QuestionSerializer,
    ImageSerializer,
)
from plio.settings import (
    DEFAULT_TENANT_SHORTCODE,
    AWS_STORAGE_BUCKET_NAME,
)
from plio.queries import (
    get_plio_details_query,
    get_sessions_dump_query,
    get_responses_dump_query,
    get_events_query,
    get_plio_latest_sessions_query,
    get_plio_latest_responses_query,
)
from plio.permissions import PlioPermission
from plio.ordering import CustomOrderingFilter
from plio.cache import invalidate_cache_for_instance


class StandardResultsSetPagination(PageNumberPagination):
    """
    Splits result sets into individual pages of data.
    Pagination links are provided as part of the content
    of the response.

    Reference: django-rest-framework.org/api-guide/pagination/
    """

    # number of results in a page
    page_size = 5

    def get_paginated_response(self, params):
        # a paginated response will follow this structure
        return Response(
            {
                "count": self.page.paginator.count,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": params["data"],
                "raw_count": params["raw_count"],
            }
        )


def set_tenant(workspace: str):
    """
    Sets the current tenant to the given workspace if it exists

    :param workspace: workspace shortcode to use as the current tenant
    :type workspace: str
    """
    tenant_model = get_tenant_model()
    tenant = tenant_model.objects.filter(shortcode=workspace).first()

    if not tenant:
        return False

    connection.set_tenant(tenant)
    return True


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
    permission_classes = [IsAuthenticated]


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

    queryset = Plio.objects.all()
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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(created_by=self.get_object().created_by)

    @action(
        detail=True,
        permission_classes=[IsAuthenticated, PlioPermission],
        methods=["patch"],
    )
    def setting(self, request, uuid):
        """Updates a plio's settings"""
        plio = self.get_object()
        plio.config = plio.config if plio.config is not None else {}
        plio.config["settings"] = self.request.data
        plio.save()
        return Response(self.get_serializer(plio).data["config"])

    @property
    def organization_shortcode(self):
        return OrganizationTenantMiddleware.get_organization_shortcode(self.request)

    @property
    def is_organizational_workspace(self):
        return self.organization_shortcode != DEFAULT_TENANT_SHORTCODE

    def list(self, request):
        queryset = self.get_queryset()

        # personal workspace
        if not self.is_organizational_workspace:
            queryset = queryset.filter(created_by=self.request.user)
        else:
            # organizational workspace
            if OrganizationUser.objects.filter(
                organization__shortcode=self.organization_shortcode,
                user=self.request.user.id,
            ).exists():
                # user should be a part of the org
                queryset = queryset.filter(
                    Q(is_public=True)
                    | (Q(is_public=False) & Q(created_by=self.request.user))
                )
            else:
                # otherwise, they don't have access to any plio
                queryset = Plio.objects.none()

        num_plios = queryset.count()

        # add the number of unique viewers to the queryset
        plio_session_group = Session.objects.filter(plio__uuid=OuterRef("uuid")).values(
            "plio__uuid"
        )

        plios_unique_users_count = plio_session_group.annotate(
            count_unique_users=Count("user__id", distinct=True)
        ).values("count_unique_users")

        # annotate the plio's queryset with the count of unique users
        queryset = queryset.annotate(
            unique_viewers=Coalesce(Subquery(plios_unique_users_count), 0)
        )

        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset.values())

        if page is not None:
            # add the items corresponding to the plio in each plio object
            for index, _ in enumerate(page):
                page[index]["items"] = ItemSerializer(
                    queryset[index].item_set, many=True
                ).data

            return self.get_paginated_response({"data": page, "raw_count": num_plios})

        # return an empty response in the paginated format if pagination fails
        return Response(
            {
                "count": 0,
                "raw_count": 0,
                "page_size": self.get_page_size(self.request),
                "next": None,
                "previous": None,
                "results": [],
            }
        )

    @action(
        methods=["get"],
        detail=True,
        permission_classes=[PlioPermission],
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
    )
    def duplicate(self, request, uuid):
        """Creates a clone of the plio with the given uuid"""
        # return 404 if user cannot access the object
        # else fetch the object
        plio = self.get_object()
        # django will auto-generate the key when the key is set to None
        plio.pk = None
        plio.uuid = None
        plio.status = "draft"  # a duplicated plio will always be in "draft" mode
        plio.save()
        return Response(self.get_serializer(plio).data)

    @action(
        methods=["post"],
        detail=True,
    )
    def copy(self, request, uuid):
        """Copies the given plio to another workspace"""
        if "workspace" not in request.data:
            return Response(
                {"detail": "workspace is not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # return 404 if user cannot access the object
        # else fetch the object
        plio = self.get_object()

        if plio.video is not None:
            video = Video.objects.filter(id=plio.video.id).first()
            video.pk = None

            items = list(Item.objects.filter(plio__id=plio.id))
            questions = list(Question.objects.filter(item__plio__id=plio.id))

            # will be needed to handle questions with images
            question_indices_with_image = []
            images = []

            for index, question in enumerate(questions):
                if question.image is not None:
                    question_indices_with_image.append(index)
                    images.append(question.image)
        else:
            video = None
            items = []
            questions = []

        # django will auto-generate the key when the key is set to None
        plio.pk = None
        plio.uuid = None
        plio.status = "draft"

        # change workspace
        workspace = request.data.get("workspace")
        success = set_tenant(workspace)

        if not success:
            return Response(
                {"detail": "workspace does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if video is not None:
            video.save()
            plio.video = video

        plio.save()

        if items:
            # before creating the items in the given workspace, update the
            # plio ids that they are linked to and reset the primary key;
            # django will auto-generate the keys when they are set to None
            for index, _ in enumerate(items):
                items[index].plio = plio
                items[index].pk = None

            # create the items
            items = Item.objects.bulk_create(items)

            # before creating the questions in the given workspace, update the
            # item ids that they are linked to and
            # since we are ordering both items and questions by the item time,
            # questions and items at the same index should be linked
            for index, _ in enumerate(questions):
                questions[index].item = items[index]
                questions[index].pk = None

            # if there are any questions with images, create instances of those images in the
            # new workspace and link them to the question instances that need to be created
            if images:
                for index, _ in enumerate(images):
                    # reset the key - django will auto-generate the keys when they are set to None
                    images[index].pk = None

                images = Image.objects.bulk_create(images)
                for index, question_index in enumerate(question_indices_with_image):
                    questions[question_index].image = images[index]

            # create the questions
            questions = Question.objects.bulk_create(questions)

            # clear the cache for the destination plio or else the items wouldn't show up
            # when the plio is fetched; we need to trigger this manually as bulk_create
            # does not call the post_save signal
            invalidate_cache_for_instance(plio)

        return Response(self.get_serializer(plio).data)

    @action(
        methods=["get"],
        detail=True,
    )
    def metrics(self, request, uuid):
        """Returns usage metrics for the plio"""
        # return 404 if user cannot access the object
        # else fetch the object
        plio = self.get_object()

        # no sessions have been created for the plio: return
        if not Session.objects.filter(plio=plio.id):
            return Response({})

        import numpy as np

        with connection.cursor() as cursor:
            cursor.execute(
                get_plio_latest_sessions_query(plio.uuid, connection.schema_name)
            )
            results = cursor.fetchall()

        df = pd.DataFrame(results, columns=["id", "watch_time", "retention"])

        # number of unique viewers and average watch time
        num_unique_viewers = len(df)
        average_watch_time = df["watch_time"].mean()

        # retention at one minute
        if plio.video.duration is None or plio.video.duration < 60:
            # the metric is not applicable in this case
            percent_one_minute_retention = None
        else:
            # convert "0,1,0" to ["0", "1", "0"]
            df["retention"] = df["retention"].apply(lambda row: row.split(","))

            # remove entries where the retention is either empty or has NaN values
            df["is_retention_valid"] = df["retention"].apply(
                lambda row: ("NaN" not in row and len(row) == plio.video.duration)
            )

            valid_retention_df = df[df["is_retention_valid"]]

            if not len(valid_retention_df):
                percent_one_minute_retention = 0
            else:
                # convert ["0", "1", "0"] to [0, 1, 0]
                retention = (
                    valid_retention_df["retention"]
                    .apply(lambda row: list(map(int, row)))
                    .values
                )
                # create an array out of all the retention values and only
                # retain the values after one minute
                retention = np.vstack(retention)[:, 59:]

                # checks if a given user has crossed the second mark
                percent_one_minute_retention = np.round(
                    ((retention.sum(axis=1) > 0).sum() / num_unique_viewers) * 100, 2
                )

        # question-based metrics
        # import ipdb

        # ipdb.set_trace()
        questions = Question.objects.filter(item__plio=plio.id)

        # if the plio does not have any questions, these metrics are not applicable
        if not questions:
            accuracy = None
            average_num_answered = None
            percent_completed = None

        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    get_plio_latest_responses_query(
                        connection.schema_name, tuple(df["id"])
                    )
                )
                results = cursor.fetchall()

            df = pd.DataFrame(
                results,
                columns=[
                    "id",
                    "user_id",
                    "answer",
                    "item_type",
                    "question_type",
                    "correct_answer",
                    "survey",
                ],
            )

            # retain only the responses to items which are questions
            dff = df[df["survey"] == False].reset_index(drop=True)
            question_df = dff[dff["item_type"] == "question"].reset_index(drop=True)
            num_questions = len(questions)

            def is_answer_correct(row):
                """Whether the answer corresponding to the given row is correct"""
                if row["question_type"] in ["mcq", "checkbox"]:
                    return row["answer"] == row["correct_answer"]
                return row["answer"] is not None

            # holds the number of questions answered for each viewer
            num_answered_list = []
            # holds the number of questions correctly answered for each viewer
            num_correct_list = []

            user_grouping = question_df.groupby("user_id")
            for group in user_grouping.groups:
                # get the responses for a given user
                group_df = user_grouping.get_group(group)

                num_answered = sum(
                    group_df["answer"].apply(lambda value: value is not None)
                )

                num_answered_list.append(num_answered)

                if not num_answered:
                    num_correct_list.append(None)
                else:
                    num_correct_list.append(
                        sum(group_df.apply(is_answer_correct, axis=1))
                    )

            # converting to numpy arrays enabled us to use vectorization
            # to speed up the computation many folds
            num_answered_list = np.array(num_answered_list)
            num_correct_list = np.array(num_correct_list)
            average_num_answered = round(num_answered_list.mean())
            percent_completed = np.round(
                100 * (sum(num_answered_list == num_questions) / num_unique_viewers), 2
            )

            # only use the responses from viewers who have answered at least
            # one question to compute the accuracy
            answered_at_least_one_index = num_answered_list > 0
            num_answered_list = num_answered_list[answered_at_least_one_index]
            num_correct_list = num_correct_list[answered_at_least_one_index]

            if not len(num_correct_list):
                accuracy = None
            else:
                accuracy = np.round(
                    (num_correct_list / num_answered_list).mean() * 100, 2
                )

        return Response(
            {
                "unique_viewers": num_unique_viewers,
                "average_watch_time": average_watch_time,
                "percent_one_minute_retention": percent_one_minute_retention,
                "accuracy": accuracy,
                "average_num_answered": average_num_answered,
                "percent_completed": percent_completed,
            }
        )

    @action(
        methods=["get"],
        detail=True,
    )
    def download_data(self, request, uuid):
        """
        Downloads a zip file containing various CSVs for a Plio.

        request: HTTP request.
        uuid: UUID of the plio for which report needs to be downloaded.
        """
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

        organization = Organization.objects.filter(
            shortcode=self.organization_shortcode,
        ).first()
        is_user_org_admin = organization is not None and request.user.is_org_admin(
            organization.id
        )

        def run_query(cursor, query_method):
            # execute the sql query
            cursor.execute(
                query_method(uuid, schema=schema_name, mask_user_id=is_user_org_admin)
            )
            # extract column names as cursor.description returns a tuple
            columns = [col[0] for col in cursor.description]
            # create a dataframe from the rows and the columns
            df = pd.DataFrame(cursor.fetchall(), columns=columns)

            return df

        def save_query_results(df, filename):
            # save to csv
            df.to_csv(os.path.join(data_dump_dir, filename), index=False)

        def run_and_save_query_results(cursor, query_method, filename):
            df = run_query(cursor, query_method)
            save_query_results(df, filename)

        # create the individual dump files
        with connection.cursor() as cursor:
            # --- sessions --- #
            run_and_save_query_results(cursor, get_sessions_dump_query, "sessions.csv")

            # --- responses --- #
            # change the submitted answers to make them 1-indexed
            df = run_query(cursor, get_responses_dump_query)

            # deserialise the submitted answer values
            answers = pd.Series(df["answer"])
            df.drop(columns="answer", inplace=True)

            valid_answer_indices = answers[~answers.isnull()].index
            answers.loc[valid_answer_indices] = answers[valid_answer_indices].apply(
                json.loads
            )
            df["answer"] = answers

            # find the rows where the question type is MCQ
            # and update the submitted answer there
            df_mcq = df[df["question_type"] == "mcq"]
            df.loc[df_mcq.index, "answer"] = df_mcq["answer"].apply(
                lambda x: x + 1 if x is not None else x
            )

            # find the rows where the question type is checkbox
            # and update the submitted answer there
            df_checkbox = df[df["question_type"] == "checkbox"]
            df.loc[df_checkbox.index, "answer"] = df_checkbox["answer"].apply(
                lambda row: list(map(lambda x: x + 1, row)) if row is not None else row
            )

            save_query_results(df, "responses.csv")

            # --- interaction details --- #
            # change the correct answers to make them 1-indexed
            df = run_query(cursor, get_plio_details_query)

            # deserialise the correct_answer values
            question_correct_answer = df["question_correct_answer"]
            df.drop(columns="question_correct_answer", inplace=True)

            question_correct_answer = question_correct_answer.apply(json.loads)
            df["question_correct_answer"] = question_correct_answer

            # find the rows where the question type is MCQ
            # and update the correct answer there
            df_mcq = df[df["question_type"] == "mcq"]
            df.loc[df_mcq.index, "question_correct_answer"] = df_mcq[
                "question_correct_answer"
            ].apply(lambda x: x + 1)

            # find the rows where the question type is checkbox
            # and update the correct answer there
            df_checkbox = df[df["question_type"] == "checkbox"]
            df.loc[df_checkbox.index, "question_correct_answer"] = df_checkbox[
                "question_correct_answer"
            ].apply(lambda row: list(map(lambda x: x + 1, row)))

            save_query_results(df, "plio-interaction-details.csv")

            # --- events --- #
            run_and_save_query_results(cursor, get_events_query, "events.csv")

            df = pd.DataFrame(
                [[plio.uuid, plio.name, plio.video.url]],
                columns=["id", "name", "video"],
            )
            df.to_csv(os.path.join(data_dump_dir, "plio-meta-details.csv"), index=False)

            # move the README for the data dump to the directory
            shutil.copyfile(
                "./plio/static/plio/docs/download_csv_README.pdf",
                os.path.join(data_dump_dir, "READ-ME-FIRST.pdf"),
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
        queryset = Item.objects.all()
        plio_uuid = self.request.query_params.get("plio")
        if plio_uuid is not None:
            queryset = queryset.filter(plio__uuid=plio_uuid).order_by("time")
        return queryset

    @action(methods=["post"], detail=True)
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

    @action(methods=["delete"], detail=False)
    def bulk_delete(self, request):
        """deletes items whose ids have been provided"""
        if "id" not in request.data:
            return Response(
                {"detail": "item id(s) not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ids_to_delete = request.data["id"]

        # ensure that a list of ids has been provided
        if not isinstance(ids_to_delete, list):
            return Response(
                {"detail": "id should contain a list of item ids to be deleted"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_to_delete = Item.objects.filter(pk__in=ids_to_delete)
        if len(items_to_delete) != len(ids_to_delete):
            return Response(
                {"detail": "one or more of the ids provided do not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        items_to_delete.delete()
        return Response("deletion successful")


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

    @action(methods=["post"], detail=True)
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
    permission_classes = [IsAuthenticated]

    @action(methods=["post"], detail=True)
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

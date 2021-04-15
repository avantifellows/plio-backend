from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from entries.models import Session, SessionAnswer, Event
from entries.serializers import (
    SessionSerializer,
    SessionAnswerSerializer,
    EventSerializer,
)


class SessionViewSet(viewsets.ModelViewSet):
    """
    Session ViewSet description

    list: List all sessions
    retrieve: Retrieve a session
    update: Update a session
    create: Create a session
    partial_update: Patch a session
    destroy: Soft delete a session
    """

    serializer_class = SessionSerializer

    def get_queryset(self):
        queryset = Session.objects.filter(user=self.request.user)

        # filter the sessions based on a particular plio uuid
        plio_uuid = self.request.query_params.get("plio")
        if plio_uuid is not None:
            queryset = queryset.filter(plio__uuid=plio_uuid)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False)
    def unique_users(self, request):
        """Returns the number of unique user ids across all the sessions"""
        return Response(
            self.get_queryset().aggregate(Count("user__id", distinct=True))[
                "user__id__count"
            ]
        )


class SessionAnswerViewSet(viewsets.ModelViewSet):
    """
    SessionAnswer ViewSet description

    list: List all session answers
    retrieve: Retrieve a session answer
    update: Update a session answer
    create: Create a session answer
    partial_update: Patch a session answer
    destroy: Soft delete a session answer
    """

    queryset = SessionAnswer.objects.all()
    serializer_class = SessionAnswerSerializer


class EventViewSet(viewsets.ModelViewSet):
    """
    Event ViewSet description

    list: List all events
    retrieve: Retrieve a event
    update: Update a event
    create: Create a event
    partial_update: Patch a event
    destroy: Soft delete a event
    """

    queryset = Event.objects.all()
    serializer_class = EventSerializer

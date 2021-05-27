from rest_framework.filters import OrderingFilter
from django.db.models import OuterRef, Subquery, Count
from entries.models import Session
from django.db.models.functions import Coalesce


class CustomOrderingFilter(OrderingFilter):
    """
    This class extends the OrderingFilter class provided in
    rest_framework/utils/filters.py

    Two methods are overridden.
    get_ordering(): Retrieves the ordering from the request query params,
                    parses it into a list and checks it against a list of
                    allowed ordering fields. If matched, returns the list

    filter_queryset(): Gets the prepared ordering list from `get_ordering()`,
                       prepares the queryset according to any specific custom
                       ordering implementation, and returns the ordered by queryset

    inspired by: https://stackoverflow.com/questions/40950251/django-rest-ordering-custom
    """

    # define the allowed custom ordering fields
    # any ordering value other than this list will be rejected
    allowed_ordering_fields = ["unique_viewers", "-unique_viewers"]

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(",")]
            # filter out the fields that are not allowed
            ordering = [f for f in fields if f in self.allowed_ordering_fields]
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            # if the ordering fields contain "unique_viewers"
            if any("unique_viewers" in orderBy for orderBy in ordering):
                # prepare a session queryset which has an annotated field "count_unique_users"
                # that holds the count of unique users for every plio in the plio's queryset
                session_queryset = Session.objects.filter(
                    plio__uuid=OuterRef("uuid")
                ).values("plio__uuid")

                session_queryset = session_queryset.annotate(
                    count_unique_users=Count("user__id", distinct=True)
                ).values("count_unique_users")

                # annotate the plio's queryset with the count of unique users
                queryset = queryset.annotate(
                    unique_viewers=Coalesce(Subquery(session_queryset), 0)
                )

            return queryset.order_by(*ordering)

        return queryset

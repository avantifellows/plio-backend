from rest_framework.filters import OrderingFilter


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
                       ordering implementation, and returns the ordered queryset

    inspired by: https://stackoverflow.com/questions/40950251/django-rest-ordering-custom
    """

    # define the allowed custom ordering fields
    # any ordering value other than this list will be rejected
    allowed_ordering_fields = ["unique_viewers", "name", "updated_at", "created_at"]
    # set the default ordering
    default_ordering = ["-updated_at"]

    def get_ordering(self, request, queryset, view):
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(",")]

            def is_valid_field(field):
                if field.startswith("-"):
                    field = field[1:]
                return field in self.allowed_ordering_fields

            # filter out the fields that are not allowed
            ordering = [field for field in fields if is_valid_field(field)]
            if ordering:
                return ordering

        # no ordering was included, or all the ordering fields were invalid
        setattr(view, "ordering", self.default_ordering)
        return self.get_default_ordering(view)

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            return queryset.order_by(*ordering)

        return queryset

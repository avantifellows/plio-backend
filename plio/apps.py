from django.apps import AppConfig


class PlioConfig(AppConfig):
    name = "plio"

    def ready(self):
        import plio.signals  # noqa

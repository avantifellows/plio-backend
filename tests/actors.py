class Actor:
    def __init__(self, client, user):
        self.client = client
        self.user = user

    def get(self, path, organization=None, **extra):
        return self.client.get(path, **self._headers(organization, extra))

    def post(self, path, data=None, organization=None, **extra):
        return self.client.post(path, data=data, **self._headers(organization, extra))

    def patch(self, path, data=None, organization=None, **extra):
        return self.client.patch(path, data=data, **self._headers(organization, extra))

    def delete(self, path, organization=None, **extra):
        return self.client.delete(path, **self._headers(organization, extra))

    @staticmethod
    def _headers(organization, extra):
        if organization:
            extra["HTTP_ORGANIZATION"] = organization.shortcode
        return extra

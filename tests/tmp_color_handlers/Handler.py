
from httpserver.EndpointDecorators import uri_mapping


class H:
    @uri_mapping('/color-test', method='GET')
    def c(self, request):
        """Doc

>>>openapi
summary: Color test
responses: { 200: { description: OK } }
<<<openapi
"""
        pass

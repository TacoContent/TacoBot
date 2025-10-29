
from httpserver.EndpointDecorators import uri_mapping

class CustomMarkersHandler:
    @uri_mapping('/custom-markers', method=['GET'])
    def get_custom(self, request):
        """Example using custom markers.

        [[openapi
        summary: Custom markers example
        responses: { 200: { description: OK } }
        ]]openapi
        """
        pass

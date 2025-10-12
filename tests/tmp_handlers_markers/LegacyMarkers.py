
from httpserver.EndpointDecorators import uri_mapping

class LegacyMarkersHandler:
    @uri_mapping('/legacy-markers', method=['GET'])
    def get_legacy(self, request):
        """Example using legacy markers.

        ---openapi
        summary: Legacy markers example
        responses: { 200: { description: OK } }
        ---end
        """
        pass

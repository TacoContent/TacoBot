from httpserver.EndpointDecorators import uri_mapping


class NewMarkersHandler:
    @uri_mapping('/new-markers', method=['GET'])
    def get_new(self, request):
        """Example using new default markers.

        >>>openapi
        summary: New markers example
        responses: { 200: { description: OK } }
        <<<openapi
        """
        pass


from httpserver.EndpointDecorators import uri_mapping

class OnlyGetHandler:
    @uri_mapping('/only-get', method=['GET'])
    def only_get(self, request):
        """Handler with extraneous POST definition in method-rooted block.

        >>>openapi
        get:
          summary: Only get
          responses: { 200: { description: OK } }
        post:
          summary: Should not be here
          responses: { 200: { description: OK } }
        <<<openapi
        """
        pass

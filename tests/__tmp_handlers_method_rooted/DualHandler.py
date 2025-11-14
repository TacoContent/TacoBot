
from httpserver.EndpointDecorators import uri_mapping

class DualHandler:
    @uri_mapping('/dual', method=['GET','POST'])
    def dual(self, request):
        """Dual method endpoint with method-rooted openapi block

        >>>openapi
        get:
          summary: Dual get
          tags: [test]
          responses: { 200: { description: OK } }
        post:
          summary: Dual post
          tags: [test]
          responses: { 200: { description: OK } }
        <<<openapi
        """
        pass

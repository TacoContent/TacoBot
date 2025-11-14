
from httpserver.EndpointDecorators import uri_mapping, uri_variable_mapping, uri_pattern_mapping

class DemoHandler:
    @uri_mapping('/health', method='GET')
    def health(self, request):
        """health endpoint

        >>>openapi
        summary: Health
        responses: { 200: { description: OK } }
        <<<openapi
        """
        pass

    @uri_mapping('/multi', method=['GET','POST'])
    def multi(self, request):
        """multi endpoint

        >>>openapi
        summary: Multi
        responses: { 200: { description: OK } }
        <<<openapi
        """
        pass

    @uri_variable_mapping('/api/v1/items/{item_id}', method='DELETE')
    def delete_item(self, request, uri_variables):
        """delete endpoint

        >>>openapi
        summary: Delete item
        parameters:
          - in: path
            name: item_id
            schema: { type: string }
            required: true
            description: Item id
        responses: { 200: { description: Deleted } }
        <<<openapi
        """
        pass

    @uri_pattern_mapping(r'^/regex/(?P<slug>[a-z0-9-]+)$', method='GET')
    def regex(self, request, slug):
        """regex endpoint (ignored)

        >>>openapi
        summary: Regex
        responses: { 200: { description: OK } }
        <<<openapi
        """
        pass

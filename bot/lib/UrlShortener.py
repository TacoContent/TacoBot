import json

import requests


class UrlShortener:
    def __init__(self, **kwargs):
        self.api_url = 'https://api-ssl.bitly.com/v4'
        if 'access_token' in kwargs:
            self.access_token = kwargs['access_token']
        if 'api_url' in kwargs:
            self.api_url = kwargs['api_url']

        enforce_https = False
        if 'enforce_https' in kwargs:
            enforce_https = bool(kwargs['enforce_https'])

        if self.api_url is None or self.api_url == "":
            raise Exception("Missing required api_url argument")

        if self.access_token is None or self.access_token == "":
            raise Exception("Missing required access_token argument")

        if self.api_url[-1] == '/':
            self.api_url = self.api_url[:-1]

        if not self.api_url.startswith('https://') and enforce_https:
            raise Exception("API URL must be a secure URL")

    def shorten(self, **kwargs):
        # loop through the kwargs and build the params
        payload = {}
        for key, value in kwargs.items():
            payload[key] = value

        print(json.dumps(payload, indent=4))

        response = requests.post(
            f"{self.api_url}/api/shorten",
            data=json.dumps(payload),
            headers={"X-ACCESS-TOKEN": f"{self.access_token}", "Content-Type": "application/json"},
        )
        print(response.text)
        r = response.json()
        print(r)
        return r

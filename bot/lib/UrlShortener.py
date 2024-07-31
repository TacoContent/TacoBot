import json

import requests


class UrlShortener:
    def __init__(self, **kwargs):
        self.api_url = 'https://api-ssl.bitly.com/v4'
        if 'access_token' in kwargs:
            self.access_token = kwargs['access_token']
        if 'api_url' in kwargs:
            self.api_url = kwargs['api_url']

        if self.api_url is None or self.access_token is None:
            raise Exception("Missing access_token or api_url")
        if self.api_url[-1] == '/':
            self.api_url = self.api_url[:-1]

        if not self.api_url.startswith('https://'):
            raise Exception("API URL must be a secure URL")

        if self.api_url == "":
            raise Exception("API URL cannot be empty")

    def shorten(self, **kwargs):
        # loop through the kwargs and build the params
        payload = {}
        for key, value in kwargs.items():
            payload[key] = value

        print(json.dumps(payload, indent=4))

        response = requests.post(
            f"{self.api_url}/shorten",
            data=json.dumps(payload),
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
        )
        r = response.json()
        print(r)
        return r

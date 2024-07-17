import traceback

import requests


class SteamApiClient:
    def __init__(self):
        # self.api_key = os.environ.get('STEAM_API_KEY')
        self.base_url = 'https://store.steampowered.com/api'
        self.headers = {'User-Agent': 'TacoBot/1.0.0-snapshot'}

    def get_app_id_from_url(self, url: str):
        if 'store.steampowered.com' not in url:
            return None

        # if url ends with / then remove it
        if url[-1] == '/':
            url = url[:-1]
        if 'app' in url:
            # if the url ends with an app id use index -1
            if url.split('/')[-1].isnumeric():
                return url.split('/')[-1]
            # otherwise use index -2
            else:
                app_id = url.split('/')[-2]
                return app_id
        return None

    def get_app_details(self, app_id: str):
        try:
            url = f'{self.base_url}/appdetails?appids={app_id}&cc=us&l=en'
            response = requests.get(url, headers=self.headers)
            result = response.json()
            return result
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            # todo: log error
            return None

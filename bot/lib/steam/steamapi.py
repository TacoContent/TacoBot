import requests

class SteamApiClient:

    def __init__(self):
        # self.api_key = os.environ.get('STEAM_API_KEY')
        self.base_url = 'https://store.steampowered.com/api'
        self.headers = {
            'User-Agent': 'TacoBot/1.0.0-snapshot'
        }

    def get_app_id_from_url(self, url: str):
        if 'store.steampowered.com' not in url:
            return None
        if 'app' in url:
            app_id = url.split('/')[-1]
            return app_id
        return None

    def get_app_details(self, app_id: str):
        url = f'{self.base_url}/appdetails?appid={app_id}'
        response = requests.get(url, headers=self.headers)
        return response.json()

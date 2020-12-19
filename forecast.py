import requests
import json
from datetime import timedelta, datetime
from logger import logger
from my_config import OWM_KEY

class Forecast():
    def __init__(self, lat="51.550113", lon="9.945940"):
        self.api_key = OWM_KEY
        self.lat = lat
        self.lon =  lon
        self._data = None
        self.last_update = None
        if not self._update():
            raise RuntimeError("Could not get initial forecast")
        self.lat = self._data['city']['coord']['lat']
        self.lon = self._data['city']['coord']['lon']
        self.city = self._data['city']['name']

    def _update(self):
        success=False
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={self.lat}&lon={self.lon}&appid={self.api_key}"
        try:
            response = requests.get(url)
            _data = json.loads(response.text)
            if _data['cod'] == '200':
                self._data = _data
                self.last_update = datetime.now()
                success=True
                logger.info("Data updated")
            else:
                logger.warning("Got non-ok response: {}".format(_data))
        except requests.exceptions.RequestException as e:
            logger.warning("Request failed: {}".format(e))
        return success



    def outdated(self):
        nextdt = datetime.fromtimestamp(self._data['list'][0]['dt'])
        if nextdt < datetime.now():
            return True

        return False



    def get_data(self):
        if self.outdated():
            self._update()
        return self._data



    def check_snow(self, dtlimit):
        snow=False
        details=[]
        data = self.get_data()
        if self.outdated():
            raise RuntimeError("Could not get recent weather data")
        for dt in data['list']:
            if dt['dt'] > dtlimit:
                break
            if 'snow' in dt:
                snow=True
                t = dt['dt_txt']
                temp = dt['main']['temp'] - 273.15
                weather = [w['description'] for w in dt['weather']]
                sn = dt['snow']['3h']
                details.append(f"{t}: {temp:.1f}°C, {weather}, {sn}mm\n")
        return snow,details



    def check_snow_tomorrow(self):
        return self.check_snow((datetime.now() + timedelta(days=1, hours=3)).timestamp())


    def pretty_forecast(self):
        data = self.get_data()
        out = f"{self.city}: \n"
        for dt in data['list'][::4]:
            t = dt['dt_txt']
            temp = dt['main']['temp'] - 273.15
            weather = [w['description'] for w in dt['weather']]
            out+=f"{t}: {temp:.1f}°C, {weather}\n"
        return out

if __name__ == "__main__":
    goettingen = Forecast()
    print(goettingen.check_snow_tomorrow())

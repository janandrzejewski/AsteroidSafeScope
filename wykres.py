from selenium import webdriver
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import configparser
from datetime import datetime, timedelta
import requests
import re
from tabulate import tabulate
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.gaia import Gaia
import logging
import time
import numpy as np
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import AltAz
import matplotlib.pyplot as plt
from astropy.time import Time
from astropy.coordinates import Angle
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# logging.getLogger().setLevel(logging.WARNING)


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class DataObject:
    def __init__(self, _id, begin, end):
        self._id = _id
        self.begin = begin
        self.end = end


def timeit(func):
    def timed(*args, **kwargs):
        ts = time.time()
        result = func(*args, **kwargs)
        te = time.time()
        logging.info(f"Function: {func.__name__} time: {round((te -ts)*1000,1)} ms)")
        return result

    return timed




@timeit
def separate_data(api_response, asteroid):
    match = re.search(r"\$\$SOE.*?\$\$EOE", api_response.text, re.DOTALL)
    if match:
        fragment = match.group()
        lines = fragment.strip().split("\n")
        asteroid_positions = []

        for line in lines:
            line = line.strip()
            parts = line.split()
            if len(parts) >= 2:
                date_time = parts[0] + " " + parts[1]
                datetime_obj = datetime.strptime(date_time, "%Y-%b-%d %H:%M")

                # Tworzenie obiektu Time z obiektu datetime
                time = Time(datetime_obj)
                ra = parts[2] + " " + parts[3] + " " + parts[4]
                dec = parts[5] + " " + parts[6] + " " + parts[7]
                ra = better_pos(ra)
                dec = better_pos(dec)
                alt = get_altitude(ra, dec, time)
                asteroid_positions.append([asteroid[0], time, ra, dec, alt])
        return np.array(asteroid_positions)
    else:
        logging.exception("No ephemeris for target")
        return []

@timeit
def better_pos(pos):
    parts = pos.split()
    hours = parts[0]
    minutes = parts[1]
    seconds = parts[2]

    formatted_pos = f"{hours}d{minutes}m{seconds}s"
    return formatted_pos

@timeit
def get_altitude(ra, dec, observing_time):
    observing_location = EarthLocation(
        lat=-30 * u.deg, lon=-70 * u.deg, height=1750 * u.m
    )
    coord = SkyCoord(ra, dec)
    altaz = coord.transform_to(
        AltAz(obstime=observing_time, location=observing_location)
    )
    altitude_rad = altaz.alt
    altitude_deg = altitude_rad.to(u.deg)
    return altitude_deg

@timeit
def get_position(start_time, stop_time, asteroid_names):
    session = requests.Session()
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    response = session.get(
        url,
        params={
            "format": "text",
            "COMMAND": asteroid_names[1],
            "OBJ_DATA": "NO",
            "EPHEM_TYPE": "OBSERVER",
            "START_TIME": start_time,
            "STOP_TIME": stop_time,
            "STEP_SIZE": "1m",
            "QUANTITIES": "1",
        },
    )
    if response.status_code != 200:
        logging.exception("Horizons API error")
    asteroid_pos = separate_data(response, asteroid_names)
    return asteroid_pos

@timeit
def draw(data,asteroid_name):
    times = [entry[1].datetime for entry in data]
    altitudes = [entry[4].deg for entry in data]
    plt.plot(times, altitudes)
    plt.xlabel('Time')
    plt.ylabel('altitude (deg)')
    plt.title('A(t) ' + asteroid_name)
    min_deg = 20
    plt.axhline(y=min_deg, color='green', linestyle='--', label='Min deg = 20°')
    plt.legend(loc='upper left')
    max_deg = max(altitudes)
    max_hour = times[altitudes.index(max_deg)]
    print(max_deg,max_hour)
    plt.show()




@timeit
def main():
    with open("asteroidy.txt", "r") as file:
        asteroid_names = file.read().splitlines()
    start_time = "'" + datetime.today().strftime("%Y-%m-%d") + " " + "23:00" + "'"
    stop_time = (
        "'"
        + (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        + " "
        + "08:00"
        + "'"
    )
    asteroid_pos = get_position(start_time, stop_time, asteroid_names)
    draw(asteroid_pos,asteroid_names[1])

if __name__ == "__main__":
    main()

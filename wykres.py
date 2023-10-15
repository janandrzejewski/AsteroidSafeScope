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
import ephem
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
from astroplan import Observer

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
def separate_data(api_response, name):
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
                ra = better_pos_ra(ra)
                dec = better_pos_dec(dec)
                alt = get_altitude(ra, dec, time)
                asteroid_positions.append([name, time, ra, dec, alt])
        return np.array(asteroid_positions)
    else:
        logging.exception("No ephemeris for target")
        return []


@timeit
def better_pos_ra(pos):
    parts = pos.split()
    hours = parts[0]
    minutes = parts[1]
    seconds = parts[2]

    formatted_pos = f"{hours}h{minutes}m{seconds}s"
    return formatted_pos


@timeit
def better_pos_dec(pos):
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
def get_position(start_time, stop_time, name):
    session = requests.Session()
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    response = session.get(
        url,
        params={
            "format": "text",
            "COMMAND": name,
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
    asteroid_pos = separate_data(response, name)
    return asteroid_pos


@timeit
def draw(night_start, night_end,times,altitudes,b_times,b_altitudes,obs_start,obs_end,name):
    plt.plot(times, altitudes)
    plt.plot(b_times, b_altitudes)
    plt.xlabel("Time")
    plt.ylabel("altitude (deg)")

    min_deg = 20
    plt.axhline(y=min_deg, color="green", linestyle="--", label="Min deg = 20°")
    plt.legend(loc="upper left")
    plt.axvline(
        x=night_start,
        color="blue",
        linestyle="--",
        label="Początek nocy astronomicznej",
    )
    plt.axvline(
        x=night_end, color="blue", linestyle="--", label="Koniec nocy astronomicznej"
    )
    plt.title("A(t) " + name +  " START =  " + str(obs_start) +"END = " + str(obs_end))
    plt.ylim(0, 90)

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
        + "11:00"
        + "'"
    )
    location = EarthLocation(lat=-30 * u.deg, lon=-70 * u.deg, height=1750 * u.m)
    deepskychile = Observer(location=location, name="Subaru")
    night_start = deepskychile.twilight_evening_astronomical(Time((datetime.today())))
    night_end = deepskychile.twilight_morning_astronomical(
        Time((datetime.today() + timedelta(days=1)))
    )
    for name in asteroid_names:
        asteroid_pos = get_position(start_time, stop_time, name)
        times = [entry[1].datetime for entry in asteroid_pos]
        altitudes = [entry[4].deg for entry in asteroid_pos]
        better_data = [
            entry
            for entry in asteroid_pos
            if entry[4].deg > 20
            and entry[1].datetime > (night_start)
            and entry[1].datetime < night_end
        ]
        b_times = [entry[1].datetime for entry in better_data]
        b_altitudes = [entry[4].deg for entry in better_data]
        max_deg = max(altitudes)
        max_hour = times[altitudes.index(max_deg)]
        obs_start = b_times[0]
        obs_end = b_times[-1]
        draw(night_start.datetime, night_end.datetime,times,altitudes,b_times,b_altitudes,obs_start,obs_end,name)


if __name__ == "__main__":
    main()

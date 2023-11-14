import configparser
import logging
import os
import re
import time
from datetime import datetime, timedelta

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import requests
from astroplan import Observer
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from astroquery.gaia import Gaia
from flask import Flask, jsonify, request
from matplotlib.patches import Circle

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# logging.getLogger().setLevel(logging.WARNING)


def timeit(func):
    def timed(*args, **kwargs):
        ts = time.time()
        result = func(*args, **kwargs)
        te = time.time()
        logging.info(f"Function: {func.__name__} time: {round((te -ts)*1000,1)} ms)")
        return result

    return timed


@timeit
def read_config():
    config_path = "config.ini"
    config = configparser.ConfigParser()
    try:
        config.read(config_path)
    except FileNotFoundError:
        logging.exception("There is no config file named config.ini")
    else:
        RADIUS_FACTOR = config.getfloat("Parameters", "RADIUS_FACTOR")
        MAX_STARS = config.getint("Parameters", "MAX_STARS")
        MAX_DISTANCE = config.getfloat("Parameters", "MAX_DISTANCE")
        QUERY_STARS_LIMIT = config.getfloat("Parameters", "QUERY_STARS_LIMIT")
        MIN_DEG = config.getfloat("Parameters", "MIN_DEG")

    return RADIUS_FACTOR, MAX_STARS, MAX_DISTANCE, QUERY_STARS_LIMIT, MIN_DEG


@timeit
def separate_data(api_response, name, location):
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
                time = Time(datetime_obj)
                ra = f"{parts[2]}h{parts[3]}m{parts[4]}s"
                dec = f"{parts[5]}d{parts[6]}m{parts[7]}s"
                alt = get_altitude(ra, dec, time, location)
                asteroid_positions.append([name, time, ra, dec, alt])
        return np.array(asteroid_positions)
    else:
        logging.exception("No ephemeris for target")
        return []


@timeit
def get_altitude(ra, dec, observing_time, observing_location):
    coord = SkyCoord(ra, dec)
    altaz = coord.transform_to(
        AltAz(obstime=observing_time, location=observing_location)
    )
    altitude_rad = altaz.alt
    altitude_deg = altitude_rad.to(u.deg)

    return altitude_deg



@timeit
def get_radius(x, y, x_mean, y_mean, radius_factor):
    radius = (np.sqrt((x[0] - x_mean) ** 2 + (y[0] - y_mean) ** 2)) * radius_factor
    logging.info(f"radius = {radius}")
    return radius


@timeit
def get_cartesian_positions(asteroid_positions):
    arr = asteroid_positions
    asteroid_cartesian_positions = SkyCoord(
        arr[:, 2], arr[:, 3], unit=(u.hourangle, u.deg)
    )

    x = asteroid_cartesian_positions.ra.deg
    y = asteroid_cartesian_positions.dec.deg

    x_mean = np.mean(x)
    y_mean = np.mean(y)
    return x, y, x_mean, y_mean




@timeit
def get_position(start_time, stop_time, name, location):
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    response = requests.get(
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
    response.raise_for_status()
    asteroid_pos = separate_data(response, name, location)
    return asteroid_pos


@timeit
def get_stars_in_radius(radius, x_mean, y_mean):
    coord = SkyCoord(ra=x_mean, dec=y_mean, unit=(u.deg, u.deg))
    j = Gaia.cone_search(coord, radius * u.deg)
    result = j.get_results()
    return result


@timeit
def get_stars_in_distance(MAX_DISTANCE, stars, a, b):
    x = stars["ra"]
    y = stars["dec"]
    stars["d"] = abs((a * x + -1 * y + b) / np.sqrt(a**2 + 1))
    stars = stars[stars["d"] < MAX_DISTANCE]
    return stars


@timeit
def get_stars(radius, x_mean, y_mean, a, b, MAX_DISTANCE):
    stars_in_radius = get_stars_in_radius(radius, x_mean, y_mean)
    stars = get_stars_in_distance(MAX_DISTANCE, stars_in_radius, a, b)
    return stars


@timeit
def get_linear_f(x, y, x_mean, y_mean):
    delta_x = x - x_mean
    delta_y = y - y_mean

    a = np.sum(delta_x * delta_y) / np.sum(delta_x**2)
    b = y_mean - a * x_mean
    return a, b


@timeit
def get_table_data(
    start,
    end,
    name,
    asteroid_table_data,
    MAX_DISTANCE,
    MAX_STARS,
    x,
    y,
    x_mean,
    y_mean,
    radius,
):
    a, b = get_linear_f(x, y, x_mean, y_mean)
    stars_nearby = get_stars(radius, x_mean, y_mean, a, b, MAX_DISTANCE)
    stars_count = len(stars_nearby)
    if len(stars_nearby) < MAX_STARS:
        mag_values = stars_nearby["phot_g_mean_mag"][
            :5
        ]  # Limited to a maximum of 5 mag values
        mag_str = ", ".join(map(str, mag_values))

        mean_position = SkyCoord(x_mean, y_mean, unit=(u.deg, u.deg))
        duration = end - start
        asteroid_table_data["Asteroid ID"].append(name)
        asteroid_table_data["Info"].append(
            f"Istnieje {len(stars_nearby)} gwiazd blisko trasy \n MAG:{mag_str}"
        )
        asteroid_table_data["Start"].append(str(start))
        asteroid_table_data["Stop"].append(str(end))
        asteroid_table_data["Stars qty"].append(stars_count)
        asteroid_table_data["Duration"].append(str(duration))
        asteroid_table_data["Position"].append(
            f"{mean_position.ra.to_string(unit='hour', decimal=True)} {mean_position.dec.to_string(decimal=True)}"
        )
    return asteroid_table_data


@app.route("/asterod_data_processing", methods=["POST"])
def main():
    RADIUS_FACTOR, MAX_STARS, MAX_DISTANCE, QUERY_STARS_LIMIT, MIN_DEG = read_config()
    Gaia.ROW_LIMIT = int(QUERY_STARS_LIMIT)
    data = request.get_json()
    asteroid_names = data.get("asteroid_list").split(", ")
    obs_date_str = data.get("date")
    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d")
    location = EarthLocation(lat=-30 * u.deg, lon=-70 * u.deg, height=1750 * u.m)
    deepskychile = Observer(location=location, name="deepskychile")
    night_start = deepskychile.twilight_evening_astronomical(
        Time((obs_date + timedelta(days=1)))
    )
    night_end = deepskychile.twilight_morning_astronomical(
        Time((obs_date + timedelta(days=1)))
    )  # dziala tylko gdy night_start zaczyna sie juz nastepnego dnia :p
    start_time = f"'{night_start.datetime.strftime('%Y-%m-%d %H:%M')}'"
    stop_time = f"'{night_end.datetime.strftime('%Y-%m-%d %H:%M')}'"
    asteroid_table_data = {
        "Asteroid ID": [],
        "Info": [],
        "Start": [],
        "Stop": [],
        "Stars qty": [],
        "Duration": [],
        "Position": [],
    }
    for name in asteroid_names:
        asteroid_positions = get_position(start_time, stop_time, name, location)
        if len(asteroid_positions) > 0:
            better_data = [
                entry
                for entry in asteroid_positions
                if entry[4].deg > 20
                and entry[1].datetime > (night_start)
                and entry[1].datetime < night_end
            ]
            b_times = [entry[1].datetime for entry in better_data]
            obs_start = b_times[0]
            obs_end = b_times[-1]
            x, y, x_mean, y_mean = get_cartesian_positions(asteroid_positions)
            radius = get_radius(x, y, x_mean, y_mean, RADIUS_FACTOR)
            asteroid_table_data = get_table_data(
                obs_start,
                obs_end,
                name,
                asteroid_table_data,
                MAX_DISTANCE,
                MAX_STARS,
                x,
                y,
                x_mean,
                y_mean,
                radius,
            )
    return jsonify(asteroid_table_data)


if __name__ == "__main__":
    app.run(port=5000)
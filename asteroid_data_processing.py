import configparser
import logging
import re
import time
from datetime import datetime, timedelta
import pandas as pd
import astropy.units as u
import numpy as np
import requests
from astroplan import Observer
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from astroquery.gaia import Gaia
from flask import Flask, jsonify, request

from io import StringIO

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
def separate_data(api_response, location):
    match = re.search(r"(?<=\$\$SOE).*?(?=\$\$EOE)", api_response.text, re.DOTALL)
    if match:
        text_data = StringIO(match.group())
        df = pd.read_csv(text_data, sep='\\s+',header=None)
        df['datatime'] = df.apply(get_datatime,axis = 1)
        df['coord'] = df.apply(convert_to_coo,axis = 1)
        df['alt'] = df.apply(get_altitude,axis = 1,observing_location = location)
        df = df.drop(df.columns[:8], axis=1)
    return df

def convert_to_coo(row):
    ra = f"{row[2]}h{row[3]}m{row[4]}s"
    dec = f"{row[5]}d{row[6]}m{row[7]}s"
    coord = SkyCoord(ra,dec, unit=(u.hourangle, u.deg))
    return coord



def get_datatime(row):
  date_time = f'{row[0]} {row[1]}'
  datetime_obj = datetime.strptime(date_time, "%Y-%b-%d %H:%M")

  return datetime_obj

def get_altitude(row,observing_location):
    coord = row['coord']
    altaz = coord.transform_to(
        AltAz(obstime=row['datatime'], location=observing_location)
    )
    altitude_rad = altaz.alt
    altitude_deg = altitude_rad.to(u.deg)

    return altitude_deg.value

@timeit
def get_radius(x, y, x_mean, y_mean, radius_factor):
    radius = (np.sqrt((x.iloc[0] - x_mean) ** 2 + (y.iloc[0] - y_mean) ** 2)) * radius_factor
    logging.info(f"{radius = }")
    return radius

@timeit
def get_cartesian_positions(filtered_df):
    x = filtered_df['coord'].apply(lambda x: x.ra.deg)
    y = filtered_df['coord'].apply(lambda x: x.dec.deg)

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
            "STEP_SIZE": "4m",
            "QUANTITIES": "1",
        },
    )
    response.raise_for_status()
    asteroid_pos = separate_data(response, location)
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
        asteroid_df = get_position(start_time, stop_time, name, location)
        alt_condition = asteroid_df['alt'] > 20
        datatime_condition = (asteroid_df['datatime'] > night_start.datetime) & (asteroid_df['datatime'] < night_end.datetime)
        filtered_df = asteroid_df[alt_condition & datatime_condition].sort_values(by='datatime')
        obs_start = filtered_df['datatime'].iloc[0]
        obs_end = filtered_df['datatime'].iloc[-1]
        x, y, x_mean, y_mean = get_cartesian_positions(filtered_df)
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
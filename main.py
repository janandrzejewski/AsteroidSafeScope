import matplotlib.pyplot as plt
from matplotlib.patches import Circle
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
from astroplan import Observer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.getLogger().setLevel(logging.WARNING)


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
    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        RADIUS_FACTOR = config.getfloat("Parameters", "RADIUS_FACTOR")

        MAX_STARS = config.getint("Parameters", "MAX_STARS")

        MAX_DISTANCE = config.getfloat("Parameters", "MAX_DISTANCE")

        QUERY_STARS_LIMIT = config.getfloat("Parameters", "QUERY_STARS_LIMIT")

    except FileNotFoundError:
        logging.exception("There is no config file named config.ini")
    return RADIUS_FACTOR, MAX_STARS, MAX_DISTANCE, QUERY_STARS_LIMIT


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

                # Tworzenie obiektu Time z obiektu datetime
                time = Time(datetime_obj)
                ra = parts[2] + " " + parts[3] + " " + parts[4]
                dec = parts[5] + " " + parts[6] + " " + parts[7]
                ra = better_pos_ra(ra)
                dec = better_pos_dec(dec)
                alt = get_altitude(ra, dec, time, location)
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
def get_radius(x, y, x_mean, y_mean, RADIUS_FACTOR):
    radius = (np.sqrt((x[0] - x_mean) ** 2 + (y[0] - y_mean) ** 2)) * RADIUS_FACTOR
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
def get_altitude(ra, dec, observing_time, observing_location):
    coord = SkyCoord(ra, dec)
    altaz = coord.transform_to(
        AltAz(obstime=observing_time, location=observing_location)
    )
    altitude_rad = altaz.alt
    altitude_deg = altitude_rad.to(u.deg)

    return altitude_deg


@timeit
def get_position(start_time, stop_time, name, location):
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
    asteroid_pos = separate_data(response, name, location)
    return asteroid_pos


@timeit
def draw(
    night_start,
    night_end,
    times,
    altitudes,
    b_times,
    b_altitudes,
    obs_start,
    obs_end,
    name,
):
    plt.plot(times, altitudes)
    plt.plot(b_times, b_altitudes)
    plt.xlabel("Time")
    plt.ylabel("altitude (deg)")

    min_deg = 20
    plt.axhline(y=min_deg, color="green", linestyle="--", label="Min deg = 20°")

    plt.axvline(
        x=night_start,
        color="blue",
        linestyle="--",
        label="Początek nocy astronomicznej",
    )
    plt.axvline(
        x=night_end, color="blue", linestyle="--", label="Koniec nocy astronomicznej"
    )
    plt.title("A(t) " + name + " START =  " + str(obs_start) + "END = " + str(obs_end))
    plt.ylim(0, 90)
    plt.legend(loc="upper left")
    plt.savefig(f"{name}_altitude")
    plt.clf()


@timeit
def get_stars_in_radius(radius, x_mean, y_mean):
    coord = SkyCoord(ra=x_mean, dec=y_mean, unit=(u.deg, u.deg))
    j = Gaia.cone_search(coord, radius * u.deg)
    result = j.get_results()
    return result


@timeit
def get_stars_in_d(MAX_DISTANCE, stars, a, b):
    x = stars["ra"]
    y = stars["dec"]
    stars["d"] = abs((a * x + -1 * y + b) / np.sqrt(a**2 + 1))
    stars = stars[stars["d"] < MAX_DISTANCE]
    return stars


@timeit
def get_stars(radius, x_mean, y_mean, a, b, MAX_DISTANCE):
    stars_in_radius = get_stars_in_radius(radius, x_mean, y_mean)
    stars = get_stars_in_d(MAX_DISTANCE, stars_in_radius, a, b)
    return stars


@timeit
def get_linear_f(x, y, x_mean, y_mean):
    delta_x = x - x_mean
    delta_y = y - y_mean

    a = np.sum(delta_x * delta_y) / np.sum(delta_x**2)
    b = y_mean - a * x_mean
    return a, b


@timeit
def get_row_color(stars_count, MAX_STARS):
    if stars_count == 0:
        row_color = bcolors.OKGREEN  # Green
    elif stars_count < MAX_STARS / 2:
        row_color = bcolors.WARNING  # Orange
    else:
        row_color = bcolors.FAIL  # Red
    return row_color


def f(a, b, x):
    return a * x + b


@timeit
def draw_f(ax, a, b, x):
    ax.plot(x, f(a, b, x), color="red")
    return ax


@timeit
def draw_circle(ax, radius, x_mean, y_mean):
    center = (x_mean, y_mean)
    circle = Circle(center, radius, edgecolor="black", facecolor="none")
    ax.add_patch(circle)
    xmin = center[0] - radius - 1
    xmax = center[0] + radius + 1
    ymin = center[1] - radius - 1
    ymax = center[1] + radius + 1
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    return ax


@timeit
def draw_stars(ax, stars, size):
    ax.plot(stars["ra"], stars["dec"], marker="*", ls="none", ms=size)
    for i, mag in enumerate(stars["phot_g_mean_mag"]):
        if mag > 18:
            continue
        ax.annotate(round(mag, 2), (stars["ra"][i], stars["dec"][i]))
    ax.invert_xaxis()
    return ax


@timeit
def plot(name, x, y, x_mean, y_mean, MAX_DISTANCE, radius):
    fig, ax = plt.subplots()
    a, b = get_linear_f(x, y, x_mean, y_mean)
    ax = draw_f(ax, a, b, x)
    ax = draw_circle(ax, radius, x_mean, y_mean)
    stars_in_radius = get_stars_in_radius(radius, x_mean, y_mean)
    stars_in_d = get_stars_in_d(MAX_DISTANCE, stars_in_radius, a, b)
    ax = draw_stars(ax, stars_in_radius, 2)
    ax = draw_stars(ax, stars_in_d, 5)
    plt.axis("equal")
    plt.grid(True)
    ax.invert_xaxis()
    plt.savefig(f"{name}_stars")
    plt.close()


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
        row_color = get_row_color(stars_count, MAX_STARS)
        mag_values = stars_nearby["phot_g_mean_mag"][
            :5
        ]  # Limited to a maximum of 5 mag values
        mag_str = ", ".join(map(str, mag_values))

        mean_position = SkyCoord(x_mean, y_mean, unit=(u.deg, u.deg))
        duration = end - start
        asteroid_row = [
            row_color + name,
            f"{row_color}There are {len(stars_nearby)} stars close to the path \n{row_color} MAG:{mag_str}{bcolors.ENDC}",
            row_color + str(start),
            row_color + str(end),
            stars_count,
            duration,
            f"{mean_position.ra.to_string(unit = 'hour',decimal=True)} {mean_position.dec.to_string(decimal=True)}",
        ]
        asteroid_table_data.append(asteroid_row)
    return asteroid_table_data


@timeit
def print_table(asteroid_table_data):
    asteroid_table_headers = [
        "Asteroid ID",
        "Info",
        "Start",
        "Stop",
        "Stars qty",
        "Duration",
        "Position",
    ]
    asteroid_table = tabulate(
        asteroid_table_data, headers=asteroid_table_headers, tablefmt="grid"
    )
    print(f"Result:\n{asteroid_table}")


def main():
    RADIUS_FACTOR, MAX_STARS, MAX_DISTANCE, QUERY_STARS_LIMIT = read_config()
    Gaia.ROW_LIMIT = int(QUERY_STARS_LIMIT)
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
    deepskychile = Observer(location=location, name="deepskychile")
    night_start = deepskychile.twilight_evening_astronomical(Time((datetime.today())))
    night_end = deepskychile.twilight_morning_astronomical(
        Time((datetime.today() + timedelta(days=1)))
    )
    asteroid_table_data = []
    for name in asteroid_names:
        asteroid_positions = get_position(start_time, stop_time, name, location)
        times = [entry[1].datetime for entry in asteroid_positions]
        altitudes = [entry[4].deg for entry in asteroid_positions]
        better_data = [
            entry
            for entry in asteroid_positions
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
        draw(
            night_start.datetime,
            night_end.datetime,
            times,
            altitudes,
            b_times,
            b_altitudes,
            obs_start,
            obs_end,
            name,
        )
        if len(asteroid_positions) > 0:
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
            plot(name, x, y, x_mean, y_mean, MAX_DISTANCE, radius)

    sorted_table_data = sorted(asteroid_table_data, key=lambda row: (row[4], -row[5]))
    print_table(sorted_table_data)


if __name__ == "__main__":
    main()

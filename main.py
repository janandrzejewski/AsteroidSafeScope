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


def f(a, b, x):
    return a * x + b


@timeit
def read_config():
    config_path = "config.ini"
    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        email = config.get("Credentials", "email")
        password = config.get("Credentials", "password")
        page_name = config.get("Page", "name")
        
        RADIUS_FACTOR = config.getfloat("Parameters", "RADIUS_FACTOR")

        MAX_STARS = config.getint("Parameters", "MAX_STARS")

        MAX_DISTANCE = config.getfloat("Parameters", "MAX_DISTANCE")

    except FileNotFoundError:
        logging.exception("Nie ma pliku config o nazwie config.ini")
    return email, password, page_name, RADIUS_FACTOR, MAX_STARS, MAX_DISTANCE


@timeit
def log_in(email, password, page_name):
    driver = webdriver.Firefox()
    driver.get(page_name)
    element = driver.find_element(By.NAME, "email")
    element.send_keys(email)
    element = driver.find_element(By.NAME, "pass")
    element.send_keys(password)
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div[2]/form/div[4]/button"
    ).click()
    driver.find_element(
        By.XPATH, "/html/body/div[2]/div[2]/div/div[1]/ul[2]/li[3]/a/span"
    ).click()
    driver.find_element(By.ID, "sites").click()
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div/div[2]/table/tbody/tr[4]/td[1]/a/i"
    ).click()
    driver.find_element(
        By.XPATH, "/html/body/div[3]/div/div/div[2]/table/tbody/tr[1]/td[1]/a/i"
    ).click()
    driver.find_element(By.XPATH, "/html/body/div[3]/div/div/div[3]/button").click()

    return driver


@timeit
def get_asteroids_list(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")

    asteroids_list = []

    for row in rows:
        cells = row.find_all("td")

        if len(cells) >= 8:
            asteroid_id = cells[1].find("span", id="id")
            start_time = cells[7].text
            stop_time = cells[8].text

            asteroid = DataObject(asteroid_id.text, start_time, stop_time)
            asteroids_list.append(asteroid)

    return asteroids_list


@timeit
def close_website(driver):
    driver.quit()



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
def get_linear_f(x, y, x_mean, y_mean):
    delta_x = x - x_mean
    delta_y = y - y_mean

    a = np.sum(delta_x * delta_y) / np.sum(delta_x**2)
    b = y_mean - a * x_mean
    return a, b

@timeit
def get_radius(x, y, x_mean, y_mean, RADIUS_FACTOR):
    radius = (np.sqrt((x[0] - x_mean) ** 2 + (y[0] - y_mean) ** 2)) * RADIUS_FACTOR
    logging.info(f"radius = {radius}")
    return radius


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
                ra = parts[2] + " " + parts[3] + " " + parts[4]
                dec = parts[5] + " " + parts[6] + " " + parts[7]

                asteroid_positions.append([asteroid._id, date_time, ra, dec])
        return np.array(asteroid_positions)
    else:
        logging.exception("No ephemeris for target")
        return []


@timeit
def start_session():
    return requests.Session()

@timeit
def create_plt():
    ax = plt.subplots()
    return ax

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
def get_stars_in_radius(radius,x_mean,y_mean):
    coord = SkyCoord(ra=x_mean, dec=y_mean, unit=(u.deg, u.deg))
    j = Gaia.cone_search(coord, radius * u.deg)
    result = j.get_results()
    return result


@timeit
def get_stars_in_d(MAX_DISTANCE,stars,a,b):
    x = stars["ra"]
    y = stars["dec"]
    stars["d"] = abs((a * x + -1 * y + b)/np.sqrt(a**2 + 1))
    stars = stars[stars["d"] < MAX_DISTANCE]
    return stars

@timeit
def get_stars(radius,x,y, x_mean, y_mean, a,b, MAX_DISTANCE):
    stars_in_radius = get_stars_in_radius(radius,x_mean,y_mean)
    logging.info(f"There are {len(stars_in_radius)} stars in radius = {radius}")    
    stars =  get_stars_in_d(MAX_DISTANCE,stars_in_radius,a,b)
    return stars

@timeit
def draw_stars(ax, stars, size):
    ax.plot(stars["ra"], stars["dec"], marker="*", ls="none", ms=size)
    logging.info(f'\n{stars["d"]}')
    for i, mag in enumerate(stars["phot_g_mean_mag"]):
        if mag > 18:
            continue
        ax.annotate(round(mag, 2), (stars["ra"][i], stars["dec"][i]))
    ax.invert_xaxis()
    return ax

@timeit
def plot(asteroid_positions, asteroid,x,y,x_mean,y_mean,MAX_DISTANCE,radius):
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
    plt.savefig(f"{asteroid._id}")
    plt.close()



def decdeg2dms(dd):
    mult = -1 if dd < 0 else 1
    mnt,sec = divmod(abs(dd)*3600, 60)
    deg,mnt = divmod(mnt, 60)
    return f"{mult*deg}:{mnt}:{sec}"

@timeit
def print_table(asteroid_table_data):
    asteroid_table_headers = ["Asteroid ID", "Info", "Start", "Stop", "Stars qty", "Duration","Position"]
    asteroid_table = tabulate(
        asteroid_table_data, headers=asteroid_table_headers, tablefmt="grid"
    )
    print(f"Result:\n{asteroid_table}")


@timeit
def get_position(asteroid, session):
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    start_time = (
        "'" + datetime.today().strftime("%Y-%m-%d") + " " + asteroid.begin + "'"
    )
    if asteroid.begin > asteroid.end:
        stop_time = (
            "'"
            + (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            + " "
            + asteroid.end
            + "'"
        )
    else:
        stop_time = (
            "'" + datetime.today().strftime("%Y-%m-%d") + " " + asteroid.end + "'"
        )

    response = session.get(
        url,
        params={
            "format": "text",
            "COMMAND": asteroid._id,
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
    return response

@timeit
def get_row_color(stars_count, MAX_STARS):
    if stars_count == 0:
        row_color = bcolors.OKGREEN  # Green
    elif stars_count < MAX_STARS / 2:
        row_color = bcolors.WARNING  # Orange
    else:
        row_color = bcolors.FAIL  # Red
    return row_color


@timeit
def get_table_data(asteroid_positions, asteroid, asteroid_table_data, MAX_DISTANCE, MAX_STARS, x, y, x_mean, y_mean,radius):
    x, y, x_mean, y_mean = get_cartesian_positions(asteroid_positions)
    a, b = get_linear_f(x, y, x_mean, y_mean)
    stars_nearby = get_stars(radius,x,y, x_mean, y_mean,a,b,MAX_DISTANCE)
    stars_count = len(stars_nearby)
    if len(stars_nearby) < MAX_STARS:
        row_color = get_row_color(stars_count,MAX_STARS)
        mag_values = stars_nearby["phot_g_mean_mag"][
            :5
        ]  # Limited to a maximum of 5 mag values
        mag_str = ", ".join(map(str, mag_values))

        start = datetime.strptime(asteroid.begin, "%H:%M")
        end = datetime.strptime(asteroid.end, "%H:%M")

        if start < end:
            duration = end - start
        else:
            duration = (end - start) + timedelta(seconds=(24 * 3600))
        
        mean_position = SkyCoord(
        x_mean,y_mean, unit=(u.deg, u.deg)
    )

        asteroid_row = [
            row_color + asteroid._id,
            f"{row_color}There are {len(stars_nearby)} stars close to the path \n{row_color} MAG:{mag_str}{bcolors.ENDC}",
            row_color + asteroid.begin,
            row_color + asteroid.end,
            stars_count,
            duration,
            f"{mean_position.ra.to_string(unit = 'hour',decimal=True)} {mean_position.dec.to_string(decimal=True)}"
        ]
        asteroid_table_data.append(asteroid_row)
    return asteroid_table_data


@timeit
def main():
    email, password, page_name, RADIUS_FACTOR, MAX_STARS, MAX_DISTANCE, QUERY_STARS_LIMIT = read_config()
    driver = log_in(email, password, page_name)
    asteroids_list = get_asteroids_list(driver)
    close_website(driver)
    session = start_session()
    asteroid_table_data = []
    Gaia.ROW_LIMIT = QUERY_STARS_LIMIT
    for asteroid in asteroids_list:
        logging.info(f"asteroid_id {asteroid._id}")
        api_response = get_position(asteroid, session)
        asteroid_positions = separate_data(api_response, asteroid)
        if len(asteroid_positions) > 0:
            x, y, x_mean, y_mean = get_cartesian_positions(asteroid_positions)
            radius = get_radius(x, y, x_mean, y_mean, RADIUS_FACTOR)

            asteroid_table_data = get_table_data(asteroid_positions, asteroid, asteroid_table_data, MAX_DISTANCE, MAX_STARS,x, y, x_mean, y_mean,radius)
            
            #plot(asteroid_positions, asteroid,x,y,x_mean,y_mean,MAX_DISTANCE,radius)
        
    sorted_table_data = sorted(
        asteroid_table_data, key=lambda row: (row[4], -row[5])
    )
    print_table(sorted_table_data)


if __name__ == "__main__":
    main()
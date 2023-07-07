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

#determines the size of the radius
RADIUS_FACTOR = 1.05


d = 0.00138888889
# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

def timeit(func):
    def timed(*args, **kwargs):
        ts = time.time()
        result = func(*args, **kwargs)
        te = time.time()
        logging.info(f"Function: {func.__name__} time: {round((te -ts)*1000,1)} ms)")
        return result
    return timed



class DataObject:
    def __init__(self, _id, begin, end):
        self._id = _id
        self.begin = begin
        self.end = end



def f(a,b,x):
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

    except FileNotFoundError:
        logging.exception("Nie ma pliku config o nazwie config.ini")
    return email, password, page_name

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
def get_collided_stars(asteroid_positions, radius=5):
    if asteroid_positions:
        collided_stars = set()
        for position in asteroid_positions:
            coord = SkyCoord(ra=position[2], dec=position[3], unit=(u.hourangle, u.deg))
            j = Gaia.cone_search(coord, radius * u.arcsec)
            result = j.get_results()

            if len(result) > 0:
                for star in result:
                    star_id = star["DESIGNATION"]
                    if star_id not in collided_stars:
                        collided_stars.add(star_id)

        stars_nearby_data = []
        for star_id in collided_stars:
            stars_nearby_data.append([star_id])
        return stars_nearby_data
    else:
        return []
        


@timeit
def get_cartesian_positions(asteroid_positions):
    arr = asteroid_positions
    asteroid_cartesian_positions = SkyCoord(arr[:,2], arr[:,3], unit=(u.hourangle, u.deg))
    x = asteroid_cartesian_positions.ra.deg
    y = asteroid_cartesian_positions.dec.deg
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    return x,y,x_mean,y_mean


@timeit
def get_linear_f(x,y,x_mean,y_mean):
    delta_x = x - x_mean
    delta_y = y - y_mean

    a = np.sum(delta_x * delta_y) / np.sum(delta_x**2)
    b = y_mean - a * x_mean
    return a,b

def get_radius(x,y,x_mean,y_mean):
    radius = (np.sqrt((x[0] - x_mean)**2 + (y[0] - y_mean)**2)) * RADIUS_FACTOR
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


def create_plt():
    ax = plt.subplots()
    return ax

def draw_f(ax,a,b,x):
    ax.plot(x, f(a,b,x), color='red')
    return ax

def draw_circle(ax,radius,x_mean,y_mean):
    center = (x_mean, y_mean)
    circle = Circle(center,radius,edgecolor='black',facecolor='none')
    ax.add_patch(circle)
    xmin = center[0] - radius - 1
    xmax = center[0] + radius + 1
    ymin = center[1] - radius - 1
    ymax = center[1] + radius + 1
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin,ymax)
    return ax


def get_stars_in_radius(radius,x_mean,y_mean):
    coord = SkyCoord(ra=x_mean, dec=y_mean, unit=(u.deg, u.deg))
    j = Gaia.cone_search(coord, radius * u.deg)
    result = j.get_results()
    return result



def get_stars_in_d(ax,d,stars_in_radius,a,b,x,y):
    x = stars_in_radius["ra"]
    y = stars_in_radius["dec"]
    stars_in_radius["d"] = abs((a * x + -1 * y + b)/np.sqrt(a**2 + 1))
    stars_in_radius = stars_in_radius[stars_in_radius["d"] < d]
    return stars_in_radius

def draw_stars(ax,stars_in_d,x,y):
    ax.plot(stars_in_d["ra"],stars_in_d["dec"],marker= "*",ls='none',ms=2)
    logging.info(f'\n{stars_in_d["d"]}')
    for i, mag in enumerate(stars_in_d["phot_g_mean_mag"]):
        if mag > 18: continue
        ax.annotate(round(mag,2), (x[i], y[i]))
    ax.invert_xaxis()
    return ax

def temp(asteroid_positions,asteroid):
    x,y,x_mean,y_mean = get_cartesian_positions(asteroid_positions)
    a,b = get_linear_f(x,y,x_mean,y_mean) 
    radius  = get_radius(x,y,x_mean,y_mean)
    fig, ax = plt.subplots()
    ax = draw_f(ax,a,b,x)
    ax = draw_circle(ax,radius,x_mean,y_mean)
    stars_in_radius = get_stars_in_radius(radius,x_mean,y_mean)
    stars_in_d = get_stars_in_d(ax,d,stars_in_radius,a,b,x,y)
    ax = draw_stars(ax,stars_in_d,x,y)
    plt.axis('equal')
    plt.grid(True)
    plt.savefig(f'{asteroid._id}')
    plt.close()

@timeit
def parse_horizons_response(asteroid_positons, stars_nearby_id):
    asteroid_table_headers = ["Object ID", "Date-Time", "RA", "Dec"]
    asteroid_table = tabulate(
        asteroid_positons, headers=asteroid_table_headers, tablefmt="grid"
    )
    stars_nearby_table = tabulate(
        stars_nearby_id, headers=["Star ID"], tablefmt="grid"
    )
    logging.info('\n' + asteroid_table +'\n'+ stars_nearby_table)

@timeit
def get_position(asteroid, session):
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    start_time = "'" +  datetime.today().strftime("%Y-%m-%d") + " " + asteroid.begin + "'"
    if asteroid.begin > asteroid.end:
        stop_time = (
            "'"+ (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            + " "
            + asteroid.end
            + "'"
        )
    else:
        stop_time = "'" + datetime.today().strftime("%Y-%m-%d") + " " + asteroid.end + "'"

    response = session.get(url,params={
        "format":"text",
        "COMMAND":asteroid._id,
        "OBJ_DATA":"NO",
        "EPHEM_TYPE":"OBSERVER",
        "START_TIME":start_time,
        "STOP_TIME":stop_time,
        "STEP_SIZE":"1m",
        "QUANTITIES":"1"
        })
    if response.status_code != 200:
        logging.exception("Horizons API error")
    return response


def main():
    email, password, page_name = read_config()
    driver = log_in(email, password, page_name)
    asteroids_list = get_asteroids_list(driver)
    close_website(driver)
    session = start_session()
    for asteroid in asteroids_list:
        api_response = get_position(asteroid, session)
        asteroid_positions = separate_data(api_response, asteroid)
        if len(asteroid_positions) > 0:
            temp(asteroid_positions,asteroid)
        #stars_nearby_id = get_collided_stars(asteroid_positions)
        #parse_horizons_response(asteroid_positions, stars_nearby_id)


if __name__ == "__main__":
    main()

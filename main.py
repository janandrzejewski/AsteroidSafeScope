from selenium import webdriver
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
    def __init__(self, id, begin, end):
        self.id = id
        self.begin = begin
        self.end = end

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
def get_data_objects(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")

    data_objects = []

    for row in rows:
        cells = row.find_all("td")

        if len(cells) >= 8:
            id = cells[1].find("span", id="id")
            if id:
                name_text = id.text

                begin_time = cells[7].text
                end_time = cells[8].text

                data_object = DataObject(name_text, begin_time, end_time)
                data_objects.append(data_object)

    return data_objects

@timeit
def close_website(driver):
    driver.quit()

@timeit
def get_collided_stars(data, radius=5):
    if data:
        collided_stars = set()
        for positon in data:
            coord = SkyCoord(ra=positon[2], dec=positon[3], unit=(u.hourangle, u.deg))
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
def separate_data(data, object):
    match = re.search(r"\$\$SOE.*?\$\$EOE", data.text, re.DOTALL)
    if match:
        fragment = match.group()
        lines = fragment.strip().split("\n")
        table_data = []

        for line in lines:
            line = line.strip()
            parts = line.split()
            if len(parts) >= 2:
                date_time = parts[0] + " " + parts[1]
                ra = parts[2] + " " + parts[3] + " " + parts[4]
                dec = parts[5] + " " + parts[6] + " " + parts[7]

                table_data.append([object.id, date_time, ra, dec])
        return table_data
    else:
        logging.exception("No ephemeris for target")
        return []
@timeit
def start_session():
    return requests.Session()

@timeit
def parse_horizons_response(obj_position_data, stars_nearby_data):
    obj_position_headers = ["Object ID", "Date-Time", "RA", "Dec"]
    obj_position_table = tabulate(
        obj_position_data, headers=obj_position_headers, tablefmt="grid"
    )
    stars_nearby_table = tabulate(
        stars_nearby_data, headers=["Star ID"], tablefmt="grid"
    )
    logging.info('\n' + obj_position_table +'\n'+ stars_nearby_table)

@timeit
def get_position(object, session):
    url = "https://ssd.jpl.nasa.gov/api/horizons.api"
    start_time = "'" +  datetime.today().strftime("%Y-%m-%d") + " " + object.begin + "'"
    if object.begin > object.end:
        stop_time = (
            "'"+ (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            + " "
            + object.end
            + "'"
        )
    else:
        stop_time = "'" + datetime.today().strftime("%Y-%m-%d") + " " + object.end + "'"

    response = session.get(url,params={
        "format":"text",
        "COMMAND":object.id,
        "OBJ_DATA":"NO",
        "EPHEM_TYPE":"OBSERVER",
        "START_TIME":start_time,
        "STOP_TIME":stop_time,
        "STEP_SIZE":"1h",
        "QUANTITIES":"1"
        })
    if response.status_code != 200:
        logging.exception("Horizons API error")
    return response


def main():
    email, password, page_name = read_config()
    driver = log_in(email, password, page_name)
    object_list = get_data_objects(driver)
    close_website(driver)
    session = start_session()
    for object in object_list:
        obj_position = get_position(object, session)
        obj_position_data = separate_data(obj_position, object)
        stars_nearby_data = get_collided_stars(obj_position_data)
        parse_horizons_response(obj_position_data, stars_nearby_data)


if __name__ == "__main__":
    main()

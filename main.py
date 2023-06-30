from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import configparser
from datetime import datetime, timedelta
import requests
import re
from tabulate import tabulate


class DataObject:
    def __init__(self, id, begin, end):
        self.id = id
        self.begin = begin
        self.end = end


def read_config():
    config = configparser.ConfigParser()
    config.read("config.ini")

    email = config.get("Credentials", "email")
    password = config.get("Credentials", "password")
    page_name = config.get("Page", "name")

    return email, password, page_name


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


def get_info(driver):
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


def close_website(driver):
    driver.quit()


def print_data(data, object):
    match = re.search(r"\$\$SOE.*?\$\$EOE", data.text, re.DOTALL)
    if match:
        fragment = match.group()
        lines = fragment.strip().split("\n")  # Podzielenie danych na linie

        table_data = []  # Dane tabeli

        for line in lines:
            line = (
                line.strip()
            )  # Usunięcie ewentualnych spacji na początku i końcu linii
            parts = (
                line.split()
            )  # Podzielenie linii na poszczególne części (odzielone spacjami)

            if len(parts) >= 8:
                date_time = parts[0] + " " + parts[1]  # Pobranie daty i czasu
                ra = (
                    parts[2] + " " + parts[3] + " " + parts[4]
                )  # Pobranie współrzędnych rektascensji (RA)
                dec = (
                    parts[5] + " " + parts[6] + " " + parts[7]
                )  # Pobranie współrzędnych deklinacji (Dec)

                # Dodanie wiersza do danych tabeli
                table_data.append([object.id, date_time, ra, dec])

        # Nagłówki kolumn
        headers = ["Object ID", "Date-Time", "RA", "Dec"]

        # Wyświetlenie tabeli, jeśli są dane
        if table_data:
            table = tabulate(table_data, headers=headers, tablefmt="grid")
            print(table)
        else:
            print("Brak danych do wyświetlenia.")


def get_position(data_objects):
    for object in data_objects:
        url = "https://ssd.jpl.nasa.gov/api/horizons.api"
        start_time = datetime.today().strftime("%Y-%m-%d") + " " + object.begin
        if object.begin > object.end:
            stop_time = (
                (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
                + " "
                + object.end
            )
        else:
            stop_time = datetime.today().strftime("%Y-%m-%d") + " " + object.end
        url += "?format=text&COMMAND='{}'&OBJ_DATA=NO&EPHEM_TYPE=OBSERVER".format(
            object.id
        )
        url += "&START_TIME='{}'&STOP_TIME='{}'&STEP_SIZE='1m'&QUANTITIES='1'".format(
            start_time, stop_time
        )
        response = requests.get(url)
        print_data(response, object)


def main():
    email, password, page_name = read_config()
    driver = log_in(email, password, page_name)
    data_objects = get_info(driver)
    close_website(driver)
    get_position(data_objects)


if __name__ == "__main__":
    main()

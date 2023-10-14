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


coord = SkyCoord(ra=58.53991193, dec=15.55325158, unit=(u.deg, u.deg))
j = Gaia.cone_search(coord, 0.009728750246624101 * u.deg)
print(j.get_results())
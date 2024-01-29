import json
from datetime import datetime

import pandas as pd
import requests
from dash import Dash, Input, Output, State, callback, dash_table, dcc, html

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

asteroid_table_headers = [
    "Asteroid ID",
    "Info",
    "Start",
    "Stop",
    "Stars qty",
    "Duration",
    "Position",
]

app.layout = html.Div(
    [
        dcc.Input(id="asteroid_list", type="text", placeholder="NAME OR ID", value=""),
        dcc.DatePickerSingle(
            id="date-picker-single", date=datetime.today().strftime("%Y-%m-%d")
        ),
        html.Button(id="submit-button-state", n_clicks=0, children="Submit"),
        html.Div(id="output-state"),
        dcc.Input(
            id="longitude", type="text", placeholder="Lon:", value="", persistence=True
        ),
        dcc.Input(
            id="latitude", type="text", placeholder="Lat:", value="", persistence=True
        ),
        dcc.Input(
            id="altitude", type="text", placeholder="Alt:", value="", persistence=True
        ),
        dash_table.DataTable(
            [], [{"name": i, "id": i} for i in asteroid_table_headers], id="tbl"
        ),
        html.Div(
            [
                html.P(
                    "This is an open-source project, developed by Jan Andrzejewski."
                ),
                html.P("Check out the GitHub repository:"),
                html.A(
                    "Link to GitHub Repository",
                    href="https://github.com/janandrzejewski/AsteroidSafeScope",
                    target="_blank",
                ),
            ],
            style={"position": "fixed", "bottom": 0, "right": 0, "margin": "10px"},
        ),
    ]
)


@app.callback(
    [Output("tbl", "data"), Output("output-state", "children")],
    Input("submit-button-state", "n_clicks"),
    State("asteroid_list", "value"),
    State("date-picker-single", "date"),
    State("longitude", "value"),
    State("latitude", "value"),
    State("altitude", "value"),
)
def update_output(n_clicks, asteroid_list, date, longitude, latitude, altitude):
    if n_clicks:
        data = {
            "asteroid_list": asteroid_list,
            "date": date,
            "longitude": float(longitude),
            "latitude": float(latitude),
            "altitude": float(altitude),
        }
        if asteroid_list is None or asteroid_list == '':
            error_message = "Please enter a list of asteroid names separated by commas."
            return [], html.Div(error_message, style={"color": "orange"})
        response = requests.post(
            "http://dash-api-app:5000/asteroid_data_processing", json=data
        )
        if response.status_code == 200:
            data_dict = response.json()
            df = pd.DataFrame(data_dict)
            return df.to_dict("records"), None
        else:
            error_message = f"Błąd HTTP: {response.status_code}"
            return [], html.Div(error_message, style={"color": "red"})
    else:
        return [], None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8050", debug=True)

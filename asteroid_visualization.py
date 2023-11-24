import json
from datetime import datetime

import pandas as pd
import requests
from dash import Dash, Input, Output, State, callback, dash_table, dcc, html

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = Dash(__name__, external_stylesheets=external_stylesheets)

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
        dcc.Input(id="asteroid_list", type="text", value="asteroid_list"),
        dcc.DatePickerSingle(
            id="date-picker-single", date=datetime.today().strftime("%Y-%m-%d")
        ),
        html.Button(id="submit-button-state", n_clicks=0, children="Submit"),
        html.Div(id="output-state"),
        dash_table.DataTable(
            [], [{"name": i, "id": i} for i in asteroid_table_headers], id="tbl"
        ),  # Initialize with an empty table
    ]
)


@app.callback(
    [Output("tbl", "data"), Output("output-state", "children")],
    Input("submit-button-state", "n_clicks"),
    State("asteroid_list", "value"),
    State("date-picker-single", "date"),
)
def update_output(n_clicks, asteroid_list, date):
    if n_clicks:
        data = {"asteroid_list": asteroid_list, "date": date}
        response = requests.post(
            "http://localhost:5000/asterod_data_processing", json=data
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
    app.run(debug=True)

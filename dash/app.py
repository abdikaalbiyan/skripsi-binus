import os
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
from dotenv import load_dotenv

from dash import Dash, Input, Output, dcc, html
from plotly.subplots import make_subplots
from pearson import get_correlation

load_dotenv()


engine = create_engine(f"postgresql+psycopg2://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}@127.0.0.1:6543/postgres")

data = pd.read_sql("""
    SELECT date, price, asset FROM(
        SELECT date, last AS price, 'bitcoin' AS asset
        FROM public.btc_price
        UNION
        SELECT date, close AS price, 'ihsg' AS asset
        FROM public.ihsg_price
        UNION
        SELECT date, buy AS price, 'emas_buy' AS asset
        FROM public.emas_price
        UNION
        SELECT date, sell AS price, 'emas_sell' AS asset
        FROM public.emas_price
    ) alls
    ORDER BY date""", engine).assign(Date=lambda data: pd.to_datetime(data["date"], format="%Y-%m-%d %H:%M:%S"))

assets = data["asset"].sort_values().unique()

external_stylesheets = [
    {
        "href": (
            "https://fonts.googleapis.com/css2?"
            "family=Lato:wght@400;700&display=swap"
        ),
        "rel": "stylesheet",
    },
]

app = Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    children=[
        html.Div(
            children=[
                html.H1(
                    children="Daily Closing Prices Analytics",
                    className="header-title"),
                html.P(
                    children=(
                        "Analyze the correlation between IHSG, Gold, and Bitcoin closing prices"
                    ),
                    className="header-description",
                ),
            ],
            className="header",
        ),
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.Div(children="Asset to Compare", className="menu-title"),
                        dcc.Dropdown(
                            id        = "asset-filter-1",
                            options   = [{"label": asset, "value": asset} for asset in assets],
                            value     = "bitcoin",
                            clearable = False,
                            className = "dropdown",
                        ),
                        dcc.Dropdown(
                            id        = "asset-filter-2",
                            options   = [{"label": asset, "value": asset} for asset in assets],
                            value     = "ihsg",
                            clearable = False,
                            className = "dropdown",
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.Div(
                            children="Date Range", className="menu-title"
                        ),
                        dcc.DatePickerRange(
                            id="date-range",
                            min_date_allowed= data["Date"].min(),
                            max_date_allowed= data["Date"].max(),
                            start_date      = data["Date"].min(),
                            end_date        = data["Date"].max(),
                        ),
                    ]
                ),
            ],
            className="menu",
        ),
        html.Div(
            children=[
                html.Div(
                    children=dcc.Graph(
                        id="price-chart",
                        config={"displayModeBar": False},
                    ),
                    className="card",
                ),
            ],
            className="wrapper",
        ),
    ]
)

@app.callback(
    Output("price-chart", "figure"),
    Input("asset-filter-1", "value"),
    Input("asset-filter-2", "value"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
)

def update_charts(asset1, asset2, start_date, end_date):
    filtered_data1 = data.query(
        "asset == @asset1"
        " and Date >= @start_date and Date <= @end_date"
    )
    filtered_data2 = data.query(
        "asset == @asset2"
        " and Date >= @start_date and Date <= @end_date"
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x = filtered_data1["date"], 
            y = filtered_data1["price"],
            name = f"{asset1} price",
            marker = {'color' : 'blue'}), 
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x = filtered_data2["date"], 
            y = filtered_data2["price"], 
            name = f"{asset2} price",
            marker = {'color' : 'green'}), 
        secondary_y=True,
    )

    # Add figure title
    fig.update_layout(title_text=f"Closing Price of {asset1.upper()} vs {asset2.upper()}", 
                      plot_bgcolor= "rgba(0, 0, 0, 0)",)

    # Set y-axes titles
    fig.update_yaxes(
        title_text = f"{asset1.upper()}", 
        secondary_y = False)
    fig.update_yaxes(
        title_text = f"{asset2.upper()}", 
        secondary_y=True)
    
    corr = get_correlation(start_date.replace('T00:00:00', ''),
                                end_date.replace('T00:00:00', ''),
                                asset1, asset2)
    
    fig.update_layout(legend_title_text=f"Coefficient: {round(corr['coefficient'], 3)} <br>\
                      {corr['status']}<br><br>", 
                      plot_bgcolor= "rgba(0, 0, 0, 0)",)
    fig.update_layout(legend_title_font_size=13) 
    fig.update_layout(legend_title_side="top") 

    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from numpy.ma.core import maximum_fill_value
import json
import os
# import folium for streamlit
from streamlit_folium import folium_static

from utilsBox import *

stations_df = pd.read_csv('Infos_Stations.csv')
price_df = pd.read_csv('Prix_2024.csv')

stations_df.rename(columns={'ID': 'id'}, inplace=True)

# Right format for the coordinates
stations_df['Longitude'] = stations_df['Longitude'].apply(float) / 10 ** 5
stations_df['Latitude'] = stations_df['Latitude'].apply(float) / 10 ** 5

# Change ids to strings
stations_df['id'] = stations_df['id'].apply(str)
price_df['id'] = price_df['id'].apply(str)

stations_df.rename(columns={'ID': 'id'}, inplace=True)

# Change brands column to lower case
stations_df['Enseignes'] = stations_df['Enseignes'].str.lower()

stations_df['Enseignes'] = stations_df['Enseignes'].apply(remove_accents)

# Aggregate enseignes with similar names
rename_enseigne(stations_df, 'access', 'taccess')
rename_enseigne(stations_df, 'total', 'total energy')
rename_enseigne(stations_df, 'carrefour', 'carrefour')
rename_enseigne(stations_df, 'intermarch', 'intermarche')
rename_enseigne(stations_df, 'huit', '8aHuit')
rename_enseigne(stations_df, 'system', 'system u')
rename_enseigne(stations_df, ' u', 'system u')
rename_enseigne(stations_df, 'esso', 'esso')

# endregion Prepare the data

# region sidebar
st.sidebar.header("Filters")

stations_types = pd.unique(stations_df['Type'])
stations_types_selection = st.sidebar.multiselect(
    "Station\'s type",
    options=stations_types,
    default=stations_types[:1]
)

selected_fuel = st.sidebar.selectbox(
    'Choose a fuel',
    options=['Gazole', 'SP95', 'SP98', 'E10', 'E85', 'GPLc']
)

nb_range_station = st.sidebar.number_input('Min stations\'s number for a brand', min_value=0, max_value=1000, value=100)
# endregion sidebar

dates= pd.to_datetime(price_df["Date"], format="%Y-%m-%d")

# Interface utilisateur pour sélectionner la date
selected_date = st.sidebar.date_input("Monitored date", value=dates.max(), min_value=dates.min(), max_value=dates.max())


total_nb_stations = len(stations_df)
stations_df = filter_nb_stations_df(stations_df, nb_range_station, selected_fuel)


st.title('Carrefour monitoring')

c1_1, c1_2 = st.columns(2)

c1_1.metric('Number of stations monitored',
           f'{len(stations_df)} stations',
           delta= - (total_nb_stations - len(stations_df)),
           delta_color='inverse'
           )

c1_2.html(f'Filtered by number of stations for each brand <br> (<strong>{nb_range_station}</strong> minimum)')


st.header('KPIs', divider='blue')

nearby_competitors_id = get_dict_nearby_competitors('carrefour', 10)
# st.write(number_competitor_per_target(nearby_competitors_id))

target_id = get_station_coord_dict(stations_df)
competitor_coord_dict = get_station_coord_dict(stations_df)

focus_target = list(target_id.keys())[1]

# Create a map centered on the first station
focus_target_map = folium.Map(location=target_id[focus_target], zoom_start=11)

icon_size = 30
# Add focus target marker
focus_target_icon = folium.features.CustomIcon(
    './logos/carrefour.png',
    icon_size=(icon_size, icon_size)
)

folium.Marker(
    location=target_id[focus_target],
    popup=focus_target,
    icon=focus_target_icon
).add_to(focus_target_map)


if len(nearby_competitors_id[focus_target]) > 0:
    for id in nearby_competitors_id[focus_target]:
        coords = [float(x) for x in competitor_coord_dict[id]]
        folium.Marker(
            location=coords,
            popup=id,
        ).add_to(focus_target_map)

else:
    print('No competitors found')


# display map
folium_static(focus_target_map)

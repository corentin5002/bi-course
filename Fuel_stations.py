import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import os

import utilsBox as ub

stations_df = pd.read_csv('Infos_Stations.csv')
price_df = ub.read_price_csv()

stations_df.rename(columns={'ID': 'id'}, inplace=True)

# join the two dataframes by the station id
main_df = pd.merge(stations_df, price_df, on='id')

# region sidebar
st.sidebar.header("Filtres")

default_enseignes_selection = []
selected_enseignes_sidebar = st.sidebar.multiselect(
    'Choisir les enseignes',
    options=pd.unique(main_df['Enseignes']),
    default=default_enseignes_selection
)

stations_types = pd.unique(main_df['Type'])

stations_types_selection = st.sidebar.multiselect(
    "Type de stations",
    options=stations_types,
    default=stations_types[:1]
)

selected_fuel = st.sidebar.selectbox(
    'Choisir le carburant',
    options=['Gazole', 'SP95', 'SP98', 'E10', 'E85', 'GPLc']
)

nb_range_station = st.sidebar.number_input('Nombre de stations min', min_value=0, max_value=1000, value=100)
# endregion sidebar

st.title("Analyse des stations d'essence")

st.header('Nombre de stations par type de carburant')

c1, c2, c3, c4, c5 = st.columns(5)

# SP95	SP98	E10	E85	GPLc
c1.metric("Gazole", ub.nb_station_fuel(main_df, 'Gazole'))
c2.metric("SP 95", ub.nb_station_fuel(main_df, 'SP95'))
c3.metric("SP 98", ub.nb_station_fuel(main_df, 'SP98'))
c4.metric("E10", ub.nb_station_fuel(main_df, 'E10'))
c5.metric("GPLc", ub.nb_station_fuel(main_df, 'GPLc'))

# st.header('Nombre d\'enseignes de stations')

# Set format for "Enseigne" column
main_df['Enseignes'] = main_df['Enseignes'].str.lower()

# Aggregate enseignes with similar names
ub.rename_brand(main_df, 'access', 'taccess')
ub.rename_brand(main_df, 'total', 'total energy')
ub.rename_brand(main_df, 'carrefour', 'carrefour')
ub.rename_brand(main_df, 'intermarch', 'intermarche')
ub.rename_brand(main_df, 'huit', '8aHuit')

c21, c22 = st.columns(2)

# c21.metric("Nombre d'enseignes", len(pd.unique(main_df['Enseignes'])))

# Apply filters on the main_df
working_df = main_df[main_df['Type'].isin(stations_types_selection)]

enseignes_selection = None

if len(selected_enseignes_sidebar) > 0:
    enseignes_selection = selected_enseignes_sidebar

else:
    # count the number of stations for each enseignes
    number_station_enseigne = main_df.groupby('Enseignes')['id'].unique().apply(len).sort_values(ascending=False)

    # Filter main_df by the enseignes that have more than 100 stations
    enseignes_selection = number_station_enseigne[number_station_enseigne > nb_range_station].index

    # c22.metric("Nombre d'enseignes sélectionnées", len(enseignes_selection))

# region Cleaning
# Clean independant, unknown enseignes
working_df = working_df[~working_df['Enseignes'].str.contains('independant')]
# st.write(f'[debug] Num enseignes {len(working_df["Enseignes"].unique())}')

# st.dataframe(working_df[["id", 'Enseignes', 'Date' ,'Gazole']])

# Replace extremes values
ub.replace_extremes(working_df, selected_fuel)

# endregion Cleaning

working_df = working_df[working_df['Enseignes'].isin(enseignes_selection)]

# region Visualisation price/date Evolution
enseignes_date_evolution = working_df.groupby(['Enseignes', 'Date'])[selected_fuel].mean()

# st.header('Prix moyen des enseignes sur l\'année 2024')
fig = px.line(enseignes_date_evolution, x=enseignes_date_evolution.index.get_level_values(1),
              y=enseignes_date_evolution.values, color=enseignes_date_evolution.index.get_level_values(0))

# st.plotly_chart(fig)

# region Carrefour comparision with other enseignes
target_brand = 'carrefour'

# st.header(f"Comparaison des stations de {target_brand} avec les autres enseignes")

target_df = working_df[working_df['Enseignes'] == target_brand]
other_df = working_df[working_df['Enseignes'] != target_brand]

c31, c32 = st.columns(2)
# c31.metric(f"Nombre de stations {target_brand}", len(pd.unique(target_df['id'])))
# c32.metric("Nombre d'autres stations", len(pd.unique(other_df['id'])))

# print number of unique ids in the target_df
# st.metric('len target ids', len(pd.unique(target_df['id'])))

# Select target's stations that are within a radius of 10km
coord = [45.783329, 3.08333]
search_radius = 20

# st.dataframe(target_df)

target_df = target_df[
    target_df.apply(lambda row: ub.within_radius(row, search_radius, coord), axis=1)
]

# Search for each target stations, the concurrent stations in a 10km radius

# Check if the json file already exists

target_metadata_df = target_df[['id', 'Latitude', 'Longitude']].drop_duplicates()
other_metadata_df = other_df[['id', 'Latitude', 'Longitude']].drop_duplicates()
target_metadata_df['id'] = target_metadata_df['id'].astype(str)
other_metadata_df['id'] = other_metadata_df['id'].astype(str)

# st.dataframe(target_metadata_df)

competition_stations_dict = {ids: set() for ids in target_metadata_df['id']}

json_file_exist = False
if os.path.exists(f'competition_stations_{target_brand}.json'):
    with open(f'competition_stations_{target_brand}_{search_radius}km.json', 'r') as f:
        competition_stations_dict = json.load(f)
        json_file_exist = True

else:
    for index, row in target_metadata_df.iterrows():
        # For each 'id' in target_df, search for the stations in other_df that are within a 10km radius
        if row['id'] not in competition_stations_dict:
            competition_stations_dict[row['id']] = set()
        for indexOthers, rowOthers in other_metadata_df.iterrows():
            if ub.within_radius(rowOthers, search_radius, [row['Latitude'] / 10 ** 5, row['Longitude'] / 10 ** 5]):
                competition_stations_dict[row['id']].add(rowOthers['id'])

    for key, value in competition_stations_dict.items():
        competition_stations_dict[key] = list(value)

# # Save the results in a json file
if not json_file_exist:
    with open(f'competition_stations_{target_brand}_{search_radius}km.json', 'w') as f:
        json.dump(competition_stations_dict, f)

stations_df['id'] = stations_df['id'].astype(str)
price_df['id'] = price_df['id'].astype(str)

# Bar plot of the number of concurrent stations for each target station
stations_competition_df = pd.DataFrame()
stations_competition_df['id'] = competition_stations_dict.keys()
stations_competition_df['nb_competition'] = [len(value) for value in competition_stations_dict.values()]

stations_competition_df['adress'] = [
    stations_df[stations_df['id'] == id]['Adresse'].values[0]
    + " , " +
    stations_df[stations_df['id'] == id]['Ville'].values[0]
    for id in stations_competition_df['id']
]

st.dataframe(stations_competition_df)

# st.header(f'Nombre de stations concurrentes pour chaque station {target_brand} dans un rayon de {search_radius} km')
fig = px.bar(stations_competition_df, x='adress', y='nb_competition')
# st.plotly_chart(fig)

# region Visualisation de chaque station
station_selector = st.selectbox('Selectionner une station', stations_competition_df['adress'])
id_station_selector = stations_competition_df[stations_competition_df['adress'] == station_selector]['id'].values[0]


# target_station_dict =

def get_date_price_dict(id, selected_fuel):
    competitor_df = price_df[price_df['id'] == id]

    return {row['Date']: row[selected_fuel] for index, row in competitor_df.iterrows()}


def get_price_fuel_dict(id_competitors):
    competitors_dict = {
        id_competitor: get_date_price_dict(id_competitor, selected_fuel)
        for id_competitor in id_competitors
    }
    return competitors_dict

def compare_fuel_prices(target_prices, competitor_prices):
    lower, equal, higher = {}, {}, {}

    for date, target_price in target_prices.items():
        lower[date] = 0
        equal[date] = 0
        higher[date] = 0

        for competitor_dict in competitor_prices:
            if date in competitor_dict.keys():
                competitor_price = competitor_dict[date]
                st.write(f"[debug] {target_price} {competitor_price}")
                if target_price < competitor_price:
                    lower[date] += 1
                elif target_price == competitor_price:
                    equal[date] += 1
                else:
                    higher[date] += 1

    return {'lower': lower, 'equal': equal, 'higher': higher}

# def get_comparison(id_target, id_competitor):

target_price_dict = get_date_price_dict(id_station_selector, selected_fuel)

competitors_price_dict = get_price_fuel_dict(competition_stations_dict[id_station_selector])
# st.write(competitors_price_dict)

# endregion Visualisation de chaque station

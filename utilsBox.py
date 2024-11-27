import math

import pandas as pd
from unidecode import unidecode
import os
import json


def filter_nb_stations_df(df, nb_stations, selected_fuel):
    # count the number of stations for each enseignes
    number_station_brand = df.groupby('Enseignes')['id'].unique().apply(len).sort_values(ascending=False)
    # print(number_station_enseigne)

    # Filter df by the enseignes that have more than 100 stations
    selected_brands = number_station_brand[number_station_brand > nb_stations].index.tolist()
    return df[df['Enseignes'].isin(selected_brands)]

def nb_station_fuel(df, fuel):
    fuel_info = df.groupby('id')[fuel].sum()
    fuel_info = fuel_info[fuel_info > 0]
    return len(fuel_info)


def rename_enseigne(df, search_term, new_name):
    df.loc[df['Enseignes'].str.contains(search_term), 'Enseignes'] = new_name


def remove_accents(text):
    return unidecode(text)

def get_quartiles(df, fuel):
    q1 = df[fuel].quantile(0.25)
    me = df[fuel].median()
    q3 = df[fuel].quantile(0.75)
    return {'q1': q1, 'median': me, 'q3': q3}


def replace_extremes(df, fuel):
    q = get_quartiles(df, fuel)
    df.loc[df[fuel] < q['q1'], fuel] = q['q1']
    df.loc[df[fuel] > q['q3'], fuel] = q['q3']


def haversine(lat1, lon1, lat2, lon2):
    # Convert degres to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Avg earth radius in km
    R = 6371.0

    # Difference of latitudes and longitudes
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine's formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon /
                                                                             2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance in km
    distance = R * c
    return distance

def within_radius(row, radius, center):
    return haversine(center[0], center[1], row['Latitude']/10**5, row['Longitude']/10**5) <= radius


def get_station_coord_dict(df):
    return {
        df.loc[id, 'id']: (df.loc[id, 'Latitude'], df.loc[id, 'Longitude'])
        for id in df.index
    }

def get_list_nearby_competitors(id_target, target_dict, competitor_dict, search_radius):
    L_competitors = list()

    for id_competitor in competitor_dict:
        distance = haversine(
            target_dict[id_target][0],
            target_dict[id_target][1],
            competitor_dict[id_competitor][0],
            competitor_dict[id_competitor][1]
        )

        if distance <= search_radius:
            L_competitors.append(id_competitor)

    return L_competitors

def get_dict_nearby_competitors(target_brand, search_radius=10):

    json_file_path = f'competitors_stations_{target_brand}_{search_radius}_km.json'

    target_brand_df = pd.read_csv('data/carrefour.csv')
    competitors_df = pd.read_csv('data/competitor.csv')

    target_id = get_station_coord_dict(target_brand_df)
    competitor_coord_dict = get_station_coord_dict(competitors_df)

    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as f:
            nearby_id_competitor_dict = json.load(f)
    else:
        nearby_id_competitor_dict = {
            id: get_list_nearby_competitors(id, target_id, competitor_coord_dict)
            for id in target_id
        }

        with open(json_file_path, 'w') as f:
            json.dump(nearby_id_competitor_dict, f)

    return nearby_id_competitor_dict

def number_competitor_per_target(dict):
    return {id: len(dict[id]) for id in dict}



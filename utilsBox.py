import math

import pandas as pd
from unidecode import unidecode
import os
import json


# region Read csv file
def read_price_csv():
    df_1 = pd.read_csv('data/prix_2024_jan_jun.csv')
    df_2 = pd.read_csv('data/prix_2024_jun_last.csv')
    return pd.concat([df_1, df_2])


# endregion Read csv file


# region Actions on dataframes

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


def rename_brand(df, search_term, new_name):
    """
    Dumb function to manually rename brand names
    :param df:
    :param search_term:
    :param new_name:
    :return:
    """
    df.loc[df['Enseignes'].str.contains(search_term), 'Enseignes'] = new_name


def remove_accents(text):
    return unidecode(text)


def get_quartiles(df, fuel):
    q1 = df[fuel].quantile(0.25)
    me = df[fuel].median()
    q3 = df[fuel].quantile(0.75)
    return {'q1': q1, 'median': me, 'q3': q3}


def replace_extremes(df, fuel):
    """
    Replace the values of the fuel column that are below the first quartile by the first quartile
    (Objectif: remove the abberrant values)
    :param df:
    :param fuel:
    :return:
    """
    q = get_quartiles(df, fuel)
    df.loc[df[fuel] < q['q1'], fuel] = q['q1']
    df.loc[df[fuel] < q['q1'], fuel] = q['q1']
    df.loc[df[fuel] > q['q3'], fuel] = q['q3']


# endregion Actions on dataframes

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
    return haversine(center[0], center[1], row['Latitude'] / 10 ** 5, row['Longitude'] / 10 ** 5) <= radius


def get_station_coord_dict(df):
    """
    Returns a dictionary with the id as key and the coordinates as value
    :param df:
    :return:
    """
    return {
        str(df.loc[id, 'id']): (df.loc[id, 'Latitude'], df.loc[id, 'Longitude'])
        for id in df.index
    }


def get_list_nearby_competitors(id_target, target_dict, competitor_dict, search_radius):
    """
    Returns the list of competitors that are within the search radius of the target station

    :param id_target:
    :param target_dict:
    :param competitor_dict:
    :param search_radius:
    :return:
    """

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
    """
    Returns a dictionary with the target station id as key and the list of competitors within the search radius as value
    { id_target: [id_competitor1, id_competitor2, ...] }
    :param target_brand:
    :param search_radius:
    :return:
    """
    json_file_path = f'data/competitors_stations_{target_brand}_{search_radius}_km.json'

    target_brand_df = pd.read_csv('data/carrefour.csv')
    competitors_df = pd.read_csv('data/competitor.csv')

    target_id = get_station_coord_dict(target_brand_df)
    competitor_coord_dict = get_station_coord_dict(competitors_df)

    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as f:
            nearby_id_competitor_dict = json.load(f)
    else:
        nearby_id_competitor_dict = {
            id: get_list_nearby_competitors(id, target_id, competitor_coord_dict, search_radius)
            for id in target_id
        }

        with open(json_file_path, 'w') as f:
            try:
                json.dump(nearby_id_competitor_dict, f)
            except:
                pass

    return nearby_id_competitor_dict


def get_target_nearby_brand_dict(stations_dict, stations_df):
    """
    Returns a dictionary with the target station id as key and the list of competitors within the search radius as value

    { id_target: { brand1: [id_competitor1, id_competitor2, ...], brand2: [id_competitor1, id_competitor2, ...], ... } }
    :param stations_dict:
    :param stations_df:
    :return:
    """

    final_dict = {}
    for local_target_id in stations_dict:
        list_brand = stations_df[stations_df['id'].isin(stations_dict[local_target_id])]['Enseignes'].unique().tolist()
        local_target_dict = {}

        # Filter ids in nearby_competitor_dict that got the brand
        for brand in list_brand:
            local_target_dict[brand] = \
            stations_df[(stations_df['id'].isin(stations_dict[local_target_id])) & (stations_df['Enseignes'] == brand)][
                'id'].tolist()

        final_dict[local_target_id] = local_target_dict

    return final_dict


def number_competitor_per_target(dict):
    return {id: len(dict[id]) for id in dict}


def get_brand_stations_dict(df):
    """
    Returns a dictionary with the brand as key and the list of stations as value

    { brand1: [id_station1, id_station2, ...], brand2: [id_station1, id_station2, ...], ... }
    :param df:
    :return:
    """
    list_brands = df['Enseignes'].unique().tolist()
    return {
        brand: df[df['Enseignes'] == brand]['id'].tolist()
        for brand in list_brands
    }


def get_brand_price_dict(price_df, brand_stations_dict, selected_fuel, selected_date_range):
    """
    Returns a dict with the price of the selected fuel for each station of each brand for each day in the selected date range

    { day1: {
        brand1: {
            fuel: [station_price1, station_price2, ...],
            mean: mean_price
        },
        ...
    },
    :param df:
    :param brand:
    :return:
    """
    if type(selected_date_range) == list:
        date_string = f"{pd.to_datetime(selected_date_range[0]).strftime('%Y-%m-%d')}_{pd.to_datetime(selected_date_range[1]).strftime('%Y-%m-%d')}"
        selected_date_range = pd.date_range(selected_date_range[0], selected_date_range[1])
    else:
        date_string = f'{pd.to_datetime(selected_date_range).strftime('%Y-%m-%d')}'
        selected_date_range = pd.date_range(selected_date_range, selected_date_range)

    path_file = f"data/brand_price_dict_{selected_fuel}_{date_string}.json"
    if os.path.exists(path_file):
        with open(path_file, 'r') as f:
            brand_price_dict = json.load(f)
    else:
        # Create the list of days within the selected date range
        brand_price_dict = {
            day.strftime('%Y-%m-%d'): {
                brand: {
                    selected_fuel: price_df[
                        (price_df['Date'] >= day) &
                        (price_df['id'].isin(brand_stations_dict[brand]))
                        ][selected_fuel].to_list(),

                    'mean': price_df[
                        (price_df['Date'] >= day) &
                        (price_df['id'].isin(brand_stations_dict[brand]))
                        ][selected_fuel].mean()
                }
                for brand in brand_stations_dict
            }
            for day in selected_date_range
        }

        with open(path_file, 'w') as f:
            json.dump(brand_price_dict, f)

    return brand_price_dict

# Graph functions

def get_brand_daily_mean_price_df(brand_price_dict):
    """
    Returns a DataFrame with columns ['Date', 'Brand', 'Price'] from a brand_price_dict {day: {brand: {mean: price}}}
    :param brand_price_dict: Dictionary with the structure {day: {brand: {mean: price}}}
    :return: pandas DataFrame
    """
    data = []

    for day, brands in brand_price_dict.items():
        for brand, details in brands.items():
            data.append({
                'Date': day,
                'Brand': brand,
                'Price': details['mean']
            })

    temp_df = pd.DataFrame(data, columns=['Date', 'Brand', 'Price'])

    return temp_df


def get_id_adress_dict(df):
    return {
        f'{row["Adresse"]}, {row["Ville"]}': row['id']
        for _, row in df.iterrows()
    }


import pandas as pd
import plotly.express as px
import numpy as np
import utilsBox as ub
from pprint import pprint
import json
import os
import folium
from unidecode import unidecode
import streamlit as st


st.title('Treatment and functions')

st.markdown('''
# Explanations

This page contains the functions and treatment I've done over the 4 days of the BI course.

I put these as a proof of my work on the optimisation for the calculations. Optimizing using python dictionaries
''')

st.markdown('''
```python
stations_df = pd.read_csv('Infos_Stations.csv')
price_df = ub.read_price_csv()

# how to rename a column
stations_df.rename(columns={'ID': 'id'}, inplace=True)

stations_df.head()

# join the two dataframes by the station id

df = pd.merge(stations_df, price_df, on='id')
df.head()

# Count number of stations that sell gazole
selected_fuel = 'Gazole'

Gazole = df.groupby('id')["Gazole"].sum()

print('len gazole', len(Gazole))
# exclude lines where Gazole is < 1

Gazole = Gazole[Gazole > .0]

Gazole


# set every enseignes to lower case to avoid duplicates
df['Enseignes'] = df['Enseignes'].str.lower()


selected_brands = ['total energy', 'carrefour', 'intermarche', '8ahuit']

selected_brands_df = df[df['Enseignes'].isin(selected_brands)]
brands_date_evolution = selected_brands_df.groupby(['Enseignes', 'Date'])[selected_fuel].mean()



# plot the price of gazole for each enseignes from the groupby object using express

fig = px.line(brands_date_evolution, x=brands_date_evolution.index.get_level_values(1),
              y=brands_date_evolution.values, color=brands_date_evolution.index.get_level_values(0))
fig.show()

print(len(pd.unique(df['Enseignes'])))
pd.unique(df['Enseignes'])

# Right format for the coordinates
stations_df['Longitude'] = stations_df['Longitude'].apply(float) / 10 ** 5
stations_df['Latitude'] = stations_df['Latitude'].apply(float) / 10 ** 5

# Change ids to strings
stations_df['id'] = stations_df['id'].apply(str)
price_df['id'] = price_df['id'].apply(str)
df['id'] = df['id'].apply(str)

stations_df.rename(columns={'ID': 'id'}, inplace=True)

# Change brands column to lower case
stations_df['Enseignes'] = stations_df['Enseignes'].str.lower()

# Get rid of the accents and special character (ex: é -> e)
def remove_accents(text):
    return unidecode(text)

stations_df['Enseignes'] = stations_df['Enseignes'].apply(remove_accents)
df['Enseignes'] = df['Enseignes'].apply(remove_accents)

# Aggregate enseignes with similar names
ub.rename_brand(stations_df, 'access', 'taccess')
ub.rename_brand(stations_df, 'total', 'total energy')
ub.rename_brand(stations_df, 'carrefour', 'carrefour')
ub.rename_brand(stations_df, 'intermarch', 'intermarche')
ub.rename_brand(stations_df, 'huit', '8aHuit')
ub.rename_brand(stations_df, 'system', 'system u')
ub.rename_brand(stations_df, ' u', 'system u')
ub.rename_brand(stations_df, 'esso', 'esso')


ub.rename_brand(df, 'access', 'taccess')
ub.rename_brand(df, 'total', 'total energy')
ub.rename_brand(df, 'carrefour', 'carrefour')
ub.rename_brand(df, 'intermarch', 'intermarche')
ub.rename_brand(df, 'huit', '8aHuit')
ub.rename_brand(df, 'system', 'system u')
ub.rename_brand(df, ' u', 'system u')
ub.rename_brand(df, 'esso', 'esso')

stations_df.head()

# count the number of stations for each enseignes
number_station_brand = df.groupby('Enseignes')['id'].unique().apply(len).sort_values(ascending=False)
# print(number_station_enseigne)

# Filter df by the enseignes that have more than 100 stations
selected_brands = number_station_brand[number_station_brand > 100].index.tolist()
selected_brands_df = df[df['Enseignes'].isin(selected_brands)]

# group by enseignes and date and calculate the mean of gazole
brands_date_evolution = selected_brands_df.groupby(['Enseignes', 'Date'])[selected_fuel].mean()



# Filter price_df and stations_df for the enseignes that got more than 100 stations
before = len(stations_df)
stations_df = stations_df[stations_df['Enseignes'].isin(selected_brands)]
print(f'{before} -> {len(stations_df)}')

before = len(price_df)
price_df = price_df[price_df['id'].isin(stations_df['id'])]

print(f'{before} -> {len(price_df)}')

df = df[ df['id'].isin( stations_df['id'].tolist() ) ]


# plot the price of gazole for each enseignes from the groupby object using express
fig = px.line(brands_date_evolution, x=brands_date_evolution.index.get_level_values(1),
              y=brands_date_evolution.values, color=brands_date_evolution.index.get_level_values(0))
fig.show()

# ## DAY 2 : Competitor comparison per "enseignes" (brand)
# **Get per carrefour stations, the concurrents within the 10km radius**

target_brand = 'carrefour'
search_radius = 10

target_brand_df = stations_df[stations_df['Enseignes'] == target_brand]
target_brand_df.head()

competitor_df = stations_df[stations_df['Enseignes'] != target_brand]
print(f"Number of competitors' stations (other brand than {target_brand}): {len(competitor_df)}")
print(f"Number of {target_brand}'s stations: {len(target_brand_df)}")

# Dict containing the id of the carrefour stations and the list of concurrents within the 10km radius

target_brand_df.to_csv('data/carrefour.csv')
competitor_df.to_csv('data/competitor.csv')

def get_station_coord_dict(df):
    return {
        df.loc[id, 'id']: (df.loc[id, 'Latitude'], df.loc[id, 'Longitude'])
        for id in df.index
    }


target_id = get_station_coord_dict(target_brand_df)
competitor_coord_dict = get_station_coord_dict(competitor_df)

target_id

def get_list_nearby_competitors(id_target, target_dict, competitor_dict):
    L_competitors = list()

    for id_competitor in competitor_dict:
        distance = ub.haversine(
            target_dict[id_target][0],
            target_dict[id_target][1],
            competitor_dict[id_competitor][0],
            competitor_dict[id_competitor][1]
        )

        if distance <= search_radius:
            L_competitors.append(id_competitor)

    return L_competitors

json_file_path = f'competitors_stations_{target_brand}_{search_radius}_km.json'

if os.path.exists(json_file_path):
    with open(json_file_path, 'r') as f:
        nearby_id_competitor_dict = json.load(f)
else:
    nearby_id_competitor_dict = {id: get_list_nearby_competitors(id, target_id, competitor_coord_dict) for id in target_id}


pprint(nearby_id_competitor_dict)


with open(json_file_path, "w") as f:
    json.dump(nearby_id_competitor_dict, f)

def number_concurent_per_target(dict):
    return {id: len(dict[id]) for id in dict}

pprint(number_concurent_per_target(nearby_id_competitor_dict))

# json_file_exist = False
#
#
# if os.path.exists(json_file_path):
#     with open(json_file_path, "r") as f:
#         target_nearby_competitor_dict = json.load(f)

# DAY 3 :

focus_target = list(target_id.keys())[1]  # TODO: Change selection of this stations
print(focus_target)
print(nearby_id_competitor_dict[focus_target])

print(f"Focus target: {target_id[focus_target][0]} {type(target_id[focus_target][0])}")

map = folium.Map(location=list(target_id[focus_target]))

target_icon = folium.features.CustomIcon(
    './logos/carrefour.png',
    icon_size=(50, 50)
)

# Add points in folium map
folium.Marker(
    location=target_id[focus_target],
    popup=focus_target,
    icon=target_icon
).add_to(map)

if len(nearby_id_competitor_dict[focus_target]) > 0:
    for id in nearby_id_competitor_dict[focus_target]:
        coords = [float(x) for x in competitor_coord_dict[id]]
        folium.Marker(
            location=coords,
            popup=id,
        ).add_to(map)

else:
    print('No competitors found')

# Compare price for a date with competitors

def get_target_nearby_brand_dict(station_dict):

    final_dict = {}
    for local_target_id in station_dict:
        list_brand = stations_df[stations_df['id'].isin(station_dict[local_target_id])]['Enseignes'].unique().tolist()
        local_target_dict = {}

        # Filter ids in nearby_competitor_dict that got the brand
        for brand in list_brand:
            local_target_dict[brand] = stations_df[(stations_df['id'].isin(station_dict[local_target_id])) & (stations_df['Enseignes'] == brand)]['id'].tolist()

        final_dict[local_target_id] = local_target_dict

    return final_dict

selected_date = '2024-07-01'

def compare_price_with_competitors(id_focus_target):

    brands_nearby = target_brand_dict[id_focus_target]

    brands_counts = {brand: count_price_competitors(brand, brands_nearby, id_focus_target) for brand in brands_nearby}
    return  brands_counts

def count_price_competitors(brand, brands_nearby, id_focus_target):
    # Filter the selected date_price_df by selecting only station of the brand

    date_brand_price_df = date_price_df[date_price_df['id'].isin(brands_nearby[brand])]

    target_row = date_price_df[date_price_df['id'] == id_focus_target]

    if target_row.empty:
        return 0, 0, 0

    date_brand_price_df = pd.concat([date_brand_price_df, target_row], ignore_index=True)

    date_brand_price_df.sort_values(by=selected_fuel, inplace=True)
    date_brand_price_df.reset_index(drop=True, inplace=True)

    # Find index of the target in the sorted dataframe
    target_sorted_index = date_brand_price_df[date_brand_price_df['id'] == id_focus_target].index[0]

    # Get its price
    focus_target_price = date_brand_price_df.loc[target_sorted_index, selected_fuel]
    lower, low_eq, high_eq, higher = 0, 0, 0, 0

    # check above and below the focus target
    while (
            target_sorted_index - low_eq >= 0 and
            focus_target_price == date_brand_price_df.loc[target_sorted_index - low_eq, selected_fuel]
    ):
        low_eq += 1

    # Remove the count of itself
    low_eq -= 1
    lower = target_sorted_index - low_eq

    while (
            target_sorted_index + high_eq < len(date_brand_price_df) and
            focus_target_price == date_brand_price_df.loc[target_sorted_index + high_eq, selected_fuel]

    ):
        high_eq += 1

    high_eq -= 1
    higher = len(date_brand_price_df) - (target_sorted_index + 1) - high_eq

    eq = low_eq + high_eq

    return lower, eq, higher


nearby_brand_file_path = f'{target_brand}_nearby_brand_{search_radius}_km.json'

if os.path.exists(nearby_brand_file_path):
    with open(nearby_brand_file_path, "r") as f:
        target_brand_dict = json.load(f)

else:
    target_brand_dict = get_target_nearby_brand_dict(nearby_id_competitor_dict)

    with open(nearby_brand_file_path, "w") as f:
        json.dump(target_brand_dict, f)

date_price_df = price_df[price_df['Date'] == selected_date]



detail_nb_competitors_dict = {
    id: compare_price_with_competitors(id)
    for id in nearby_id_competitor_dict
}

pprint(detail_nb_competitors_dict)



def create_detail_df(detail_nb_competitors_dict):
    detail_dict = {}

    for id in detail_nb_competitors_dict:
        for brand in detail_nb_competitors_dict[id]:
            lower, eq, higher = detail_nb_competitors_dict[id][brand]

            if brand not in detail_dict:
                detail_dict[brand] = {
                    'lower': lower,
                    'eq': eq,
                    'higher': higher
                }
            else:
                detail_dict[brand]['lower'] += lower
                detail_dict[brand]['eq'] += eq
                detail_dict[brand]['higher'] += higher

    detail_df = pd.DataFrame(detail_dict).T

    return detail_df

detail_df = create_detail_df(detail_nb_competitors_dict)

detail_df


# Bar plot of the number of competitors for each category
fig = px.bar(detail_df, x=detail_df.index, y=['lower', 'eq', 'higher'],
             title='Number of competitors around the focus target',
             labels={'value': 'Number of competitors', 'index': 'Brand'},
             barmode='stack'
             )

fig.show()

len(nearby_id_competitor_dict.keys())

```
''')


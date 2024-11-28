import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import folium_static
from datetime import datetime
from utilsBox import *

stations_df = pd.read_csv('Infos_Stations.csv')
price_df = read_price_csv()

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
rename_brand(stations_df, 'access', 'taccess')
rename_brand(stations_df, 'total', 'total energy')
rename_brand(stations_df, 'carrefour', 'carrefour')
rename_brand(stations_df, 'intermarch', 'intermarche')
rename_brand(stations_df, 'huit', '8aHuit')
rename_brand(stations_df, 'system', 'system u')
rename_brand(stations_df, ' u', 'system u')
rename_brand(stations_df, 'esso', 'esso')
rename_brand(stations_df, 'indepen', 'independant')
rename_brand(stations_df, 'autre', 'independant')

# Remove the independant enseignes from the dataframe
stations_df = stations_df[stations_df['Enseignes'] != 'independant']

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

search_radius = st.sidebar.select_slider('Search radius (km)', options=range(5, 51, 5), value=10)
# endregion sidebar

dates = pd.to_datetime(price_df["Date"], format="%Y-%m-%d")
price_df['Date'] = pd.to_datetime(price_df['Date'], format="%Y-%m-%d")

default_date_range = [datetime(2024, 4, 1), datetime(2024, 4, 15)]

# Interface utilisateur pour sélectionner la date

selected_date_range = st.sidebar.date_input("Monitored date", value=default_date_range, min_value=dates.min(),
                                            max_value=dates.max())
st.sidebar.html('<strong>Advice</strong> : Select more than a month might be long to load the first time')

if len(selected_date_range) == 2:
    selected_date_range = [pd.to_datetime(date) for date in selected_date_range]
    # st.write(f'original price df size :{len(price_df)}')
    price_df = price_df[
        (price_df['Date'] >= selected_date_range[0]) &
        (price_df['Date'] <= selected_date_range[1])
        ]
    # st.write(f'original price df size :{len(price_df)}')
    string_range_date = f'{selected_date_range[0].strftime("%Y-%m-%d")} to {selected_date_range[1].strftime("%Y-%m-%d")}'

else:
    selected_date_range = pd.to_datetime(selected_date_range[0])
    # st.write(f'original price df size :{len(price_df)}')
    price_df = price_df[price_df['Date'] == selected_date_range]
    # st.write(f'filtered price df size :{len(price_df)}')
    string_range_date = f'{selected_date_range.strftime("%Y-%m-%d")}'


total_nb_stations = len(stations_df)
stations_df = filter_nb_stations_df(stations_df, nb_range_station, selected_fuel)

st.title('Carrefour monitoring')

c1_1, c1_2 = st.columns(2)

c1_1.metric('Number of stations monitored',
            f'{len(stations_df)} stations',
            delta=- (total_nb_stations - len(stations_df)),
            delta_color='inverse'
            )

c1_1.html(f'Filtered by number of stations for each brand <br> (<strong>{nb_range_station}</strong> minimum)')

nearby_competitors_id = get_dict_nearby_competitors('carrefour', search_radius)

c1_2.metric('Number of competitors',
            sum([x for x in number_competitor_per_target(nearby_competitors_id).values()])
            )
st.header(f'KPIs from {string_range_date}', divider='blue')

# region Folium map
id_coord_dict = get_station_coord_dict(stations_df)

focus_target = list(id_coord_dict.keys())[1]

# Create a map centered on the first station
focus_target_map = folium.Map(location=id_coord_dict[focus_target], zoom_start=11)

icon_size = 30
# Add focus target marker
focus_target_icon = folium.features.CustomIcon(
    './logos/carrefour.png',
    icon_size=(icon_size, icon_size)
)

folium.Marker(
    location=id_coord_dict[focus_target],
    popup=focus_target,
    icon=focus_target_icon
).add_to(focus_target_map)

if len(nearby_competitors_id[focus_target]) > 0:
    for id in nearby_competitors_id[focus_target]:
        coords = [float(x) for x in id_coord_dict[id]]
        folium.Marker(
            location=coords,
            popup=id,
        ).add_to(focus_target_map)

else:
    print('No competitors found')

# display map
folium_static(focus_target_map)
# endregion Folium map

# region Price evolution

# Convert selected_date_range to pd datetime
price_df = price_df[price_df['id'].isin(stations_df['id'])]

# Get the mean price for each fuel per brand

brand_stations_dict = get_brand_stations_dict(stations_df)

brand_price_dict = get_brand_price_dict(price_df, brand_stations_dict, selected_fuel, selected_date_range)

# KPIS

target_brand_name = 'carrefour'

target_brand_mean_price = float(
    str(f"{np.mean([brand_price_dict[day][target_brand_name]['mean'] for day in brand_price_dict]):.2f}"))
st.metric(
    f'{'carrefour'.capitalize()} price',
    f'{target_brand_mean_price} €/L'
)

brand_list = list(brand_stations_dict.keys())
kpi_columns = [st.columns(3) for _ in range(len(brand_list) // 3)]

# remove target brand from the brand list
brand_list.remove(target_brand_name)

for brand in brand_list:
    brand_dayly_mean_price = [brand_price_dict[day][brand]['mean'] for day in brand_price_dict]

    delta = np.mean(brand_dayly_mean_price) - target_brand_mean_price

    # get on which row the brand is
    row = brand_list.index(brand) // 3
    column = brand_list.index(brand) % 3

    kpi_columns[row][column].metric(
        f'{brand.capitalize()} price',
        f'{np.mean(brand_dayly_mean_price):.2f} €/L',
        delta=f'{delta:.2f} €/L',
    )

# region Graph

brand_dayly_mean_price_df = get_brand_daily_mean_price_df(brand_price_dict)

# Plot of the mean prices of selected fuel for each brand

fig = px.line(brand_dayly_mean_price_df,
              x='Date',
              y='Price',
              color='Brand'
              )

fig.update_traces(
    line=dict(
        width=4,
        color='lime'
    ),
    selector=dict(
        name=target_brand_name
    )
)

st.subheader(
    f'Price evolution from {string_range_date}',
    divider='blue'
)
st.plotly_chart(fig)


# endregion Graph

# endregion Price evolution


# region station monitoring

target_df = pd.read_csv('data/carrefour.csv')
target_df = target_df[target_df['Type'].isin(stations_types_selection)]
target_df['id'] = target_df['id'].apply(str)

competitor_df = pd.read_csv('data/competitor.csv')
competitor_df = competitor_df[competitor_df['Type'].isin(stations_types_selection)]
competitor_df['id'] = competitor_df['id'].apply(str)

target_id_adress_dict = get_id_adress_dict(target_df)

selected_stations = st.multiselect('Select the target station', options=list(target_id_adress_dict.keys()))

center_france_coord = [46.603354, 1.888334]
if len(selected_stations) > 0:
    map = folium.Map(location=center_france_coord, zoom_start=6)
    count = 0
    for station in selected_stations:
        station_id = target_id_adress_dict[station]

        folium.Marker(
            location=id_coord_dict[station_id],
            icon=folium.Icon(color='red'),
            popup=station
        ).add_to(map)

        for competitor_id in nearby_competitors_id[station_id]:
            competitor_address = stations_df[stations_df['id'] == competitor_id]['Adresse'].values[0]
            competitor_popup = f"<b>{stations_df[stations_df['id'] == competitor_id]['Enseignes'].values[0]} : </b><br>{stations_df[stations_df['id'] == competitor_id]['Adresse'].values[0]},{stations_df[stations_df['id'] == competitor_id]['Ville'].values[0]}",
            folium.Marker(
                location=id_coord_dict[competitor_id],
                popup=competitor_popup,
            ).add_to(map)

            count += 1

    folium_static(map)

    st.metric(f'Competitors found', count)

# region station monitoring

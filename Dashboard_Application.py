import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import time
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
import io
from pytz import timezone
import re

# Define the default page configuration settings
default_config = {
    'page_title': 'My Streamlit App',
    'page_icon': None,
    'layout': 'wide',
    'initial_sidebar_state': 'auto'
}

# Set the page configuration
st.set_page_config(**default_config)

# Define constants for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = 'fresh-deck-324409-5a5c7482c3d0.json'

st.title("DATA DASHBOARD & LIVE LOCATIONS")
# Create a Streamlit container to display the results
filename_container = st.empty()
tabs_container = st.empty()

interval_seconds = 30
total_records = 0
processed_file_ids = []


# Define function to authenticate and create Google Drive API service

def create_drive_service():
    creds = None
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    except Exception as e:
        st.write(f"Error: {e}")
    service = build('drive', 'v3', credentials=creds)
    return service


# Define function to read CSV files from a Google Drive folder
def read_csv_from_drive(folder_id):
    service = create_drive_service()
    file_list = []
    try:
        query = f"'{folder_id}' in parents and mimeType='text/csv'"
        results = service.files().list(q=query, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        for item in items:
            file_id = item['id']
            file_name = item['name']
            file = service.files().get_media(fileId=file_id).execute()
            csv_data = pd.read_csv(io.StringIO(file.decode('utf-8')))
            file_list.append((file_name, csv_data))
    except HttpError as error:
        st.write(f"An error occurred: {error}")
    return file_list


# Define function to load CSV data into a pandas DataFrame
def load_data(file_list):
    df_list = []
    for file in file_list:
        file_name, csv_data = file
        csv_data.columns = [col.strip().lower() for col in csv_data.columns]
        df_list.append(csv_data)
    df = pd.concat(df_list, axis=0)
    return df


# Define function to display summary statistics of a DataFrame
def display_summary_statistics(df):
    global total_records

    # Compute the analysis metrics
    total_records += df['Count'].sum()

    # create a timezone object for IST
    ist_times = pd.to_datetime(df['Last Time IST'], format= '%d/%b/%Y %H:%M:%S', errors = 'coerce')
    ist_times = ist_times[ist_times.notna()]
    start_time = ist_times.min().strftime('%d/%b/%Y %H:%M:%S')
    end_time = ist_times.max().strftime('%d/%b/%Y %H:%M:%S')

    
    # Set the option to show full contents of the "Last Time IST" column
    pd.set_option('display.max_colwidth', None)
    mac_stats = df[['No', 'Mac ID', 'Location', 'Average Interval', 'Maximum Interval',
                    'Minimum Interval', 'Last Time IST', 'Active', 'Battery', 'F/w Version']].reset_index(
        drop=True)
    mac_stats.index += 1
    
    # format the "Average Interval" column to display with two decimal places
    mac_stats["Average Interval"] = mac_stats["Average Interval"].map("{:.2f}".format)

    # format the other columns to display without decimal places
    mac_stats = mac_stats.applymap(lambda x: "{:.0f}".format(x) if isinstance(x, (int, float)) else x)

    
    # Display the updated results
    st.subheader(f"1. Total Records: {int(total_records)}")
   
    # Display the updated results
    st.subheader(f"2. Start Time: {start_time} IST")
    
    # Display the updated results
    st.subheader(f"3. End Time: {end_time} IST")
    
    # Display the updated results
    st.subheader("4. Summary Table:")

    # Set the "No" column as the index
    mac_stats = mac_stats.set_index("No")

    # Display the dataframe with increased column width
    st.dataframe(mac_stats, width=7500)

    

total_records1 = 0


# Define function to display a map of a DataFrame's latitude and longitude data
def display_map(df):
    global total_records1
    # Compute the analysis metrics
    total_records1 += df['Count'].sum()

    # create a timezone object for IST
    ist_times = pd.to_datetime(df['Last Time IST'], format= '%d/%b/%Y %H:%M:%S', errors = 'coerce')
    ist_times = ist_times[ist_times.notna()]
    start_time = ist_times.min().strftime('%d/%b/%Y %H:%M:%S')
    end_time = ist_times.max().strftime('%d/%b/%Y %H:%M:%S')

    # Display the updated results
    # create a folium map centered on India
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=4.5)

    # Create a marker cluster for the locations
    marker_cluster = MarkerCluster().add_to(m)

    # Add markers for each location in the data, with color based on the value of 'Status' column
    active_locations = set()
    active_locations_names = []
    for i, row in df.iterrows():
        if row['Active'] == 1:
            active_locations.add((row['Location']))
            icon_color = 'green'
        else:
            icon_color = 'orange'
        popup_text = f"<b>{row['Mac ID']}"
        folium.Marker(location=[row['Latitude'], row['Longitude']], tooltip=popup_text,
                      icon=folium.Icon(color=icon_color)).add_to(marker_cluster)

        active_locations_names = ','.join(active_locations).replace('{', '').replace('}', ''). \
            replace("'", '')

    active_records = len(df[df['Active'] == 1])

    st.subheader("Live map of locations")
    # folium_static(m, width=800, height=600)
    folium_static(m, width=525, height=600)

    st.subheader(f"1. Total Records: {int(total_records1)}")

    st.subheader(f"2. Start Time: {start_time} IST")

    st.subheader(f"3. End Time: {end_time} IST")

    st.subheader(f"4. Active Devices: {active_records} ")

    st.subheader(f"5. Location of Active Device: {active_locations_names} ")


def display_unknown_macid(df):
    if any(value == 1 for value in df['Unknown Mac ID']):
        st.warning('Unknown Mac ID present')
    else:
        st.warning('None')


def display_no_data(df):
    no_data_mac_ids = df.loc[df['No Data'] == 1, 'Mac ID'].tolist()
    if len(no_data_mac_ids) == 0:
        st.subheader("Data is available for all Mac IDs.")
    else:
        st.write("The following Mac IDs have No Data: ", no_data_mac_ids)



def display_data_unchanged(df):
    unchanged_mac_ids = df.loc[df['Data Unchanged'] == 1, 'Mac ID'].tolist()
    if len(unchanged_mac_ids) == 0:
        st.warning('None')
    else:
        st.write("The following Mac IDs have unchanged data: ", unchanged_mac_ids)


def display_data_dead(df):
    data_dead_mac_ids = df.loc[df['Data Dead'] == 1, 'Mac ID'].tolist()
    message_placeholder = st.empty()
    if len(data_dead_mac_ids) > 0:
        message_placeholder.write("The following Mac IDs have Data Dead:")
        message_placeholder.write(data_dead_mac_ids)
    else:
        message_placeholder.warning("None")


def main():
    folder_id = '1G4FnXmCN2Els0KqI0eG3vE66hpohEspl'
    file_list = []
    if folder_id:
        # Read CSV files from Google Drive folder
        new_files = read_csv_from_drive(folder_id)
        if new_files:
            # Filter only the files with the "chunk{n}.csv" format
            file_list = [(file_name, df) for (file_name, df) in new_files if re.match(r"chunk\d+\.csv", file_name)]

        if file_list:
            # Sort files by chunk number
            file_list = sorted(file_list, key=lambda x: int(x[0].replace('chunk', '').replace('.csv', '')))

        for file_name, df in file_list:
            # Display file name
            with filename_container:
                st.write(f"File: {file_name}")

            # Display summary statistics and map in tabs
            with tabs_container:
                tabs = st.tabs(
                    ["Summary Statistics", "Map", "Unknown Mac ID", "No Data", "Data Unchanged", "Data Dead"])
                with tabs[0]:
                    display_summary_statistics(df)
                with tabs[1]:
                    display_map(df)
                with tabs[2]:
                    display_unknown_macid(df)
                with tabs[3]:
                    display_no_data(df)
                with tabs[4]:
                    display_data_unchanged(df)
                with tabs[5]:
                    display_data_dead(df)

            # Pause for 30 seconds before displaying next file
            time.sleep(30)
    else:
        st.write("No CSV files found in folder.")

    # Pause for 3000 seconds before checking for new files
    time.sleep(3000)


if __name__ == "__main__":
    main()

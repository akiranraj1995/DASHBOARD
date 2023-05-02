# REQUIRED LIBRARIES AND PACKAGES
# LIBRARIES FOR Summary Statstics
import time
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io
from pytz import timezone

# LIBRARIES FOR Maps
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import time
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pytz import timezone
import datetime


# MENU OPTION FOR SUMMARY STATISTICS AND MAPS
def main():
    st.set_page_config(page_title="Mac ID App")

    menu = ["Mac ID Summary Statistics", "Mac ID Location Plot"]
    choice = st.sidebar.selectbox("Select Page", menu)

    if choice == "Mac ID Summary Statistics":
        while True:
            show_mac_id_summary_statistics()
            time.sleep(20)
    elif choice == "Mac ID Location Plot":
        while True:
            show_mac_id_location_plot()
            time.sleep(20)


#Time Delay
interval_seconds = 30



# SUMMARY STATISTICS
def show_mac_id_summary_statistics():
    # Set the ID of the source folder in Google Drive
    source_folder_id = '1CU1NdgBVRMosEulzkB-HXUFJJM2Wl6ij'

    # Set the credentials to authenticate the Google Drive API requests using a service account file
    creds = service_account.Credentials.from_service_account_file(
        'fresh-deck-324409-5a5c7482c3d0.json')

    # Create a service object for the Google Drive API
    drive_service = build('drive', 'v3', credentials=creds)

    # Keep track of the IDs of processed files
    processed_file_ids = []

    st.title("DATA DASHBOARD")

    # Create a Streamlit container to display the results
    rows_container = st.empty()
    starttime_container = st.empty()
    endtime_container = st.empty()
    stats_name_container = st.empty()
    stats_container = st.empty()
    total_records = 0

    while True:
        try:
            # Get a list of all CSV files in the source folder in Google Drive
            query = f"'{source_folder_id}' in parents and mimeType= 'text/csv'"
            results = drive_service.files().list(q=query, fields='files(id, name, createdTime)').execute()
            files = results.get('files', [])
            print(f'Found {len(files)} CSV files in source folder:')

            if not files:
                time.sleep(interval_seconds)
                print('No CSV files found in source folder.')

            else:
                # Loop through each CSV file
                for file in files:
                    if file['id'] not in processed_file_ids:
                        print(f'Processing file: {file["name"]}')
                        # Download the CSV file
                        file_id = file['id']
                        request = drive_service.files().get_media(fileId=file_id)
                        file_content = io.BytesIO()
                        downloader = MediaIoBaseDownload(file_content, request)

                        done = False
                        while done is False:
                            status, done = downloader.next_chunk()
                            if status:
                                print(f"Processed {int(status.progress() * 100)}%.")

                        # Convert the downloaded content to a pandas DataFrame
                        df = pd.read_csv(io.BytesIO(file_content.getvalue()))
                        
                        #Total Records
                        total_records += df['Count'].sum()

                        # create a timezone object for IST
                        ist = timezone('Asia/Kolkata')

                        # define a function to convert a timestamp to IST and return a human-readable string
                        def convert_timestamp(timestamp):
                            if timestamp != 0:
                                # convert the timestamp to a pandas datetime object with UTC timezone
                                dt = pd.to_datetime(timestamp, unit='s').tz_localize('UTC')
                                # convert the timezone to IST
                                dt = dt.astimezone(ist)
                                # format the datetime object as a human-readable string
                                return dt.strftime('%d/%b/%Y %H:%M:%S')
                            else:
                                return pd.NaT

                        df['Last Time IST'] = df.groupby('Mac ID', group_keys=False)['Last Time'].apply(
                            lambda x: x.apply(convert_timestamp))

                        start_time = pd.to_datetime(df['Last Time IST']).min().strftime('%d/%b/%Y %H:%M:%S')
                        end_time = pd.to_datetime(df['Last Time IST']).max().strftime('%d/%b/%Y %H:%M:%S')

                        
                        mac_stats = df[
                            ['No', 'Mac ID', 'Location', 'Average Interval', 'Maximum Interval', 'Minimum Interval',
                             'Last Time', 'Active']].reset_index(drop=True)

                        
                        mac_stats.index += 1

                        # Update the processed file IDs
                        processed_file_ids.append(file['id'])

                        # Display the updated results
                        with rows_container:
                            st.subheader(f" 1. Total Records: {int(total_records)}")
                        # Display the updated results
                        with starttime_container:
                            st.subheader(f" 2. Start Time: {start_time} IST")
                        # Display the updated results
                        with endtime_container:
                            st.subheader(f" 3. End Time: {end_time} IST")
                        # Display the updated results
                        with stats_name_container:
                            st.subheader(" 4. Summary Table:")
                        # Display the updated results
                        with stats_container:
                            st.write(mac_stats)
                        # Wait for 30 seconds before processing the next CSV file
                        time.sleep(interval_seconds)

        except HttpError as error:
            print(f'An error occurred: {error}')

        except KeyboardInterrupt:
            print('Execution interrupted by user.')
            break


# MAP LOCATION PLOT
def show_mac_id_location_plot():
    # Set the Google Drive folder ID
    folder_id = "1CU1NdgBVRMosEulzkB-HXUFJJM2Wl6ij"

    # Define a function to authenticate the Google Drive API
    def get_gdrive_service(
            credentials_path="fresh-deck-324409-5a5c7482c3d0.json"):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        service = build("drive", "v3", credentials=credentials)
        return service

    def download_and_process_files(folder_id, credentials_path):
        # Authenticate the Google Drive API
        service = get_gdrive_service(credentials_path)

        # Create a subdirectory to store the CSV files
        if not os.path.exists("csv_files"):
            os.mkdir("csv_files")

        st.header(" 2. LOCATION MAP OF MAC ID")
        # Create a Streamlit container to display the map
        map_container = st.empty()

        # Create a map object centered on India
        india_map = folium.Map(location=[20.5937, 78.9629], zoom_start=2)

        # Keep track of the total records, active records, and inactive records
        total_records = 0
        active_records = 0
        inactive_records = 0

        # Create Streamlit containers to display the counts
        total_records_container = st.empty()
        active_records_container = st.empty()
        inactive_records_container = st.empty()

        # Define Streamlit containers for the start time and end time
        start_time_container = st.empty()
        end_time_container = st.empty()
        active_locations_container = st.empty()

        # Start the loop to download and process the files
        processed_files = set()
        # Start the loop to download and process the files
        while True:
            # Download the files from Google Drive
            file_list = service.files().list(q=f"'{folder_id}' in parents", fields="files(id, name)").execute().get(
                "files",
                [])

            for file in file_list:
                if file["id"] not in processed_files:
                    file_id = file["id"]
                    file_name = os.path.join("csv_files", file_id + ".csv")
                    request = service.files().get_media(fileId=file_id)
                    with open(file_name, "wb") as f:
                        f.write(request.execute())

                    # Process the CSV files as streaming data
                    data = pd.read_csv(file_name)

                    # Create a marker cluster for this chunk
                    marker_cluster = MarkerCluster().add_to(india_map)

                    # Define a timezone object for IST
                    ist = timezone('Asia/Kolkata')

                    count = 0
                    active_count = 0
                    inactive_count = 0

                    active_locations = set()
                    for index, row in data.iterrows():
                        if row["Active"] == 1:
                            active_locations.add(row["Location"])
                            color = "green"
                            count += 1
                            active_count += 1
                        else:
                            color = "orange"
                            count += 1
                            inactive_count += 1
                        active_locations_names = ', '.join(active_locations).replace("{", "").replace("}", "").replace(
                            "'",
                            "")

                        folium.Marker(location=[row["Latitude"], row["Longitude"]],
                                      tooltip=row["Mac ID"], icon=folium.Icon(color=color)).add_to(marker_cluster)

                    # Update the Active and Inactive counts
                    active_records = len(data[data["Active"] == 1])
                    inactive_records = len(data[data["Active"] == 0])

                    # create a timezone object for IST
                    ist = timezone('Asia/Kolkata')

                    # define a function to convert a timestamp to IST and return a human-readable string
                    def convert_timestamp(timestamp):
                        if timestamp != 0:
                            # convert the timestamp to a pandas datetime object with UTC timezone
                            dt = pd.to_datetime(timestamp, unit='s').tz_localize('UTC')
                            # convert the timezone to IST
                            dt = dt.astimezone(ist)
                            # format the datetime object as a human-readable string
                            return dt.strftime('%d/%b/%Y %H:%M:%S')
                        else:
                            return pd.NaT

                    data['Last Time IST'] = data.groupby('Mac ID', group_keys=False)['Last Time'].apply(
                        lambda x: x.apply(convert_timestamp))

                    start_time = pd.to_datetime(data['Last Time IST']).min().strftime('%d/%b/%Y %H:%M:%S')
                    end_time = pd.to_datetime(data['Last Time IST']).max().strftime('%d/%b/%Y %H:%M:%S')

                    # Display the chunk on the map container
                    map_container.empty()
                    with map_container:
                        folium_static(india_map, width=800, height=600)
                        # calcuate the total records count
                        total_records += data["Count"].sum()
                        # Display the updated counts
                        total_records = int(total_records)
                        active_count = int(active_count)
                        inactive_count = int(inactive_count)

                    total_records_container.subheader(" 1. Total Records: {}".format(total_records))
                    active_records_container.subheader(" 2. Active Mac ID Count: {}".format(active_records))
                    # inactive_records_container.subheader(" 3. Inactive Mac ID Count: {}".format(inactive_records))
                    start_time_container.subheader(" 3. Start Time: {}".format(start_time))
                    end_time_container.subheader(" 4. End Time: {}".format(end_time))
                    active_locations_container.subheader(" 5. Active Location Name : {}".format(active_locations_names))

                    # Add the file ID to the set of processed files
                    processed_files.add(file["id"])
                    # Wait for some time before checking for new files
                    time.sleep(interval_seconds)

    # Authenticate the Google Drive API
    service = get_gdrive_service()

    # Download and process the files
    download_and_process_files("1CU1NdgBVRMosEulzkB-HXUFJJM2Wl6ij","fresh-deck-324409-5a5c7482c3d0.json")

if __name__ == "__main__":
    main()


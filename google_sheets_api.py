import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials


scope = ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name('ikigai-db-credentials.json', scope)
client = gspread.authorize(credentials)

# reservations_table = client.create('reservations')
# reservations_table.share('openzzggl@gmail.com', perm_type='user', role='writer')
reservations_table = client.open('reservations').sheet1



def read_table_to_df():
    global reservations_table
    reservations_table = client.open('reservations').sheet1

    data = reservations_table.get_all_values()
    headers = data.pop(0)

    df = pd.DataFrame(data=data, columns=headers)

    return df


def save_df_to_table(df):
    global reservations_table
    reservations_table.clear()
    df = df.fillna('')
    df = df.astype(str)
    columns = df.columns.values.tolist()
    data = df.values.tolist()

    reservations_table.update([columns] + data)
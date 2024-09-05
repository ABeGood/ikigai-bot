import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials


scope = ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/calendar',]

# credentials = ServiceAccountCredentials.from_json_keyfile_name(, scope)
credentials = ServiceAccountCredentials.from_json_keyfile_name('keys/table.json', scopes=scope)
client = gspread.authorize(credentials)

# reservations_table = client.create('ikigai_reservations')
# reservations_table.share('openzzggl@gmail.com', perm_type='user', role='writer')
reservations_table = client.open('ikigai_reservations').sheet1



def read_table_to_df():
    global reservations_table
    reservations_table = client.open('ikigai_reservations').sheet1

    columns_to_read = ['CreationTime', 'OrderId', 'TelegramId', 'Name', 'Type', 'Place', 'Day', 'From', 'To', 'Period', 'Payed']

    data = reservations_table.get_all_records(expected_headers=columns_to_read)

    df = pd.DataFrame(data=data, columns=columns_to_read)

    return df


def save_df_to_table(df):
    global reservations_table

    # reservations_table.append_rows(values=, table_range='A:K')
    # reservations_table.delete_columns(0, 10)

    reservations_table.clear()
    df = df.fillna('')
    df = df.astype(str)
    columns = df.columns.values.tolist()
    data = df.values.tolist()

    reservations_table.update([columns] + data)
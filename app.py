import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

filename = "cred.json"

scopes = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    filename=filename,
    scopes=scopes,
)

client = gspread.authorize(creds)
print("Cliente conectado:", client)

planilha_completa = client.open(
    title="Multiplication_Report",
    folder_id="1Lk_vg5-QgDVL7ScSqLQxpHxS1VCLM5Er",
)

planilha = planilha_completa.get_worksheet(0)
dados = planilha.get_all_records()

df = pd.DataFrame(dados)
print("\n=== DataFrame ===")
print(df)
print(f"\nLinhas: {df.shape[0]} | Colunas: {df.shape[1]}")
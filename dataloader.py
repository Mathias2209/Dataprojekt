# %%
import pandas as pd
import requests
import io
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

api_url = "https://api.github.com/repos/Mathias2209/Dataprojekt/contents/folder-Data/folder-2023%20AAR%20vaskeri%20data"

response = requests.get(api_url, verify=False)
filer = response.json()

xlsx_filer = [f for f in filer if f["name"].startswith("PLC") and f["name"].endswith(".xlsx")]

dataframes = []
for fil in xlsx_filer:
    r = requests.get(fil["download_url"], verify=False)
    df = pd.read_excel(io.BytesIO(r.content), skiprows=2)
    
    # Extract month from filename (e.g. "PLC_Januar_2023.xlsx" -> "Januar")
    match = re.search(r'(januar|februar|marts|april|maj|juni|juli|august|september|oktober|november|december)', 
                      fil["name"], re.IGNORECASE)
    df["Måned"] = match.group(1).capitalize() if match else fil["name"]

    dataframes.append(df)

samlet_df = pd.concat(dataframes, ignore_index=True)

n_unique_prod_year = (
    samlet_df
    .dropna(subset=["Unik Kode (ui)"])
    .groupby("Unik Kode (ui)")["Produkt - Produkt"]
    .nunique()
)
bad_ui_year = n_unique_prod_year[n_unique_prod_year > 1].index

conflicts_year = (
    samlet_df[samlet_df["Unik Kode (ui)"].isin(bad_ui_year)]
    .loc[:, ["Unik Kode (ui)", "Produkt - Produkt"]]
    .drop_duplicates()
    .sort_values(["Unik Kode (ui)", "Produkt - Produkt"])
)

samlet_df = samlet_df[~samlet_df["Unik Kode (ui)"].isin(bad_ui_year)].copy()

# Filter all cases where Stk. tøj per kassationsdato is larger than 1
samlet_df = samlet_df[samlet_df["Stk. tøj per kassationsdato"] == 1]

# Filter all cases where antal vaske is 0 or lager
samlet_df = samlet_df[samlet_df["Total antal vask"] >= 0]


def kategoriser_produkt(produktnavn):
    produktnavn = str(produktnavn).lower()
    
    # Tjek i prioriteret rækkefølge (mest specifik først)
    if any(ord in produktnavn for ord in ['forklæde', 'forkl']):
        return 'Forklæde'
    elif 'kokkej' in produktnavn:
        return 'Kokkejakke'
    elif any(ord in produktnavn for ord in ['shorts', 'knickers']):
        return 'Shorts'
    elif any(ord in produktnavn for ord in ['jakke', 'vest', 'jak', 'jk', 'softshell', 'soft shell']):
        return 'Jakke'
    elif 'fleece' in produktnavn:
        return 'Fleece'
    elif any(ord in produktnavn for ord in ['sweat', 'ziptrøje', 'tunika', 'bluse', 'cardigan']):
        return 'Langærmet'
    elif any(ord in produktnavn for ord in ['t-shirt', 'polo', 'tshirt']):
        return 'T-shirt'
    elif 'kittel' in produktnavn or re.search(r'\bkit[\s\.]', produktnavn):
        return 'Kittel'
    elif any(ord in produktnavn for ord in ['skjorte', 'skj.']):
        return 'Skjorte'
    elif any(ord in produktnavn for ord in ['buks', 'benk', 'benklæder', 'unisexben', 'jeans', 'pull on uni']):
        return 'Bukser'
    elif 'overall' in produktnavn or 'kedeldr' in produktnavn or 'heldragt' in produktnavn:
        return 'Overall'
    elif any(ord in produktnavn for ord in ['kokkebuss', 'busseron', 'halvbusseron']):
        return 'Busseron'
    elif any(ord in produktnavn for ord in ['strømpe', 'sok']):
        return 'Strømper'
    else:
        return 'Andet'

# Tilføj kategori
samlet_df['Kategori'] = samlet_df['Produkt - Produkt'].apply(kategoriser_produkt)

# Nu kan du filtrere uden overlap
skjorte_data = samlet_df[samlet_df['Kategori'] == 'Skjorte']
shorts_data = samlet_df[samlet_df['Kategori'] == 'Shorts']
bukse_data = samlet_df[samlet_df['Kategori'] == 'Bukser']
tshirt_data = samlet_df[samlet_df['Kategori'] == 'T-shirt']
langærmet_data = samlet_df[samlet_df['Kategori'] == 'Langærmet']
jakke_data = samlet_df[samlet_df['Kategori'] == 'Jakke']
fleece_data = samlet_df[samlet_df['Kategori'] == 'Fleece']
overall_data = samlet_df[samlet_df['Kategori'] == 'Overall']
forklæde_data = samlet_df[samlet_df['Kategori'] == 'Forklæde']
kittel_data = samlet_df[samlet_df['Kategori'] == 'Kittel']
busseron_data = samlet_df[samlet_df['Kategori'] == 'Busseron']
kokkejakke_data = samlet_df[samlet_df['Kategori'] == 'Kokkejakke']
sokke_data = samlet_df[samlet_df['Kategori'] == 'Strømper']
andre_data = samlet_df[samlet_df['Kategori'] == 'Andet']

# Tjek resultater
print(samlet_df['Kategori'].value_counts())
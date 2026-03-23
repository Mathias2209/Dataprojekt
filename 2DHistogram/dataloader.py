import pandas as pd
import requests
import io
import urllib3
import re

# Remove warings when downloading files from GitHub
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Download files from GitHub API
api_url = "https://api.github.com/repos/Mathias2209/Dataprojekt/contents/folder-Data/folder-2023%20AAR%20vaskeri%20data"
response = requests.get(api_url, verify=False)
filer = response.json()

# Filter for Excel files that start with "PLC"
xlsx_filer = [f for f in filer if f["name"].startswith("PLC") and f["name"].endswith(".xlsx")]


# Load each Excel file into a DataFrame and concatenate them
dataframes = []
for fil in xlsx_filer:
    r = requests.get(fil["download_url"], verify=False)
    df = pd.read_excel(io.BytesIO(r.content), skiprows=2)
    
    # Extract month from filename (e.g. "PLC_Januar_2023.xlsx" -> "Januar")
    match = re.search(r'(januar|februar|marts|april|maj|juni|juli|august|september|oktober|november|december)', 
                      fil["name"], re.IGNORECASE)
    df["Måned"] = match.group(1).capitalize() if match else fil["name"]

    dataframes.append(df)

# Concatenate all DataFrames into one
samlet_df = pd.concat(dataframes, ignore_index=True)

# Remove duplicates based on "Unik Kode (ui)" and "Produkt - Produkt"
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

# Remove all cases where the same "Unik Kode (ui)" is associated with more than one "Produkt - Produkt"
samlet_df = samlet_df[~samlet_df["Unik Kode (ui)"].isin(bad_ui_year)].copy()

# Filter all cases where Stk. tøj per kassationsdato is larger than 1
samlet_df = samlet_df[samlet_df["Stk. tøj per kassationsdato"] == 1]

# Filter all cases where antal vaske is 0 or lager
samlet_df = samlet_df[samlet_df["Total antal vask"] >= 0]

# Filter all cases where Dage i cirkulation is 1 or lager
samlet_df = samlet_df[samlet_df["Dage i cirkulation"] >= 1]

# Add ratio column: washes per month in circulation
samlet_df['Vask per måned'] = (samlet_df['Total antal vask'] / samlet_df['Dage i cirkulation']) * 30.44

def kategoriser_produkt(produktnavn):
    produktnavn = str(produktnavn).lower()

    if any(ord in produktnavn for ord in ['forklæde', 'forkl']):
        return 'Forklæde'
    elif 'kokkej' in produktnavn:
        return 'Kokkejakke'
    elif any(ord in produktnavn for ord in ['knickers']):
        return 'knickers'
    elif any(ord in produktnavn for ord in ['nederdel']):
        return 'nederdel'
    elif any(ord in produktnavn for ord in ['shorts']):
        return 'Shorts'
    elif any(ord in produktnavn for ord in ['softshell', 'soft shell.']):
        return 'softshell'
    elif any(ord in produktnavn for ord in ['jakke', 'vest', 'jak', 'jk']):
        return 'Jakke'
    elif 'fleece' in produktnavn:
        return 'Fleece'
    elif any(ord in produktnavn for ord in ['ziptrøje']):
        return 'ziptrøje'
    elif any(ord in produktnavn for ord in ['tunika']):
        return 'tunika'
    elif any(ord in produktnavn for ord in ['bluse']):
        return 'bluse'
    elif any(ord in produktnavn for ord in ['cardigan']):
        return 'cardigan'
    elif any(ord in produktnavn for ord in ['sjælevarm']):
        return 'sjælevarm'
    elif any(ord in produktnavn for ord in ['fusion shirt']):
        return 'fusion shirt'
    elif any(ord in produktnavn for ord in ['sweat']):
        return 'Langærmet'
    elif any(ord in produktnavn for ord in ['polo']):
        return 'Polo'
    elif any(ord in produktnavn for ord in ['undertrøje']):
        return 'undertrøje'
    elif any(ord in produktnavn for ord in ['t-shirt', 'tshirt']):
        return 'T-shirt'
    elif 'kittel' in produktnavn or re.search(r'\bkit[\s\.]', produktnavn):
        return 'Kittel'
    elif any(ord in produktnavn for ord in ['skjorte', 'skj.', 'kokkesk.']):
        return 'Skjorte'
    elif any(ord in produktnavn for ord in ['jeans']):
        return 'jeans'
    elif any(ord in produktnavn for ord in ['buks', 'benk', 'benklæder', 'unisexben', 'pull on uni']):
        return 'Bukser'
    elif 'overall' in produktnavn or 'kedeldr' in produktnavn or 'heldragt' in produktnavn:
        return 'Overall'
    elif any(ord in produktnavn for ord in ['kokkebuss', 'busseron', 'halvbusseron']):
        return 'Busseron'
    else:
        return 'Andet'

samlet_df['Kategori'] = samlet_df['Produkt - Produkt'].apply(kategoriser_produkt)

skjorte_data    = samlet_df[samlet_df['Kategori'] == 'Skjorte']
shorts_data     = samlet_df[samlet_df['Kategori'] == 'Shorts']
knickers_data   = samlet_df[samlet_df['Kategori'] == 'knickers']
nederdel_data   = samlet_df[samlet_df['Kategori'] == 'nederdel']
shorts_data     = pd.concat([shorts_data, knickers_data, nederdel_data], ignore_index=True)
bukse_data      = samlet_df[samlet_df['Kategori'] == 'Bukser']
jeans_data      = samlet_df[samlet_df['Kategori'] == 'jeans']
bukse_data      = pd.concat([bukse_data, jeans_data], ignore_index=True)
polo_data       = samlet_df[samlet_df['Kategori'] == 'Polo']
tshirt_data     = samlet_df[samlet_df['Kategori'] == 'T-shirt']
undertrøje_data = samlet_df[samlet_df['Kategori'] == 'undertrøje']
tshirt_data     = pd.concat([polo_data, tshirt_data, undertrøje_data], ignore_index=True)
langærmet_data  = samlet_df[samlet_df['Kategori'] == 'Langærmet']
ziptrøje_data   = samlet_df[samlet_df['Kategori'] == 'ziptrøje']
tunika_data     = samlet_df[samlet_df['Kategori'] == 'tunika']
bluse_data      = samlet_df[samlet_df['Kategori'] == 'bluse']
cardigan_data   = samlet_df[samlet_df['Kategori'] == 'cardigan']
sjælevarm_data  = samlet_df[samlet_df['Kategori'] == 'sjælevarm']
fusion_data     = samlet_df[samlet_df['Kategori'] == 'fusion shirt']
langærmet_data  = pd.concat([langærmet_data, ziptrøje_data, tunika_data, bluse_data, cardigan_data, sjælevarm_data, fusion_data], ignore_index=True)
jakke_data      = samlet_df[samlet_df['Kategori'] == 'Jakke']
softshell_data  = samlet_df[samlet_df['Kategori'] == 'softshell']
jakke_data      = pd.concat([jakke_data, softshell_data], ignore_index=True)
fleece_data     = samlet_df[samlet_df['Kategori'] == 'Fleece']
overall_data    = samlet_df[samlet_df['Kategori'] == 'Overall']
forklæde_data   = samlet_df[samlet_df['Kategori'] == 'Forklæde']
kittel_data     = samlet_df[samlet_df['Kategori'] == 'Kittel']
busseron_data   = samlet_df[samlet_df['Kategori'] == 'Busseron']
kokkejakke_data = samlet_df[samlet_df['Kategori'] == 'Kokkejakke']
andre_data      = samlet_df[samlet_df['Kategori'] == 'Andet']

# Tjek resultater
print(samlet_df['Kategori'].value_counts())
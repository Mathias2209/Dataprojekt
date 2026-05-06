import sys
sys.path.append("2DHistogram")
import matplotlib.pyplot as plt
import numpy as np

from dataloader import skjorte_data, shorts_data, bukse_data, tshirt_data, langærmet_data, jakke_data, fleece_data, overall_data, forklæde_data, kittel_data, busseron_data, kokkejakke_data, andre_data

def top3_sammenligning(df, navn = "", antal_år = 8):
    prodnavne = df["Produkt - Produkt"].value_counts()[:3].index

    fig, ax = plt.subplots()
    min_dage = df["Dage i cirkulation"].min()
    max_dage = 365.25 * antal_år
    hist_bins = np.linspace(min_dage, max_dage)
    for prodnavn in prodnavne:
        dataframe = df[df["Produkt - Produkt"] == prodnavn]
        DiC = dataframe["Dage i cirkulation"]
        count, bin_edges = np.histogram(DiC, hist_bins)
        bin_centers = (hist_bins[:-1] + hist_bins[1:]) / 2
        ax.plot(bin_centers / 365.25, count, label = f"{prodnavn}")
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.set_title(f"Sammenligning af top 3 produkter i {navn}")
    ax.set_xlabel("Levetid")
    ax.set_xticks(range(0,9))
    ax.set_ylabel("Antal kasseret")
    plt.show()

datasæt = {
    "Skjorte": skjorte_data,
    "Shorts": shorts_data,
    "Bukser": bukse_data,
    "T-shirt": tshirt_data,
    "Langærmet": langærmet_data,
    "Jakke": jakke_data,
    "Fleece": fleece_data,
    "Overall": overall_data,
    "Forklæde": forklæde_data,
    "Kittel": kittel_data,
    "Busseron": busseron_data,
    "Kokkejakker": kokkejakke_data,
    "Andet": andre_data
}

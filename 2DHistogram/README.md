# 2D Histogram - Kassationsanalyse

## Formål

Formålet med programmet er interaktivt at lave 2D histogrammer som kan benyttes til visualisering og analyse af datasættet.

---

## Opsætning

For at programmet virker skal følgende pakker være installeret. Kør denne kommando i terminalen:

```
pip install PyQt5 matplotlib numpy pandas scipy pyarrow openpyxl
```

Første gang programmet køres vil det tage lidt længere tid at åbne, da data indlæses og gemmes som cache. Fremover åbner programmet hurtigere. Hvis et nyt datasæt skal indlæses kan dette gøres i programmet øverst til højre på knappen **"🔄 Opdater data"**.

Start programmet ved at køre:

```
python histogram_app.py
```

---

## Brug

### Topbar
Øverst i vinduet er der tre knapper:
- **1 Graf** – vis én graf ad gangen med faneblade for Graf A og Graf B
- **2 Grafer** – vis begge grafer side om side
- **🔄 Opdater data** – genindlæs data fra dataloader og genstart programmet

### Kontrolpanelerne
Hvert panel har to kolonner:

**Venstre kolonne – Indstillinger**
- Vælg datasæt og kassationsårsag
- Vælg graftype: *Begge*, *2D Histogram* eller *Overdødelighed*
- Juster bins og glatning
- Slå logaritmisk farveskala og regressionsmodel til/fra
- Gem og indlæs grafer

**Højre kolonne – Filtrering**
- Vælg x-akse skala: *Dage*, *Måneder* eller *År*
- Filtrer på dage i cirkulation, antal vaske og vask per måned
- Slå referencelinjer og kvantillinjer til/fra
- Indstil synkronisering mellem Graf A og Graf B

### Graftyper

**2D Histogram** viser forholdet mellem dage i cirkulation og antal vaske. Farven angiver, hvor mange produkter der befinder sig i hvert område. Kvantillinjerne viser 25%-, median- og 75%-percentilen.

**Overdødelighed** viser kassationsprofilen over tid – altså hvornår i produktets levetid de fleste kasseres. Kurven sammenlignes med en forventet baseline, og afvigelser markeres med z-score-tærskler.

### Gem og eksporter
- **💾 Gem** – gemmer et billede af grafen samt alle indstillinger, så grafen kan genskabes præcist
- **📄 CSV** – eksporterer det filtrerede datasæt som en CSV-fil

Gemte grafer placeres i mappen `Saved Histograms/` i samme mappe som programmet.

### Synkronisering (kun i 2-grafer tilstand)
I filtreringspanelet for Graf A er der en synkroniseringsgruppe. Her kan du vælge hvilke indstillinger der automatisk kopieres fra den ene graf til den anden. Klik **"Alle"** for at synkronisere alt på én gang.

---

## Filsystem

Alle filer skal ligge i samme mappe for at programmet virker:

| Fil | Beskrivelse |
|-----|-------------|
| `histogram_app.py` | Startpunkt – kør denne fil for at åbne programmet |
| `config.py` | Farver og konstanter |
| `data_cache.py` | Indlæsning og caching af data |
| `widgets.py` | Fælles UI-komponenter |
| `loading_screen.py` | Splash-screen ved opstart |
| `plot_canvas.py` | Al tegnelogik for histogram og overdødelighed |
| `plot_widget.py` | Wrapper rundt om canvas |
| `control_panel.py` | Alle indstillinger og filtre |
| `panels.py` | Layout og synkroniseringslogik |
| `dataloader.py` | Indlæsning af data |

Data caches i filen `data_cache.pkl` – slet den manuelt eller brug **"🔄 Opdater data"** for at genopbygge den.
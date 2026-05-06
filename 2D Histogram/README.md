# 2D Histogram

## Formål

Programmet bruges til interaktivt at visualisere og analysere kassationsdata via 2D histogrammer og kassationsprofiler (overdødelighed).

---

## Opsætning

For at programmet virker skal følgende pakker være installeret. Kør denne kommando i terminalen:

```
pip install PyQt5 matplotlib numpy pandas scipy pyarrow openpyxl pymc
```

Start programmet ved at køre:

```
python histogram_app.py
```

### Første opstart

Første gang programmet køres tager det markant længere tid at åbne. Det skyldes to ting:

1. **Data indlæses** fra `dataloader.py` og gemmes som cache (`data_cache.pkl`), så det går hurtigere næste gang
2. **Weibull-modeller fittes** via Bayesiansk MCMC (PyMC) for hvert datasæt og hver kassationsårsag. Disse gemmes i mappen `cache/weibull/`. Afhængigt af antal kombinationer kan dette tage op til en time

Fremover åbner programmet hurtigt, da alt er cachet. En loading-screen med progressbar viser hvor langt opsætningen er nået.

Hvis data opdateres kan cachen nulstilles med knappen **"🔄 Opdater data"** øverst til højre. Dette sletter både data-cachen og alle Weibull-modeller, og programmet genstarter.

---

## Brug

### Topbar
Øverst i vinduet er der tre knapper:
- **1 Graf** – vis én graf ad gangen med faneblade for Graf A og Graf B
- **2 Grafer** – vis begge grafer side om side
- **🔄 Opdater data** – slet cache, genindlæs data og genstart programmet

### Kontrolpanelerne
Hvert panel har to kolonner:

**Venstre kolonne – Indstillinger**
- Vælg datasæt og kassationsårsag
- Vælg graftype: *Begge*, *2D Histogram* eller *Overdødelighed*
- Juster antal bins
- **Farveskala:**
  - Slå logaritmisk farveskala til/fra (2D Histogram)
  - Slå log y-akse til/fra (Overdødelighed)
  - Slå regressionsmodel til/fra
  - Juster farve minimum og min. alpha (skjul sparse celler)
- Tilføj en valgfri note og mappenavn til gemte grafer
- Gem og indlæs tidligere gemte grafer

**Højre kolonne – Filtrering**
- Vælg x-akse skala: *Dage*, *Måneder* eller *År* (standard: År)
- Filtrer på **Levetid**, **Antal Vaske** og **Vaske Pr. Måned**
- **VPM-linjer** – slå referencelinjerne for vaske per måned til/fra
- **Kvantillinjer** – slå 25%-, median- og 75%-linjer til/fra
- **Overdødelighed** – slå individuelle elementer til/fra:
  - *4σ-tærskel*
  - *2σ-tærskel*
  - *Overlevelseskurve*
  - *Vis forklaring* (legende)
- Indstil synkronisering mellem Graf A og Graf B

### Graftyper

**2D Histogram** viser forholdet mellem levetid og antal vaske. Farven angiver hvor mange produkter der befinder sig i hvert område. Kvantillinjer og regressionsmodel kan slås til/fra.

**Overdødelighed** viser kassationsprofilen over tid – altså hvornår i produktets levetid de fleste kasseres. Baseline beregnes med en Bayesiansk Weibull-model (MCMC) fittet på det fulde datasæt for det valgte datasæt og den valgte kassationsårsag. Grafen viser:

- **Weibull-baseline** – den forventede kassationsrate baseret på MCMC-modellen
- **95% kredibelt interval** – usikkerhedsbånd omkring baseline fra posterior-fordelingen
- **2σ og 4σ tærskler** – Poisson-baserede grænser for statistisk usædvanlig kassationsrate
- **Registreret** – den faktiske observerede kassationsrate
- **Gul fyldning** – perioder hvor observeret rate overstiger 2σ-tærsklen
- **Overlevelseskurve** – andelen af produkter stadig i cirkulation (højre akse)

**Begge** viser 2D Histogram og Overdødelighed stablet i samme vindue.

### Gem og eksporter
- **💾 Gem** – gemmer et billede af grafen samt alle indstillinger, så grafen kan genskabes præcist
- **📄 CSV** – eksporterer det filtrerede datasæt som en CSV-fil

Gemte grafer placeres i mappen `Saved Histograms/` i samme mappe som programmet.

### Synkronisering (kun i 2-grafer tilstand)
I filtreringspanelet er der en synkroniseringsgruppe. Her kan du vælge hvilke indstillinger der automatisk kopieres fra den ene graf til den anden, herunder datasæt, kassationsårsag, x-akse skala, filtre, graftype og farveskala. Klik **"Alle"** for at synkronisere alt på én gang.

---

## Filsystem

Alle filer skal ligge i samme mappe for at programmet virker:

| Fil | Beskrivelse |
|-----|-------------|
| `histogram_app.py` | Startpunkt – kør denne fil for at åbne programmet |
| `config.py` | Farver, konstanter og skala-konfiguration |
| `data_cache.py` | Indlæsning og caching af data fra dataloader |
| `weibull_cache.py` | Bayesiansk Weibull-fitting og caching af MCMC-modeller |
| `widgets.py` | Fælles UI-komponenter (sliders, knapper, labels) |
| `loading_screen.py` | Splash-screen med progressbar ved opstart |
| `plot_canvas.py` | Al tegnelogik for 2D histogram og overdødelighed |
| `plot_widget.py` | Wrapper rundt om canvas med graf-header |
| `control_panel.py` | Alle indstillinger og filtre |
| `panels.py` | Layout og synkroniseringslogik |

### Cache-filer (genereres automatisk)

| Sti | Indhold |
|-----|---------|
| `data_cache.pkl` | Data indlæst fra dataloader |
| `cache/weibull/<navn>.pkl` | MCMC posterior-samples for hvert datasæt × kassationsårsag |

Slet cachen manuelt eller brug **"🔄 Opdater data"** for at genopbygge alt fra bunden.

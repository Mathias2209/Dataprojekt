# 2D Histogram

## Formål

Programmet bruges til interaktivt at visualisere og analysere kassationsdata via 2D histogrammer og kassationsprofiler (overdødelighed).

---

## AI dekeleration

Udviklingen af dette program er gennemført i samarbejde med kunstig intelligens. Samarbejdet er baseret på vores koncepter, som AI'en efterfølgende har implementeret i værktøjet.

## Opsætning

For at programmet virker skal følgende pakker være installeret. Kør denne kommando i terminalen:

```
pip install PyQt5 matplotlib numpy pandas scipy pyarrow openpyxl pymc requests urllib3
```

Start programmet ved at køre:

```
python histogram_app.py
```

### Første opstart

Programmet kommer med cache filer som er genereret, men som udgangspunkt følger programmet denne proces:

Første gang programmet køres tager det markant længere tid at åbne. Det skyldes to ting:

1. **Data indlæses** fra `dataloader.py` og gemmes som cache (`data_cache.pkl`), så det går hurtigere næste gang
2. **Weibull-modeller fittes** via Bayesiansk MCMC (PyMC) for hvert datasæt og hver kassationsårsag. Disse gemmes i mappen `Settings/cache/weibull/`.

Fremover åbner programmet hurtigt, da alt er cachet. En loading-screen med progressbar viser hvor langt opsætningen er nået.

Hvis data ikke kan hentes fra netværket starter programmet automatisk i **demo-tilstand** med et simpelt datasæt, så brugerfladen stadig kan anvendes.

Hvis data opdateres kan cachen nulstilles med knappen **"Opdater data"** øverst til højre. Dette sletter både data-cachen og alle Weibull-modeller, og programmet genstarter.

Hvis cachen skal genskabes på en Windows-computer, anbefales det kraftigt at benytte pakken

```
g++
```

Da det vil tage meget lang tid at køre programmet uden.

---

## Anvendelse

### Hovedpanel
Øverst i vinduet er der fire knapper:
- **1 Graf** – vis én graf ad gangen med faneblade for Graf A og Graf B
- **2 Grafer** – vis begge grafer side om side
- **Fuldskærm** – skjul kontrolpaneler og vis kun grafen. Tryk Escape for at vende tilbage
- **Opdater data** – slet cache, genindlæs data og genstart programmet

### Kontrolpanelerne
Hvert panel har to kolonner:

**Venstre kolonne – Indstillinger**
- Indlæs eller slet tidligere gemte grafer (🔄 opdaterer listen, 🗑 sletter valgt graf)
- Vælg datasæt og kassationsårsag
- **Søg produkt** – filtrer data på produktnavn. Slå *Hele ord* til for at matche hele ord
- Vælg graftype: *Begge*, *2D Histogram* eller *Overdødelighed*
- Juster antal bins
- **Farveskala:**
  - Slå logaritmisk farveskala til/fra (2D Histogram)
  - Slå regressionsmodel til/fra
- Tilføj en valgfri note og mappenavn til gemte grafer
- Gem grafen med knappen **Gem**

**Højre kolonne – Filtrering**
- Vælg x-akse skala: *Måneder* eller *År* (standard: År)
- Filtrer på **Levetid**, **Antal Vaske** og **Vaske Pr. Måned**
- **VPM-linjer** – slå referencelinjerne for vaske per måned til/fra
- **Kvantillinjer** – slå 25%-, median- og 75%-linjer til/fra
- **Overdødelighed** – slå individuelle elementer til/fra:
  - *4σ-grænse*
  - *2σ-grænse*
  - *Overlevelseskurve*
  - *Vis forklaring* 
- Indstil synkronisering mellem Graf A og Graf B

### Graftyper

**2D Histogram** viser forholdet mellem levetid og antal vaske. Farven angiver hvor mange produkter der befinder sig i hvert område. Kvantillinjer og regressionsmodel kan slås til/fra.

**Overdødelighed** viser kassationsprofilen over tid – altså hvornår i produktets levetid de fleste kasseres. Baseline beregnes med en Bayesiansk Weibull-model (MCMC) fittet på det fulde datasæt for det valgte datasæt og den valgte kassationsårsag. Grafen viser:

- **Weibull-baseline** – den forventede kassationsrate baseret på MCMC-modellen
- **95% kredibelt interval** – usikkerhedsbånd omkring baseline fra posterior-fordelingen
- **2σ og 4σ tærskler** – Poisson-baserede grænser for statistisk usædvanlig kassationsrate
- **Registreret** – den faktiske observerede kassationsrate
- **Gul udfyldning** – perioder hvor observeret rate overstiger 2σ-tærsklen
- **Overlevelseskurve** – andelen af produkter stadig i cirkulation (højre akse)

**Begge** viser 2D Histogram og Overdødelighed stablet i samme vindue.

### Gem og eksporter
- **Gem** – gemmer et billede af grafen samt alle indstillinger, så grafen kan genskabes præcist, derudover eksporteres det filtrerede datasæt som en CSV-fil

### Synkronisering (kun i 2-grafer tilstanden)
I filtreringspanelet er der en synkroniseringsgruppe. Her kan du vælge hvilke indstillinger der automatisk kopieres fra den ene graf til den anden, herunder datasæt, kassationsårsag, x-akse skala, filtre, graftype og farveskala. Klik **"Alle"** for at synkronisere alt på én gang.

---

## Filsystem

```
2D Histogram/
├── histogram_app.py        ← startpunkt, kør denne fil
└── Settings/               ← alle moduler ligger her
    ├── config.py           ← farver, konstanter og skala-konfiguration
    ├── data_cache.py       ← indlæsning og caching af data fra dataloader
    ├── dataloader.py       ← henter rådata fra GitHub
    ├── weibull_cache.py    ← Bayesiansk Weibull-fitting og caching af MCMC-modeller
    ├── chi.py              ← chi-squared goodness-of-fit mod Weibull-modellen
    ├── widgets.py          ← fælles UI-komponenter (sliders, knapper, labels)
    ├── loading_screen.py   ← splash-screen med progressbar ved opstart
    ├── plot_canvas.py      ← al tegnelogik for 2D histogram og overdødelighed
    ├── plot_widget.py      ← wrapper rundt om canvas med graf-header
    ├── control_panel.py    ← alle indstillinger og filtre
    └── panels.py           ← layout og synkroniseringslogik
```

### Cache-filer (genereres automatisk)

| Sti | Indhold |
|-----|---------|
| `Settings/data_cache.pkl` | Data indlæst fra dataloader |
| `Settings/cache/weibull/<navn>.pkl` | MCMC posterior-samples for hvert datasæt × kassationsårsag |

Slet cachen manuelt eller brug **"Opdater data"** for at genopbygge alt fra bunden.

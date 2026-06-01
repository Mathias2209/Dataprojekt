# 2D Histogram

## Formål

Programmet har til formål at visualisere datasættet 'PLC, product detaljeret, Aarhus', samt at give bedre muligheder for at finde data udsnit til yderligere analyse.

---

## AI dekeleration

Udviklingen af dette program er gennemført i samarbejde med kunstig intelligens. Programmet er baseret på vores koncepter, som AI'en efterfølgende har implementeret i værktøjet.

## Opsætning

For at programmet virker skal følgende pakker være installeret.

```
PyQt5 matplotlib numpy pandas scipy pyarrow openpyxl pymc requests urllib3
```

Programmet startes ved at køre:

```
histogram_app.py
```

### Første opstart

Programmet kommer med cache filer som er genereret, men som udgangspunkt følger programmet denne proces:

1. **Data indlæses** fra `dataloader.py` og gemmes som cache (`data_cache.pkl`), så det går hurtigere næste gang
2. **Weibull-modeller fittes** via Bayesiansk MCMC (PyMC) for hvert datasæt og hver kassationsårsag. Disse gemmes i mappen `Settings/cache/weibull/`.

Fremover åbner programmet hurtigt, da alt er cachet.

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


### Gem og eksporter
- **Gem** – gemmer et billede af grafen samt alle indstillinger, så grafen kan genskabes præcist, derudover eksporteres det filtrerede datasæt som en CSV-fil

### Synkronisering
I filtreringspanelet er der en synkroniseringsgruppe. Her vælges hvilke indstillinger der kopieres fra den ene graf til den anden.

---

## Filsystem

```
2D Histogram/
├── histogram_app.py        ← Hovedprogram
└── Settings/               ← Alle moduler ligger her
    ├── config.py           ← farver, konstanter og skala-konfiguration
    ├── data_cache.py       ← indlæsning og caching af data fra dataloader
    ├── dataloader.py       ← henter rådata fra GitHub
    ├── weibull_cache.py    ← Bayesiansk Weibull-fitting og caching af MCMC-modeller
    ├── chi.py              ← chi-squared goodness-of-fit mod Weibull-modellen
    ├── widgets.py          ← UI-komponenter
    ├── loading_screen.py   ← splash-screen med progressbar ved opstart
    ├── plot_canvas.py      ← Grafværktøjer for 2D histogram og overdødelighed
    ├── plot_widget.py      ← Wrapper rundt om canvas med graf-header
    ├── control_panel.py    ← Alle indstillinger og filtre
    └── panels.py           ← Layout og synkroniseringslogik
```

### Cache-filer

| Sti | Indhold |
|-----|---------|
| `Settings/data_cache.pkl` | Data indlæst fra dataloader |
| `Settings/cache/weibull/<navn>.pkl` | MCMC posterior-samples for hvert datasæt × kassationsårsag |
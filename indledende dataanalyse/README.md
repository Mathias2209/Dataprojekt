# Indledende dataanalyse
Denne branch indeholder vores indledende dataanalysen. Formålet er at danne et overblik over dataen, undersøge tøjets levetid (dage i cirkulation og antal vask) og identificere mønstre i kassationsårsager. 

Undervejs fandt vi problemer i datakvaliteten, så som genbrug af Unikke Koder (UI). Dette har vi efterfølgende løst og integreret direkte i dataloaderen. Indsigterne fra den indledende analyse danner fundamentet for den endelige analyse og 2D histogram programmet.

Fil-oversigten nedenunder er blot en kort redegørelse af hvad filerne indeholder. Inde på de individuelle filer er der dybere forklaringer af hvad filerne indeholder og hvordan man kan justere koden for at eksempelvis generere plots af andre tøjkategorier, kassationsårsager og så videre.

## Akkumulerede kategorier
Visualisering af hvilke kategorier, som udgør den største andel af datasættet.

## Conflicting UI
Plots over de stykker tøj som deler deres unikke kode.

## Distribution_Of_Most_Common_Items
Overblik over de 10 største subset.

## Indledende 2D historgrammer
Første udkast af 2D histogrammer.

## Overdøddelighed
Første udkast af en overdødeligheds model.

## PCA
Tidligt forsøg på at lave Principal Component Analysis. Vi vurderede den som irrelevant for den endelige analyse og bruger den ikke fremadrettet.

## Scatterplots
Scatterplot for hver kassationsårsag.

## Stackedbarplots
Stacked barplots for hver tøj kategori.

## Tilbage-beregning
Tidspunktet hvert stykke tøj er kommet i cirkulation.

## UI_problem
Samlet overblik over problemet med unikke koder.

## Violinplots forbedret
Violinplots for tøj kategorierne. 

## kassationsårsager_ved_buler_violin
Procentvis fordeling af kassationsårsag for kategorier, som har store buler i vores violinplots.

## uniqueness_ui_11_02
Dybere undersøgelse af problemet med unikke koder

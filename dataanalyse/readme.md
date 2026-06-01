# Dataanalyse

## Chi_2_test
Sammenligner de observerede kassationer med Weibull modellens forudsigelser via en $\chi^2$-værdi. Overdødeligheden undersøges i de perioder, hvor den faktiske kassationsrate overstiger den estimerede baseline for det samlede datasæt.

Det er disse $\chi^2$-værdier som også bruges i vores 2D Histogram app.

## Weibull_model
Vores endelig version af vores Weibull modeller, som bruges i vores 2D Histogram app. Den træner en weibull model på tøjdata med hændblik på at modellere estimeret levetid.
Der trænes én model pr tøjkategori pr kassationsårsag, og en samlet model, hvilket i alt giver os $181$ fittede modeller.

## diff_prodnavn_kass
Anvender *prodnavn_sammenligning* 
til at analysere om de observerede spikes i kassationerne skyldes specifikke produkter eller kassationsårsager. Indeholder konkret analyse af Arla T-shirts med store spikes ved $2$–$3$ og $5$–$6$ år. 


## price analysis
Et forsøg på at analysere nogle pris-relaterede nøgletal, med nogle **opdigtede og fiktive priser** (Da vi ikke har noget data på priser).

Dette indebærer pris-per-dag for levetiden og break even punktet for to produkter, hvor et dyrere produkt bliver det billigste pr. dag, samt viser overlevelseskurver og empirisk levetidsfordeling side om side.

## weibull_fit_metrics
Heri evalueres $135$ af vores Weibull modeller, med mere end $10$ observationer, ved hjælp af $R^2$, Root Mean Squared Error, Mean Absolute Error, Kolmogorov-Smirnov statistik og p-værdier hertil. 

Derudover identificeres og undersøges de dårligste af modellerne, som skyldes negative $R^2$ værdier og høje KS-stats.
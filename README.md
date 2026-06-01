# Levetidsmodellering

I denne branch har vi trænet en matematisk model med henblik på at modellere levetiden af tekstilerne i vores data. 

## Opsætning

For at træne modellen bruges filen `Weibull_model.py` som har inkorporeret vores dataloader `dataloader.py`. Begrundelser af valg af den bayesiske process og valg af fordeling findes i `Kassering_bayesianapproach.ipynb`. 

## Integrering af modellen i vores grafværktøj
Efter træning er vores modelparametrene gemt i en cache, så levetidsmodellen kan tilgåes i vores grafværktøj `histogram_app.py` på main branch, som en del af overdødelighedsplotsne. Dermed kan modellerne og deres respektive parametre til enhver kombination af tøjkategori og kassationsårsag tilgås der.

## OBS
Vi oplevede lange træningstider ved træning af modellen på windows bærbare computere ift til Macbooks. For at nedskære træningstiden har os med windows computere downloadet en g+ compiler, som nedskar træningstiden markant.

## Poisson model
I `Kassering_bayesianapproach.ipynb` findes også en Poisson model som ikke virker. Poisson modellen var vores første forsøg på en levetidsmodel, men Weibull fordelingen gav et bedre fit, som afspejler sig i de plots i `Kassering_bayesianapproach.ipynb`, som er på alt data uden kategorisering. Vi valgte dermed ikke at arbejde videre med en levetidsmodel basseret på Poisson fordelingen. 

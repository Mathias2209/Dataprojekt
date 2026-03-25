'''
Denne python fil træner en weibull model på tøjdata med hændblik på at modellere estimeret levetid.
For dybere gennemgang af modellen se "Kassering_bayesianapproach.ipynb" i Git-branchen "Levetids-modellering"


Når denne fil køres for at genereres trace.nc og ppc.nc lokalt, så modellen ikke trænes ved hvert kald

OBS: Tager ca. 15-45 minutter uden g++ compiler

til at loade den fulde model i andre filer:
    trace = az.from_netcdf('trace.nc')
    ppc = az.from_netcdf('ppc.nc')
eller for en bestemt kategori
    trace = az.from_netcdf('trace_KATEGORI.nc')
    ppc = az.from_netcdf('ppc_KATEGORI.nc')

'''


import pymc as pm
from dataloader import samlet_df
import numpy as np
import arviz as az
from scipy.stats import weibull_min

def weibull(df, draws = 500, tune = 500, chains = 2):
    #finder rækker hvor dage=0 eller vask=0 
    mask = (df['Dage i cirkulation'] == 0) | (df['Total antal vask'] == 0)

    #fjerner dem fra df
    df_filtered = df[~mask]

    alpha_est, _, beta_est = weibull_min.fit(df_filtered['Dage i cirkulation'], floc=0)

    mean_vask = df_filtered['Total antal vask'].mean()
    #normalisering
    vask_norm = (df_filtered['Total antal vask'] - mean_vask) / df_filtered['Total antal vask'].std()
    with pm.Model() as model:
        #priors
        alpha = pm.Gamma('alpha', mu = alpha_est, sigma=0.5)
        intercept = pm.Normal('intercept', mu=np.log(beta_est), sigma=1)
        a = pm.HalfNormal('a', sigma=1) #halfnormal er normalfordelingen med afskæring i 0. Kun højre side

        #deterministisk funktion af a og observerede data
        beta = pm.math.exp(intercept + a * vask_norm)

        #likelihood
        obs = pm.Weibull('obs', alpha = alpha, beta = beta, observed = df_filtered['Dage i cirkulation'])
        
        #resultat
        trace = pm.sample(draws = draws, tune = tune, chains = chains)

    with model:
        ppc = pm.sample_posterior_predictive(trace)

    return trace, ppc

#gemme en lokal version af modellen på hele datasættet
trace, ppc = weibull(samlet_df)
az.to_netcdf(trace, 'trace.nc')
az.to_netcdf(ppc, 'ppc.nc')

#gemme en lokal version af modellen for hver kategori
for kategori in samlet_df['Kategori'].unique():
    df = samlet_df[samlet_df['Kategori']==kategori]
    trace, ppc = weibull(df)
    az.to_netcdf(trace, f'trace_{kategori}.nc')
    az.to_netcdf(ppc, f'ppc_{kategori}.nc')

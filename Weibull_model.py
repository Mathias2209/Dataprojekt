# Kør denne fil for at generere trace.nc og ppc.nc lokalt
# OBS: Tager ca. 15-45 minutter uden g++ compiler

import pymc as pm
from dataloader import samlet_df
import numpy as np
import arviz as az
from scipy.stats import weibull_min

#finder rækker hvor dage=0 eller vask=0 
mask = (samlet_df['Dage i cirkulation'] == 0) | (samlet_df['Total antal vask'] == 0)

#fjerner dem fra df
samlet_df_filtered = samlet_df[~mask]

alpha_est, _, beta_est = weibull_min.fit(samlet_df_filtered['Dage i cirkulation'], floc=0)

mean_vask = samlet_df_filtered['Total antal vask'].mean()
#normalisering
vask_norm = (samlet_df_filtered['Total antal vask'] - mean_vask) / samlet_df_filtered['Total antal vask'].std()

with pm.Model() as model:
    #priors
    alpha = pm.Gamma('alpha', mu = alpha_est, sigma=0.5)
    intercept = pm.Normal('intercept', mu=np.log(beta_est), sigma=1)
    a = pm.HalfNormal('a', sigma=1) #halfnormal er normalfordelingen med afskæring i 0. Kun højre side

    #deterministisk funktion af a og observerede data
    beta = pm.math.exp(intercept + a * vask_norm)

    #likelihood
    obs = pm.Weibull('obs', alpha = alpha, beta = beta, observed = samlet_df_filtered['Dage i cirkulation'])
    
    #resultat
    trace = pm.sample(draws=500, tune=500, chains=2)

with model:
    ppc = pm.sample_posterior_predictive(trace)

#saves result as a file
az.to_netcdf(trace, 'trace.nc')
az.to_netcdf(ppc, 'ppc.nc')

#til loade af model i andre filer
#   trace = az.from_netcdf('trace.nc')
#   ppc = az.from_netcdf('ppc.nc')
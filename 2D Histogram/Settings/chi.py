#getting expected counts and the posterior for the weibull
from weibull_cache import weibull_expected_counts, get_weibull_posterior
import numpy as np

def chi_squared_weibull(df, cache_key, n_bins=100):
    df_filtered = df[df['Dage i cirkulation'] < 2922]

    posterior = get_weibull_posterior(days_array = df['Dage i cirkulation'].values,
    cache_key = cache_key)
    counts, bin_edges = np.histogram(
    df_filtered['Dage i cirkulation'].values,
    bins = n_bins
    )   

    expected_counts = weibull_expected_counts(
        alpha_samples = posterior['alpha_samples'],
        beta_samples = posterior['beta_samples'],
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2,
        bin_width = bin_edges[1] - bin_edges[0],
        n_total = len(df_filtered)
    )

    chi_squared = 0
    for i in range(n_bins):
        chi_squared += (counts[i] - expected_counts['mean'][i])**2 / expected_counts['mean'][i]

    return chi_squared
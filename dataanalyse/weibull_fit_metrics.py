import os
import numpy as np
import pandas as pd
from scipy.stats import weibull_min, ks_2samp
from tabulate import tabulate

from data_cache import load_data
from config import DATASET_MAP
from weibull_cache import get_weibull_posterior, WEIBULL_CACHE_DIR

# pd.set_option('display.width', None, 'display.max_colwidth', None)

def compute_metrics(days: np.ndarray, alpha_mean: float, beta_mean: float) -> dict:
    """
    Beregn fit-metrics ved at sammenligne observeret fordeling mod fitted Weibull.
    """
    days = days[days > 0]
    n = len(days)
    if n < 10:
        return None

    #  Bin data til histogram 
    n_bins = max(1, min(50, n // 20))
    counts, bin_edges = np.histogram(days, bins=n_bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_width   = bin_edges[1] - bin_edges[0]

    # Forventet antal per bin fra fitted Weibull 
    pdf_vals  = weibull_min.pdf(bin_centers, alpha_mean, loc=0, scale=beta_mean)
    expected  = pdf_vals * bin_width * n

    # Metrics 
    residuals = counts - expected
    mse       = np.mean(residuals ** 2)
    rmse      = np.sqrt(mse)
    mae       = np.mean(np.abs(residuals))

    ss_res    = np.sum(residuals ** 2)
    ss_tot    = np.sum((counts - counts.mean()) ** 2)
    r2        = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    # KS-test (empirisk CDF vs fitted CDF)
    fitted_samples = weibull_min.rvs(alpha_mean, loc=0, scale=beta_mean,
                                     size=10_000, random_state=42)
    ks_stat, ks_p  = ks_2samp(days, fitted_samples)

    return {
        'n':       n,
        'R²':      round(r2,      4),
        'RMSE':    round(rmse,    2),
        'MAE':     round(mae,     2),
        'KS-stat': round(ks_stat, 4),
        'KS-p':    round(ks_p,    4),
    }


def run_metrics() -> None:
    # Indlæs data 
    load_data()

    rows = []

    for ds_name, df in DATASET_MAP.items():
        if df is None or 'Dage i cirkulation' not in df.columns:
            continue

        # Alle årsager samlet + per årsag
        combos = [('Alle', df['Dage i cirkulation'].dropna().values)]
        if 'Kassationsårsag (ui)' in df.columns:
            for årsag in sorted(df['Kassationsårsag (ui)'].dropna().unique()):
                subset = df.loc[df['Kassationsårsag (ui)'] == årsag,
                                'Dage i cirkulation'].dropna().values
                combos.append((årsag, subset))

        for årsag, days in combos:
            cache_key = f"{ds_name}__{årsag}".replace(' ', '_')
            safe_key  = "".join(c if c.isalnum() or c in '-_' else '_'
                                for c in cache_key)
            cache_path = os.path.join(WEIBULL_CACHE_DIR, f"{safe_key}.pkl")

            if not os.path.isfile(cache_path):
                print(f"Ingen cache for {ds_name} — {årsag}, springer over")
                continue

            posterior = get_weibull_posterior(days, cache_key)
            alpha_mean = float(np.mean(posterior['alpha_samples']))
            beta_mean  = float(np.mean(posterior['beta_samples']))

            metrics = compute_metrics(days, alpha_mean, beta_mean)
            if metrics is None:
                continue

            rows.append({
                'Datasæt':  ds_name,
                'Årsag':    årsag,
                **metrics,
            })


    ds_order = ['Samlet', 'Bukser', 'T-shirt', 'Skjorte', 'Shorts',
            'Langærmet', 'Jakke', 'Fleece', 'Overall', 'Forklæde',
            'Kittel', 'Busseron', 'Kokkejakke', 'Andet']

    results_df = pd.DataFrame(rows)
    results_df['_order'] = results_df['Datasæt'].map(
        {name: i for i, name in enumerate(ds_order)}
        ).fillna(999)
    results_df = results_df.sort_values(['_order', 'Årsag']).drop(columns='_order')


    first = True
    for ds_name in ds_order:
        group = results_df[results_df['Datasæt'] == ds_name]
        if group.empty:
            continue
        if first:
            print(tabulate(group, headers='keys', tablefmt='rounded_outline',
                           showindex=False, floatfmt='.2f'))
            first = False
        else:
            print(tabulate(group, headers='keys', tablefmt='rounded_outline',
                           showindex=False, floatfmt='.2f'))
        print()

        



    ### Resultater
    print(f"Modeller evalueret (n>10):  {len(results_df)} ")

    ## Gennemsnit og median for hver metric
    print("\nOpsummering:")
    print(f"{'Gennemsnitlig R²:':<28} {results_df['R²'].mean():<10.4f} | {'Median R²:':<20} {results_df['R²'].median():.4f}")
    print(f"{'Gennemsnitlig RMSE:':<28} {results_df['RMSE'].mean():<10.4f} | {'Median RMSE:':<20} {results_df['RMSE'].median():.4f}")
    print(f"{'Gennemsnitlig MAE:':<28} {results_df['MAE'].mean():<10.4f} | {'Median MAE:':<20} {results_df['MAE'].median():.4f}")
    print(f"{'Gennemsnitlig KS-stat:':<28} {results_df['KS-stat'].mean():<10.4f} | {'Median KS-stat:':<20} {results_df['KS-stat'].median():.4f}")
    print(f"{'Gennemsnitlig KS-p:':<28} {results_df['KS-p'].mean():<10.4f} | {'Median KS-p:':<20} {results_df['KS-p'].median():.4f}")

    ## R²
    print(f"\nR²:") 
    # Ekstreme R² værider
    print("Ekstreme R² værider:")
    print(f"R² > 0.9:                   {(results_df['R²'] > 0.9).sum()} modeller")
    print(f"R² < 0.7:                   {(results_df['R²'] < 0.7).sum()} modeller")

    # Negativ R²
    print("\n")
    print(f"Negativ R²:                 {(results_df['R²'] < 0).sum()} modeller")
    print(results_df[results_df['R²'] < 0].to_string())

    # Gode R² værdier
    print("\n")
    print(f"Gode R² værdier >0.98:                 {(results_df['R²'] >= 0.98).sum()} modeller")
    print(results_df[results_df['R²'] > 0.98].to_string())

    ## KS-stats
    print("\nKS-stats:")
    # KS overblik
    print(f"KS-stat > 0.1:              {(results_df['KS-stat'] > 0.1).sum()} modeller")
    print(f"KS-p > 0.05 (godt fit):     {(results_df['KS-p'] > 0.05).sum()} modeller")
    print(f"KS-p < 0.05 (dårligt fit):  {(results_df['KS-p'] < 0.05).sum()} modeller")
    
    # max og min KS-stat
    print(f"KS-stat min:                {results_df['KS-stat'].min():.4f}")
    print(f"KS-stat max:                {results_df['KS-stat'].max():.4f}")

    # Ekstreme KS-stats
    print("\nEkstreme KS-stats:")
    print(f"KS-stat > 0.25:             {(results_df['KS-stat'] > 0.25).sum()} modeller")
    print(results_df[results_df['KS-stat'] > 0.25].to_string())

    ## Dårligste fit
    print("\nDårligste fit:")
    bad_fit = results_df[(results_df['R²'] < 0.7) & (results_df['KS-stat'] > 0.25)]
    print(f"Modeller med R²<0.7 OG KS>0.25: {len(bad_fit)}")
    print(bad_fit.to_string())

# if __name__ == '__main__':
#     run_metrics()
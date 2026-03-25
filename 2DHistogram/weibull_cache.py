# weibull_cache.py — Bayesian Weibull fitting with persistent cache
# ─────────────────────────────────────────────────────────────────────────────
# First call for a given dataset+årsag:
#   → fits a PyMC Weibull model on the FULL unfiltered data (~50 seconds)
#   → saves posterior samples to  cache/weibull/<key>.pkl
#
# Subsequent calls:
#   → loads the pickle directly (~0.1 seconds)
#
# The fit is always on the full dataset so the baseline is not affected by
# whatever the user has filtered in the UI sliders.
#
# Public API
# ----------
#   get_weibull_posterior(days_array, cache_key)
#       → dict with keys: alpha_samples, beta_samples
#         (numpy arrays of posterior draws, ready to use directly)
#
#   invalidate_weibull_cache()
#       → delete all cached Weibull fits (call after "Opdater data")

import os
import pickle
import warnings
import numpy as np

WEIBULL_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'cache', 'weibull'
)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_weibull_posterior(days_array: np.ndarray,
                          cache_key: str,
                          status_cb=None) -> dict:
    """
    Return posterior samples {alpha_samples, beta_samples} for a Weibull
    model fitted to days_array.

    Parameters
    ----------
    days_array : np.ndarray
        Raw 'Dage i cirkulation' values (in days, full unfiltered dataset).
        Rows with value 0 are removed automatically.
    cache_key : str
        Unique string identifying this dataset+årsag combination.
        Used as the cache filename.
    status_cb : callable(str) | None
        Optional progress callback (e.g. splash screen set_status).

    Returns
    -------
    dict with numpy arrays:
        alpha_samples  — posterior draws for Weibull shape parameter
        beta_samples   — posterior draws for Weibull scale parameter (days)
    """
    def _s(msg):
        if status_cb:
            status_cb(msg)

    os.makedirs(WEIBULL_CACHE_DIR, exist_ok=True)

    # Sanitise key for use as filename
    safe_key = "".join(c if c.isalnum() or c in '-_' else '_' for c in cache_key)
    cache_path = os.path.join(WEIBULL_CACHE_DIR, f"{safe_key}.pkl")

    # ── 1. Try cache ───────────────────────────────────────────────────────────
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                result = pickle.load(f)
            return result
        except Exception as e:
            print(f"Weibull cache corrupt for '{cache_key}', refitting: {e}")
            os.remove(cache_path)

    # ── 2. Fit PyMC model ──────────────────────────────────────────────────────
    _s(f"Weibull-model: passer til '{cache_key}'…")

    # Clean data — remove zeros and NaNs
    data = days_array[~np.isnan(days_array)]
    data = data[data > 0].astype(float)

    if len(data) < 30:
        # Not enough data for MCMC — fall back to MLE
        from scipy.stats import weibull_min
        alpha_fit, _, beta_fit = weibull_min.fit(data, floc=0)
        result = {
            'alpha_samples': np.full(200, alpha_fit),
            'beta_samples':  np.full(200, beta_fit),
            'method':        'mle_fallback',
            'n':             len(data),
        }
        _save_cache(cache_path, result)
        return result

    # Get MLE estimates to initialise priors (same as notebook)
    from scipy.stats import weibull_min
    alpha_est, _, beta_est = weibull_min.fit(data, floc=0)

    import pymc as pm

    _s(f"Weibull MCMC: kører på {len(data):,} rækker  (første gang ~50 sek)…")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        import pytensor
        # Suppress PyMC progress bars in the Qt app
        import logging
        logging.getLogger("pymc").setLevel(logging.ERROR)
        logging.getLogger("pytensor").setLevel(logging.ERROR)

        with pm.Model() as model:
            # Priors — exactly as in the notebook
            alpha = pm.Gamma('alpha', mu=alpha_est, sigma=0.5)

            # Simple model: no vask covariate — we fit on the full marginal
            # distribution of dage so the baseline is independent of filters.
            # The vask effect belongs to the 2D histogram regression, not here.
            beta  = pm.Gamma('beta', mu=beta_est,
                             sigma=max(beta_est * 0.3, 50.0))

            # Likelihood
            _obs = pm.Weibull('obs', alpha=alpha, beta=beta, observed=data)

            # Sample
            trace = pm.sample(
                draws=500,
                tune=500,
                chains=4,
                progressbar=False,   # no tqdm output in Qt
                return_inferencedata=True,
            )

    alpha_samples = trace.posterior['alpha'].values.flatten()
    beta_samples  = trace.posterior['beta'].values.flatten()

    result = {
        'alpha_samples': alpha_samples,
        'beta_samples':  beta_samples,
        'method':        'mcmc',
        'n':             len(data),
        'alpha_mean':    float(alpha_samples.mean()),
        'beta_mean':     float(beta_samples.mean()),
        'alpha_hdi':     _hdi(alpha_samples),
        'beta_hdi':      _hdi(beta_samples),
    }

    _save_cache(cache_path, result)
    _s(f"Weibull MCMC færdig — cache gemt ✔")
    return result


def invalidate_weibull_cache() -> None:
    """Delete all cached Weibull fits so they are rebuilt on next use."""
    if not os.path.isdir(WEIBULL_CACHE_DIR):
        return
    removed = 0
    for fname in os.listdir(WEIBULL_CACHE_DIR):
        if fname.endswith('.pkl'):
            os.remove(os.path.join(WEIBULL_CACHE_DIR, fname))
            removed += 1
    if removed:
        print(f"✓ Weibull cache slettet: {removed} fil(er)")


def prefetch_all_weibull(status_cb=None, progress_cb=None) -> None:
    """
    Pre-fit Weibull models for every dataset × kassationsårsag combination
    that does not already have a cache file.  Call this at startup after
    data has been loaded into DATASET_MAP.

    Parameters
    ----------
    status_cb    : callable(str)  — splash status label update
    progress_cb  : callable(int, str)  — splash.set_progress(percent, msg)
    """
    from config import DATASET_MAP

    def _s(msg):
        if status_cb:
            status_cb(msg)
    def _p(pct, msg):
        if progress_cb:
            progress_cb(pct, msg)
        elif status_cb:
            status_cb(msg)

    # Build the full list of (dataset_name, årsag, days_array) tuples
    tasks = []
    for ds_name, df in DATASET_MAP.items():
        if df is None or 'Dage i cirkulation' not in df.columns:
            continue
        days_all = df['Dage i cirkulation'].dropna().values

        # "Alle" — whole dataset
        tasks.append((ds_name, 'Alle', days_all))

        # One per kassationsårsag
        if 'Kassationsårsag (ui)' in df.columns:
            for årsag in sorted(df['Kassationsårsag (ui)'].dropna().unique()):
                subset = df.loc[df['Kassationsårsag (ui)'] == årsag,
                                'Dage i cirkulation'].dropna().values
                tasks.append((ds_name, årsag, subset))

    # Filter to only tasks that are not yet cached
    pending = []
    for ds_name, årsag, days in tasks:
        cache_key = f"{ds_name}__{årsag}".replace(' ', '_')
        safe_key  = "".join(c if c.isalnum() or c in '-_' else '_'
                            for c in cache_key)
        cache_path = os.path.join(WEIBULL_CACHE_DIR, f"{safe_key}.pkl")
        if not os.path.isfile(cache_path):
            pending.append((ds_name, årsag, days, cache_key))

    if not pending:
        # All models already cached — return immediately WITHOUT importing
        # pymc or pytensor.  On Windows this avoids a slow C++ compilation
        # check that happens on every pymc import even when no fitting is done.
        _p(90, "Alle Weibull-modeller er allerede cachet ✔")
        return

    # Only reach here if at least one model needs fitting — now safe to import.
    n_total = len(pending)
    _s(f"Weibull MCMC: {n_total} modeller skal fittes (første opstart)…")

    for i, (ds_name, årsag, days, cache_key) in enumerate(pending):
        # Progress spans 80 → 90 % across all fits
        pct = 80 + int(10 * i / n_total)
        _p(pct, f"Weibull [{i+1}/{n_total}]: {ds_name} — {årsag}…")

        # get_weibull_posterior handles caching internally
        get_weibull_posterior(days, cache_key)

    _p(90, f"Weibull MCMC færdig — {n_total} modeller cachet ✔")


def weibull_expected_counts(alpha_samples: np.ndarray,
                             beta_samples: np.ndarray,
                             bin_centers: np.ndarray,
                             bin_width: float,
                             n_total: int) -> dict:
    """
    Compute the posterior expected count curve and 95 % credible band.

    Parameters
    ----------
    alpha_samples, beta_samples : posterior draws (shape: [n_samples])
    bin_centers : bin centre positions IN DAYS
    bin_width   : bin width IN DAYS
    n_total     : total number of observations used for the fit

    Returns
    -------
    dict:
        mean    — posterior mean expected count per bin
        lower   — 2.5th percentile (lower credible bound)
        upper   — 97.5th percentile (upper credible bound)
    """
    from scipy.stats import weibull_min

    # For each posterior sample, compute the expected count curve
    # Shape: [n_samples, n_bins]
    n_samples = len(alpha_samples)
    curves = np.empty((n_samples, len(bin_centers)))

    for i in range(n_samples):
        pdf_vals = weibull_min.pdf(bin_centers,
                                   alpha_samples[i],
                                   loc=0,
                                   scale=beta_samples[i])
        curves[i] = pdf_vals * bin_width * n_total

    return {
        'mean':  curves.mean(axis=0),
        'lower': np.percentile(curves, 2.5,  axis=0),
        'upper': np.percentile(curves, 97.5, axis=0),
    }


# ── Internal helpers ───────────────────────────────────────────────────────────

def _save_cache(path: str, result: dict) -> None:
    try:
        with open(path, 'wb') as f:
            # Protocol 4 works on Python 3.8+ on all platforms (Windows/Mac/Linux).
            # Avoid HIGHEST_PROTOCOL which can produce files unreadable on older
            # Python versions when sharing cache files between machines.
            pickle.dump(result, f, protocol=4)
        print(f"✓ Weibull cache gemt: {os.path.basename(path)}")
    except Exception as e:
        print(f"Weibull cache-skrivning fejlede: {e}")


def _hdi(samples: np.ndarray, prob: float = 0.94) -> tuple:
    """Compute the Highest Density Interval."""
    samples_sorted = np.sort(samples)
    n = len(samples_sorted)
    interval_idx = int(np.floor(prob * n))
    n_intervals  = n - interval_idx
    interval_width = samples_sorted[interval_idx:] - samples_sorted[:n_intervals]
    min_idx = int(np.argmin(interval_width))
    return (float(samples_sorted[min_idx]),
            float(samples_sorted[min_idx + interval_idx]))
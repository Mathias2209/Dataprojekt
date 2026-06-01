"""
price analysis.py — Cost-per-day analysis for two T-shirt products
─────────────────────────────────────────────────────────────────────
Compares two products on cost efficiency over their lifetime using
the empirical survival function derived from Weibull MCMC posteriors.

Usage:
    python price_analysis.py

Configuration is at the top of the file — set product names and prices.
Requires the same folder as the histogram app (uses data_cache.pkl).
"""

import os
import sys
import pickle
import warnings
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
from scipy.stats import weibull_min

# ── Configuration — edit these ─────────────────────────────────────────────────
PRODUCTS = [
    {
        "navn":     "unisex hvid k/æ P/B",   # substring match on Produkt - Produkt
        "pris":     45,                        # kr.
        "farve":    "#4ea8de",                 # blue
        "label":    "Unisex hvid k/æ P/B",
    },
    {
        "navn":     "Hvid B/P M Arla Tryk",
        "pris":     75,
        "farve":    "#f4a261",                 # orange
        "label":    "Hvid B/P M Arla Tryk",
    },
]

KASSATIONSÅRSAG = "Alm.slid uden restværdi"   # set to None for alle årsager
KATEGORI        = "T-shirt"                    # used when filtering samlet_df
MAX_ÅR          = 8                            # x-axis upper limit
DATA_CACHE      = "data_cache.pkl"

# ── Colours ────────────────────────────────────────────────────────────────────
BG      = "#0f0f1a"
BG2     = "#1a1a2e"
BG3     = "#22223b"
GRID    = "#2a2a45"
TEXT    = "#e8e8f0"
SUBTEXT = "#8888aa"

# ── Load data ──────────────────────────────────────────────────────────────────

def load_tshirt_data() -> "pd.DataFrame":
    if not os.path.isfile(DATA_CACHE):
        sys.exit(
            f"Fejl: {DATA_CACHE} ikke fundet.\n"
            "Kør histogram_app.py én gang først for at bygge cachen."
        )
    with open(DATA_CACHE, "rb") as f:
        frames = pickle.load(f)

    # frames is the raw dict from dataloader; tshirt_data is stored separately
    # but we reconstruct from samlet_df + Kategori for product-level filtering
    samlet = frames.get("samlet_df")
    if samlet is None:
        sys.exit("Fejl: samlet_df ikke fundet i cache.")

    df = samlet[samlet["Kategori"] == KATEGORI].copy()

    if KASSATIONSÅRSAG:
        df = df[df["Kassationsårsag (ui)"] == KASSATIONSÅRSAG]

    print(f"T-shirt rows after årsag filter: {len(df):,}")
    print(f"Unikke produktnavne: {df['Produkt - Produkt'].nunique()}")
    return df


def find_product(df: "pd.DataFrame", navn: str) -> "pd.DataFrame":
    """Case-insensitive substring match on Produkt - Produkt."""
    mask = df["Produkt - Produkt"].str.contains(navn, case=False, na=False)
    sub  = df[mask]
    if len(sub) == 0:
        # Try to show similar names to help with debugging
        sample = df["Produkt - Produkt"].dropna().unique()[:10]
        print(f"\n⚠  Ingen rækker fundet for '{navn}'.")
        print("   Første 10 produktnavne i datasættet:")
        for n in sample:
            print(f"     {n}")
    else:
        print(f"  '{navn}': {len(sub):,} kassationer")
    return sub


# ── Weibull fit ────────────────────────────────────────────────────────────────

def fit_weibull_mcmc(days: np.ndarray, label: str) -> dict:
    """
    Fit a Weibull model via PyMC MCMC if available,
    otherwise fall back to scipy MLE.
    """
    data = days[days > 0]
    alpha_est, _, beta_est = weibull_min.fit(data, floc=0)

    try:
        import pymc as pm
        import logging
        logging.getLogger("pymc").setLevel(logging.ERROR)
        logging.getLogger("pytensor").setLevel(logging.ERROR)

        print(f"  MCMC fitting '{label}' ({len(data):,} obs)…", flush=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pm.Model():
                alpha = pm.Gamma("alpha", mu=alpha_est, sigma=0.5)
                beta  = pm.Gamma("beta",  mu=beta_est,
                                 sigma=max(beta_est * 0.3, 50.0))
                pm.Weibull("obs", alpha=alpha, beta=beta, observed=data)
                trace = pm.sample(500, tune=500, chains=2,
                                  progressbar=False,
                                  return_inferencedata=True)

        alpha_s = trace.posterior["alpha"].values.flatten()
        beta_s  = trace.posterior["beta"].values.flatten()
        method  = "MCMC"

    except (ImportError, Exception) as e:
        print(f"  PyMC ikke tilgængeligt ({e}) — bruger MLE")
        alpha_s = np.full(200, alpha_est)
        beta_s  = np.full(200, beta_est)
        method  = "MLE"

    return {
        "alpha_samples": alpha_s,
        "beta_samples":  beta_s,
        "alpha_mean":    float(alpha_s.mean()),
        "beta_mean":     float(beta_s.mean()),
        "method":        method,
        "n":             len(data),
    }


# ── Survival & cost curves ─────────────────────────────────────────────────────

def survival_curves(posterior: dict, t_days: np.ndarray) -> dict:
    """
    Return posterior mean + 95 % credible band for the survival function S(t).
    S(t) = P(lifetime > t) = 1 - CDF(t)
    """
    curves = np.empty((len(posterior["alpha_samples"]), len(t_days)))
    for i, (a, b) in enumerate(zip(posterior["alpha_samples"],
                                    posterior["beta_samples"])):
        curves[i] = 1 - weibull_min.cdf(t_days, a, loc=0, scale=b)

    return {
        "mean":  curves.mean(axis=0),
        "lower": np.percentile(curves, 2.5,  axis=0),
        "upper": np.percentile(curves, 97.5, axis=0),
    }


def cost_per_day_curves(survival: dict, pris: float) -> dict:
    """
    Cost-per-day at time t = pris / (t * S(t) + integral of S up to t).

    More intuitively: expected total days of service if you buy one unit
    and it survives with probability S(t) is E[min(T, t)] = ∫₀ᵗ S(u) du.
    Cost per expected service-day = pris / E[min(T, t)].
    """
    # We compute this on the mean survival curve for the main line,
    # and on the credible band for the shaded region.
    result = {}
    for key in ("mean", "lower", "upper"):
        s = survival[key]
        # Cumulative integral ∫₀ᵗ S(u) du via trapezoidal rule
        # This equals E[min(T, t)] — expected days of service up to time t
        cum_service = np.maximum(np.cumsum(s) * (t_days[1] - t_days[0]), 1e-6)
        result[key] = pris / cum_service

    return result


# ── Plotting ───────────────────────────────────────────────────────────────────

def style_ax(ax, xlabel="", ylabel=""):
    ax.set_facecolor(BG2)
    ax.set_xlabel(xlabel, color=SUBTEXT, fontsize=10)
    ax.set_ylabel(ylabel, color=SUBTEXT, fontsize=10)
    ax.tick_params(colors=SUBTEXT, which="both", labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)
    ax.grid(True, color=GRID, linestyle="--", linewidth=0.6, alpha=0.7)
    ax.xaxis.label.set_color(SUBTEXT)
    ax.yaxis.label.set_color(SUBTEXT)


def format_kr(x, _):
    return f"{x:.2f} kr"


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    matplotlib.rcParams.update({
        "text.color":      TEXT,
        "axes.labelcolor": SUBTEXT,
        "xtick.color":     SUBTEXT,
        "ytick.color":     SUBTEXT,
        "font.family":     "sans-serif",
    })

    # ── 1. Load & filter data ──────────────────────────────────────────────────
    print("Indlæser data…")
    df = load_tshirt_data()

    results = []
    for cfg in PRODUCTS:
        print(f"\nBehandler: {cfg['label']}")
        sub = find_product(df, cfg["navn"])
        if len(sub) == 0:
            print(f"  Springer over — ingen data.")
            continue
        days = sub["Dage i cirkulation"].dropna().values
        posterior = fit_weibull_mcmc(days, cfg["label"])
        results.append({**cfg, "posterior": posterior, "days": days})

    if len(results) < 2:
        sys.exit("Fejl: Fandt ikke nok produkter til sammenligning.")

    # ── 2. Compute curves ──────────────────────────────────────────────────────
    t_days = np.linspace(1, MAX_ÅR * 365.25, 2000)
    t_år   = t_days / 365.25

    for r in results:
        r["survival"]     = survival_curves(r["posterior"], t_days)
        r["cost_per_day"] = cost_per_day_curves(r["survival"], r["pris"])

    # ── 3. Find crossover point ────────────────────────────────────────────────
    cpd_a = results[0]["cost_per_day"]["mean"]
    cpd_b = results[1]["cost_per_day"]["mean"]
    diff  = cpd_a - cpd_b   # positive = A more expensive per day

    crossover_år = None
    # Find where the cheaper-upfront product stops being cheaper per day
    sign_changes = np.where(np.diff(np.sign(diff)))[0]
    if len(sign_changes) > 0:
        idx = sign_changes[0]
        crossover_år = float(t_år[idx])

    # ── 4. Build figure ────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(13, 9), facecolor=BG)
    gs  = GridSpec(2, 2, figure=fig,
                   left=0.08, right=0.96,
                   top=0.90, bottom=0.08,
                   hspace=0.38, wspace=0.32)

    ax_cpd  = fig.add_subplot(gs[0, :])   # top: cost per day (full width)
    ax_surv = fig.add_subplot(gs[1, 0])   # bottom left: survival
    ax_hist = fig.add_subplot(gs[1, 1])   # bottom right: empirical distribution

    # ── Panel 1: Cost per day ──────────────────────────────────────────────────
    style_ax(ax_cpd,
             xlabel="År i cirkulation",
             ylabel="Pris per forventet servicedag  (kr/dag)")

    for r in results:
        cpd   = r["cost_per_day"]
        farve = r["farve"]
        label = r["label"]
        pris  = r["pris"]
        a_m   = r["posterior"]["alpha_mean"]
        b_m   = r["posterior"]["beta_mean"] / 365.25
        method = r["posterior"]["method"]

        ax_cpd.fill_between(t_år, cpd["lower"], cpd["upper"],
                            color=farve, alpha=0.15)
        ax_cpd.plot(t_år, cpd["mean"],
                    color=farve, lw=2.5,
                    label=f"{label}  ({pris} kr  |  α={a_m:.2f}, β={b_m:.1f} år  [{method}])")

        # Mark starting cost (day 1)
        ax_cpd.scatter([t_år[0]], [cpd["mean"][0]],
                       color=farve, s=60, zorder=5)

    # Crossover annotation
    if crossover_år is not None:
        cpd_cross = np.interp(crossover_år, t_år,
                              results[0]["cost_per_day"]["mean"])
        ax_cpd.axvline(crossover_år, color="white",
                       lw=1.2, ls=":", alpha=0.6)
        ax_cpd.annotate(
            f"Breakeven\n{crossover_år:.1f} år",
            xy=(crossover_år, cpd_cross),
            xytext=(crossover_år + 0.25, cpd_cross * 1.15),
            color="white", fontsize=9,
            arrowprops=dict(arrowstyle="->", color="white", lw=1),
            bbox=dict(boxstyle="round,pad=0.3", fc=BG3, ec=GRID, alpha=0.9),
        )

        # Shade the region where the expensive product is actually cheaper/day
        cheaper_idx = diff > 0   # A (cheap upfront) costs more per day here
        ax_cpd.fill_between(
            t_år, cpd_a, cpd_b,
            where=cheaper_idx,
            color=results[1]["farve"], alpha=0.12,
            label=f"{results[1]['label']} billigere/dag her",
        )

    ax_cpd.yaxis.set_major_formatter(mticker.FuncFormatter(format_kr))
    ax_cpd.set_xlim(0, MAX_ÅR)
    ax_cpd.set_ylim(bottom=0)
    ax_cpd.legend(loc="upper right", fontsize=8.5,
                  facecolor=BG3, edgecolor=GRID, labelcolor=TEXT,
                  framealpha=0.9)
    ax_cpd.set_title("Pris per forventet servicedag over levetiden",
                     color=TEXT, fontsize=12, fontweight="bold", pad=10)

    # Add a subtitle with the kr/dag at year 1, 3, and 8
    subtitle_parts = []
    for r in results:
        c1 = np.interp(1, t_år, r["cost_per_day"]["mean"])
        c3 = np.interp(3, t_år, r["cost_per_day"]["mean"])
        c8 = np.interp(MAX_ÅR, t_år, r["cost_per_day"]["mean"])
        subtitle_parts.append(
            f"{r['label']}: {c1:.2f} kr/dag @ 1 år  →  "
            f"{c3:.2f} kr/dag @ 3 år  →  {c8:.2f} kr/dag @ {MAX_ÅR} år"
        )
    fig.text(0.5, 0.915, "   |   ".join(subtitle_parts),
             ha="center", va="top", color=SUBTEXT, fontsize=8.5)

    # ── Panel 2: Survival curves ───────────────────────────────────────────────
    style_ax(ax_surv,
             xlabel="År i cirkulation",
             ylabel="Andel stadig i brug  (%)")

    for r in results:
        surv  = r["survival"]
        farve = r["farve"]
        ax_surv.fill_between(t_år,
                             surv["lower"] * 100,
                             surv["upper"] * 100,
                             color=farve, alpha=0.15)
        ax_surv.plot(t_år, surv["mean"] * 100,
                     color=farve, lw=2.2, label=r["label"])

        # Mark median survival (50 % line)
        med_idx = np.argmin(np.abs(surv["mean"] - 0.5))
        med_år  = t_år[med_idx]
        ax_surv.axvline(med_år, color=farve, lw=0.9, ls="--", alpha=0.5)
        ax_surv.text(med_år + 0.1, 52,
                     f"Median\n{med_år:.1f} år",
                     color=farve, fontsize=7.5)

    ax_surv.axhline(50, color=GRID, lw=0.8, ls=":")
    ax_surv.set_xlim(0, MAX_ÅR)
    ax_surv.set_ylim(0, 105)
    ax_surv.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax_surv.legend(loc="upper right", fontsize=8,
                   facecolor=BG3, edgecolor=GRID, labelcolor=TEXT)
    ax_surv.set_title("Overlevelseskurve (Weibull)",
                      color=TEXT, fontsize=10, fontweight="bold", pad=8)

    # ── Panel 3: Empirical lifetime distribution ───────────────────────────────
    style_ax(ax_hist,
             xlabel="År i cirkulation",
             ylabel="Antal kasserede produkter")

    for r in results:
        ax_hist.hist(r["days"] / 365.25,
                     bins=60,
                     range=(0, MAX_ÅR),
                     color=r["farve"],
                     alpha=0.55,
                     label=r["label"],
                     edgecolor="none")

    ax_hist.set_xlim(0, MAX_ÅR)
    ax_hist.legend(loc="upper right", fontsize=8,
                   facecolor=BG3, edgecolor=GRID, labelcolor=TEXT)
    ax_hist.set_title("Empirisk levetidsfordeling",
                      color=TEXT, fontsize=10, fontweight="bold", pad=8)

    # ── Overall title ──────────────────────────────────────────────────────────
    årsag_str = f" — {KASSATIONSÅRSAG}" if KASSATIONSÅRSAG else ""
    fig.suptitle(
        f"Omkostningsanalyse: {' vs '.join(r['label'] for r in results)}{årsag_str}",
        color=TEXT, fontsize=14, fontweight="bold", y=0.975,
    )

    plt.savefig("cost_comparison.png", dpi=150, bbox_inches="tight",
                facecolor=BG)
    print("\n✔ Gemt: cost_comparison.png")
    plt.show()
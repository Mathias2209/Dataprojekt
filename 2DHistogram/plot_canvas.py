# plot_canvas.py — matplotlib canvas and all histogram drawing logic
# ─────────────────────────────────────────────────────────────────────────────
# This is the heaviest file — it owns draw_histogram() entirely.
# Edit this file to change anything about how plots look or what is drawn.

import copy
import numpy as np
from scipy.stats import linregress

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import LogNorm, Normalize
from PyQt5.QtWidgets import QSizePolicy

from config import (
    DARK_BG, PANEL_BG, TEXT, SUBTEXT, BORDER, ACCENT, SUCCESS, INFO,
    SCALE_CONFIG, REF_LINE_DEFS, REF_COLORS, REF_LINESTYLES, RATIO_COL,
    DATASET_MAP,
)
from weibull_cache import get_weibull_posterior, weibull_expected_counts


class PlotCanvas(FigureCanvas):
    """Matplotlib canvas embedded in Qt.  Call draw_histogram() to render."""

    def __init__(self):
        self.fig = Figure(figsize=(8, 5), facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setStyleSheet(f"background-color:{DARK_BG};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # ── Main draw entry point ─────────────────────────────────────────────────

    def draw_histogram(
        self,
        data,
        kassationsårsag: str,
        bins: int,
        min_dage: int,
        max_dage: int,
        min_vask: int,
        max_vask: int,
        x_skala: str,
        datasæt_navn: str  = '',
        total: int         = None,
        log_color: bool    = True,
        ref_lines: list    = None,
        vmin: float        = 0.1,
        min_ratio: float   = None,
        max_ratio: float   = None,
        show_percentiles: list = None,
        plot_type: str     = 'Begge',
        smooth: int        = 15,
        log_y_hist: bool   = False,
        show_regression: bool = True,
        show_4sigma: bool  = True,
        show_2sigma: bool  = True,
        show_survival: bool = True,
    ):
        """
        Render the histogram (and optionally the overdødelighed curve) into
        self.fig.  Returns the filtered DataFrame kd so callers can export CSV.
        """
        self.fig.clear()

        # ── Filter data ───────────────────────────────────────────────────────
        kd = (data if kassationsårsag == 'Alle'
              else data[data['Kassationsårsag (ui)'] == kassationsårsag])
        kd = kd[
            (kd['Dage i cirkulation'] >= min_dage) &
            (kd['Dage i cirkulation'] <= max_dage) &
            (kd['Total antal vask']   >= min_vask) &
            (kd['Total antal vask']   <= max_vask)
        ]
        if RATIO_COL in kd.columns:
            if min_ratio is not None: kd = kd[kd[RATIO_COL] >= min_ratio]
            if max_ratio is not None: kd = kd[kd[RATIO_COL] <= max_ratio]

        div    = SCALE_CONFIG[x_skala]['divisor']
        xlabel = SCALE_CONFIG[x_skala]['label']
        x_min, x_max = min_dage / div, max_dage / div
        if x_min >= x_max:  x_max = x_min + 0.1
        if min_vask >= max_vask: max_vask = min_vask + 1

        cmap = copy.copy(matplotlib.colormaps['Reds'])
        cmap.set_bad('#13131f'); cmap.set_under('#13131f')

        matplotlib.rcParams.update({
            'text.color':      TEXT,
            'axes.labelcolor': TEXT,
            'xtick.color':     SUBTEXT,
            'ytick.color':     SUBTEXT,
        })

        # ── Empty-data guard ──────────────────────────────────────────────────
        if len(kd) == 0:
            ax = self.fig.add_subplot(111, facecolor='#13131f')
            ax.text(0.5, 0.5, 'Ingen data i det valgte interval',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=13, color=SUBTEXT)
            for spine in ax.spines.values():
                spine.set_edgecolor(BORDER)
            self.draw()
            return kd

        x_data_raw = kd['Dage i cirkulation'].dropna().values
        x_data     = x_data_raw / div
        y_data     = kd['Total antal vask'].dropna().values

        # ── Regression ────────────────────────────────────────────────────────
        stats_text  = ""
        slope       = intercept = 0
        can_regress = len(np.unique(x_data)) > 1
        if can_regress and show_regression:
            slope, intercept, r_value, _, _ = linregress(x_data, y_data)
            vask_pr_md = (slope * 30.437 if x_skala == 'Dage'
                          else slope if x_skala == 'Måneder'
                          else slope / 12)
            stats_text = (
                f"Forventet Vask = {slope:.2f} × {x_skala} + {intercept:.2f}  |  "
                f"Gns: {vask_pr_md:.2f} vaske/md  |  R²: {r_value**2:.3f}"
            )

        # ── Subplot layout ────────────────────────────────────────────────────
        ax = ax_hist = None
        if plot_type == 'Begge':
            gs      = self.fig.add_gridspec(2, 1, height_ratios=[2.2, 1.3], hspace=0.15)
            ax      = self.fig.add_subplot(gs[0], facecolor='#13131f')
            ax_hist = self.fig.add_subplot(gs[1], facecolor='#13131f', sharex=ax)
        elif plot_type == '2D Histogram':
            ax      = self.fig.add_subplot(111, facecolor='#13131f')
        else:
            ax_hist = self.fig.add_subplot(111, facecolor='#13131f')

        # ── 2D Histogram ──────────────────────────────────────────────────────
        if ax is not None:
            self._draw_2d(ax, x_data, y_data, x_min, x_max, min_vask, max_vask,
                          div, bins, cmap, vmin, log_color, slope, intercept,
                          can_regress, show_regression, ref_lines, show_percentiles,
                          kd, xlabel, ax_hist, datasæt_navn, kassationsårsag,
                          total, len(kd))

        # ── Overdødelighed ────────────────────────────────────────────────────
        if ax_hist is not None:
            # full_days: unfiltered days for this dataset+årsag — Weibull is
            # always fitted on the full population, not the slider subset.
            full_df   = DATASET_MAP.get(datasæt_navn)
            full_days = (
                full_df['Dage i cirkulation'].dropna().values
                if full_df is not None else x_data_raw
            )
            cache_key = f"{datasæt_navn}__{kassationsårsag}".replace(' ', '_')
            self._draw_overdødelighed(ax_hist, x_data_raw, x_data, x_min, x_max,
                                       min_dage, max_dage, div, bins,
                                       log_y_hist, xlabel, ax,
                                       datasæt_navn, kassationsårsag, total, len(kd),
                                       full_days, cache_key,
                                       show_4sigma, show_2sigma, show_survival)

        # ── Regression footer text ────────────────────────────────────────────
        if show_regression and can_regress and ax is not None:
            self.fig.text(
                0.5, 0.01, stats_text,
                ha='center', va='bottom', fontsize=9, color=TEXT,
                bbox=dict(facecolor=PANEL_BG, edgecolor=BORDER, boxstyle='round,pad=0.4')
            )
            self.fig.subplots_adjust(bottom=0.12)

        self.fig.tight_layout()
        if show_regression and can_regress and ax is not None:
            self.fig.subplots_adjust(bottom=0.12)

        self.draw()
        return kd

    # ── Private drawing helpers ───────────────────────────────────────────────

    def _draw_2d(self, ax, x_data, y_data, x_min, x_max,
                 min_vask, max_vask, div, bins, cmap, vmin, log_color,
                 slope, intercept, can_regress, show_regression,
                 ref_lines, show_percentiles, kd, xlabel, ax_hist,
                 datasæt_navn, kassationsårsag, total, n_kd):

        h = ax.hist2d(x_data, y_data, bins=bins, cmap=cmap,
                      range=[[x_min, x_max], [min_vask, max_vask]],
                      norm=LogNorm(vmin=vmin) if log_color else Normalize(vmin=vmin))
        cb = self.fig.colorbar(
            h[3], ax=ax,
            label='Antal produkter (log)' if log_color else 'Antal produkter'
        )
        cb.ax.yaxis.label.set_color(TEXT)
        cb.ax.tick_params(colors=TEXT)

        if show_regression and can_regress:
            x_line = np.array([x_min, x_max])
            ax.plot(x_line, slope * x_line + intercept,
                    color='white', lw=2, ls='-', label='Best Fit', alpha=0.85)

        if ref_lines:
            xs = np.linspace(x_min, x_max, 300)
            for i, (interval_days, lbl) in enumerate(REF_LINE_DEFS):
                if lbl in ref_lines:
                    ax.plot(xs, (xs * div) / interval_days,
                            color=REF_COLORS[i], lw=1.5,
                            ls=REF_LINESTYLES[i], label=lbl, alpha=0.9)

        if ref_lines or (show_regression and can_regress):
            ax.legend(fontsize=8, loc='upper left',
                      facecolor=PANEL_BG, edgecolor=BORDER, labelcolor=TEXT)

        if show_percentiles:
            col = kd['Dage i cirkulation']
            for label, val, ls, y_frac in [
                ('25%',    col.quantile(0.25), '--', 0.85),
                ('Median', col.median(),       '-',  0.97),
                ('75%',    col.quantile(0.75), '--', 0.85),
            ]:
                if label not in show_percentiles: continue
                vx = val / div
                if x_min < vx < x_max:
                    ax.axvline(vx, color='white', lw=1.5, ls=ls, alpha=0.85)
                    ax.text(vx, max_vask * y_frac,
                            f'{label}\n{val / 365.25:.1f} år',
                            color='white', fontsize=7.5, ha='center', va='top',
                            bbox=dict(boxstyle='round,pad=0.2',
                                      fc='#13131f', alpha=0.8, ec='none'))

        title   = f'{datasæt_navn} — {kassationsårsag}' if datasæt_navn else kassationsårsag
        pct_str = f'  ({100 * n_kd / total:.1f}% af datasæt)' if total else ''
        ax.set_title(f'{title}\n{n_kd} produkter{pct_str}', color=TEXT, fontsize=11)
        ax.set_ylabel('Total antal vask', color=SUBTEXT)
        if ax_hist is None:
            ax.set_xlabel(xlabel, color=SUBTEXT)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(min_vask, max_vask)
        ax.tick_params(colors=SUBTEXT)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)

    def _draw_overdødelighed(self, ax_hist, x_data_raw, x_data,
                              x_min, x_max, min_dage, max_dage,
                              div, bins, log_y_hist, xlabel, ax,
                              datasæt_navn, kassationsårsag, total, n_kd,
                              full_days, cache_key,
                              show_4sigma=True, show_2sigma=True, show_survival=True):

        hist_bins   = np.linspace(min_dage, max_dage, bins + 1)
        counts, _   = np.histogram(x_data_raw, bins=hist_bins)
        bin_centers = (hist_bins[:-1] + hist_bins[1:]) / 2
        x_hist_vals = bin_centers / div
        bin_width   = hist_bins[1] - hist_bins[0]   # always in days

        # ── Bayesian Weibull fit on the FULL unfiltered dataset ───────────────
        # get_weibull_posterior() loads from cache if available, otherwise
        # runs PyMC MCMC (draws=500, tune=500, chains=2) and caches result.
        posterior = get_weibull_posterior(full_days, cache_key)
        alpha_samples = posterior['alpha_samples']
        beta_samples  = posterior['beta_samples']

        # Scale the Weibull to the *filtered* count (n_kd), not the full n.
        # This keeps the baseline proportional to what is actually shown.
        curves = weibull_expected_counts(
            alpha_samples, beta_samples,
            bin_centers, bin_width,
            n_total=len(x_data_raw),   # filtered n so curve matches histogram
        )
        baseline = np.where(curves['mean']  < 1e-9, 1e-9, curves['mean'])
        lower    = np.where(curves['lower'] < 1e-9, 1e-9, curves['lower'])
        upper    = curves['upper']

        # ── Poisson uncertainty bands on top of Weibull credible band ─────────
        # Combine two sources of uncertainty:
        #   1. Parameter uncertainty  → 95 % credible band (shaded)
        #   2. Poisson sampling noise → ±2σ and ±4σ lines above the mean
        poisson_std = np.sqrt(baseline)

        # 95 % posterior credible band (parameter uncertainty)
        ax_hist.fill_between(x_hist_vals, lower, upper,
                             alpha=0.20, color=INFO, label='95% kredibelt interval')

        # Threshold lines (Poisson noise around the posterior mean)
        if show_4sigma:
            ax_hist.plot(x_hist_vals, baseline + 4 * poisson_std,
                         color='#f38ba8', lw=1.2, ls='-.', alpha=0.85, label='4σ')
        if show_2sigma:
            ax_hist.plot(x_hist_vals, baseline + 2 * poisson_std,
                         color='#fab387', lw=1.2, ls='--', alpha=0.85, label='2σ')

        # Posterior mean Weibull baseline
        alpha_mean = float(alpha_samples.mean())
        beta_mean  = float(beta_samples.mean())
        method_lbl = posterior.get('method', 'mcmc')
        fit_lbl    = (f"Weibull MCMC  α={alpha_mean:.2f}, "
                      f"β={beta_mean/div:.0f} {xlabel.split()[0].lower()}")
        if method_lbl == 'mle_fallback':
            fit_lbl = fit_lbl.replace('MCMC', 'MLE')
        ax_hist.plot(x_hist_vals, baseline,
                     color=INFO, lw=2.2, label=fit_lbl)

        # Observed counts
        ax_hist.plot(x_hist_vals, counts,
                     color=TEXT, lw=1.8, alpha=0.92, label='Registreret')

        # Yellow fill where observed exceeds 2σ threshold
        if show_2sigma:
            over2 = counts > (baseline + 2 * poisson_std)
            if over2.any():
                ax_hist.fill_between(x_hist_vals, baseline + 2 * poisson_std, counts,
                                     where=over2, alpha=0.30,
                                     color='#f9e2af', label='Over tærskel')

        ax_hist.set_ylabel('Antal kasseret', color=TEXT)
        ax_hist.tick_params(axis='y', labelcolor=TEXT)
        ax_hist.set_facecolor('#13131f')
        for spine in ax_hist.spines.values():
            spine.set_edgecolor(BORDER)

        if ax is None:
            title   = f'{datasæt_navn} — {kassationsårsag}' if datasæt_navn else kassationsårsag
            pct_str = f'  ({100 * n_kd / total:.1f}% af datasæt)' if total else ''
            ax_hist.set_title(
                f'{title}\n{n_kd} produkter{pct_str}\nKassations-profil (Overdødelighed)',
                color=TEXT, fontsize=11)
        else:
            ax_hist.set_title('Kassations-profil (Overdødelighed)',
                               color=TEXT, fontsize=10, pad=8)

        if log_y_hist:
            ax_hist.set_yscale('log')

        # Survival curve (twin y-axis) — optional
        if show_survival:
            ax_surv       = ax_hist.twinx()
            x_sorted      = np.sort(x_data)
            survival_prob = 100 * (1 - np.arange(1, len(x_sorted) + 1) / len(x_sorted))
            ax_surv.plot(x_sorted, survival_prob, color=SUCCESS, lw=2.0, label='Overlevelse (%)')
            ax_surv.set_ylabel('Overlevelse (%)', color=SUCCESS)
            ax_surv.tick_params(axis='y', labelcolor=SUCCESS)
            ax_surv.set_ylim(0, 105)
            for spine in ax_surv.spines.values():
                spine.set_edgecolor(BORDER)
            lines_1, labels_1 = ax_hist.get_legend_handles_labels()
            lines_2, labels_2 = ax_surv.get_legend_handles_labels()
            ax_hist.legend(lines_1 + lines_2, labels_1 + labels_2,
                           loc='upper right', fontsize=8,
                           facecolor=PANEL_BG, edgecolor=BORDER,
                           labelcolor=TEXT, ncol=2)
        else:
            ax_hist.legend(loc='upper right', fontsize=8,
                           facecolor=PANEL_BG, edgecolor=BORDER, labelcolor=TEXT)

        ax_hist.set_xlabel(xlabel, color=SUBTEXT)
        ax_hist.set_xlim(x_min, x_max)
        ax_hist.grid(True, alpha=0.25, linestyle='--', color=BORDER)
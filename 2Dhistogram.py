"""
histogram_app.py  —  Standalone 2D Histogram  (A/B dual-panel)
Run with:  python histogram_app.py
Requires:  pip install pandas numpy matplotlib openpyxl
"""

import os, sys, copy, json
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import LogNorm, Normalize

# ── Colours ────────────────────────────────────────────────────────────────────
BG      = '#1e1e2e'
BG2     = '#27273a'
BG3     = '#313145'
FG      = '#cdd6f4'
FG2     = '#a6adc8'
ACCENT  = '#89b4fa'
GREEN   = '#a6e3a1'
RED_W   = '#f38ba8'
YELLOW  = '#f9e2af'
PLOT_FG = '#cdd6f4'

# ── Config ─────────────────────────────────────────────────────────────────────
SCALE_CONFIG = {
    'Dage':    {'divisor': 1,      'label': 'Dage i cirkulation'},
    'Måneder': {'divisor': 30.437, 'label': 'Måneder i cirkulation'},
    'År':      {'divisor': 365.25, 'label': 'År i cirkulation'},
}
REF_LINE_DEFS = [
    (30.437 / 4, '4 vask/måned'),
    (30.437 / 2, '2 vask/måned'),
    (30.437,     '1 vask/måned'),
    (30.437 * 3, '1 vask/3 mdr.'),
    (30.437 * 6, '1 vask/6 mdr.'),
]
REF_COLORS      = ['#89dceb', '#89b4fa', '#fab387', '#f38ba8', '#a6e3a1']
RATIO_COL       = 'Vask per måned'
SAVE_DIR        = 'Saved Histograms'
DEFAULT_MAX_DAGE = int(8 * 365.25)
DEFAULT_MAX_VASK = 250

# ── Data ───────────────────────────────────────────────────────────────────────
def load_data():
    from dataloader import (
        samlet_df, skjorte_data, shorts_data, bukse_data, tshirt_data,
        langærmet_data, jakke_data, fleece_data, overall_data,
        forklæde_data, kittel_data, busseron_data, kokkejakke_data, andre_data
    )
    return {
        'Samlet':     samlet_df,      'Skjorte':    skjorte_data,
        'Shorts':     shorts_data,    'Bukser':     bukse_data,
        'T-shirt':    tshirt_data,    'Langærmet':  langærmet_data,
        'Jakke':      jakke_data,     'Fleece':     fleece_data,
        'Overall':    overall_data,   'Forklæde':   forklæde_data,
        'Kittel':     kittel_data,    'Busseron':   busseron_data,
        'Kokkejakke': kokkejakke_data,'Andet':      andre_data,
    }

# ── Tk style ───────────────────────────────────────────────────────────────────
def apply_style():
    s = ttk.Style()
    s.theme_use('clam')
    s.configure('TCombobox', fieldbackground=BG3, background=BG3,
                foreground=FG, selectbackground=ACCENT, selectforeground=BG,
                arrowcolor=FG, bordercolor=BG3, lightcolor=BG3, darkcolor=BG3)
    s.map('TCombobox', fieldbackground=[('readonly', BG3)],
          foreground=[('readonly', FG)])
    s.configure('TScrollbar', background=BG3, troughcolor=BG2,
                arrowcolor=FG, bordercolor=BG2)
    s.configure('TNotebook', background=BG, borderwidth=0)
    s.configure('TNotebook.Tab', background=BG3, foreground=FG2,
                padding=[12, 4], font=('Segoe UI', 9))
    s.map('TNotebook.Tab',
          background=[('selected', ACCENT)],
          foreground=[('selected', BG)])

# ── Helpers ────────────────────────────────────────────────────────────────────
def mk_lbl(parent, text, size=9, bold=False, color=None):
    f = ('Segoe UI', size, 'bold') if bold else ('Segoe UI', size)
    return tk.Label(parent, text=text, bg=BG2, fg=color or FG2, font=f, anchor='w')

def sep(parent):
    tk.Frame(parent, bg=BG3, height=1).pack(fill='x', pady=(8, 2))

def section_hdr(parent, text):
    sep(parent)
    mk_lbl(parent, text, size=10, bold=True, color=FG).pack(fill='x', padx=8, pady=(2, 4))

def flat_btn(parent, text, command, bg=BG3, fg=FG):
    return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                     font=('Segoe UI', 9), relief='flat', bd=0,
                     activebackground=ACCENT, activeforeground=BG,
                     cursor='hand2', padx=10, pady=4)

def toggle_btn(parent, text, command, bg=BG3, fg=FG):
    """Returns a button that visually toggles; caller manages state."""
    return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                     font=('Segoe UI', 9, 'bold'), relief='flat', bd=0,
                     activebackground=ACCENT, activeforeground=BG,
                     cursor='hand2', padx=10, pady=4)

# ── LabeledSlider ──────────────────────────────────────────────────────────────
class LabeledSlider(tk.Frame):
    def __init__(self, parent, label, var, from_, to, resolution=1, command=None):
        super().__init__(parent, bg=BG2)
        self._lbl_widget = mk_lbl(self, label, size=8)
        self._lbl_widget.pack(anchor='w', padx=8)
        row = tk.Frame(self, bg=BG2)
        row.pack(fill='x', padx=8, pady=1)
        self._val_lbl = tk.Label(row, width=7, anchor='e', bg=BG3, fg=ACCENT,
                                  font=('Segoe UI', 8))
        self._val_lbl.pack(side=tk.RIGHT, padx=(4, 0))
        self._cmd = command
        self.sl = tk.Scale(row, from_=from_, to=to, variable=var,
                           orient='horizontal', resolution=resolution,
                           bg=BG2, fg=FG2, troughcolor=BG3,
                           activebackground=ACCENT, highlightthickness=0,
                           sliderlength=14, width=10, showvalue=False,
                           command=self._on_change)
        self.sl.pack(side=tk.LEFT, fill='x', expand=True)
        self._update_label(var.get())

    def _on_change(self, v):
        self._update_label(v)
        if self._cmd:
            self._cmd(v)

    def reconfigure(self, from_, to, resolution, value=None, label=None):
        self.sl.config(from_=from_, to=to, resolution=resolution)
        if value is not None:
            self.sl.set(value)
        if label is not None:
            self._lbl_widget.config(text=label)

    def _update_label(self, v):
        try:
            val = float(v)
            self._val_lbl.config(
                text=f'{val:.2f}' if (val != int(val) and abs(val) < 100) else str(int(val)))
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# GraphPanel — one self-contained panel (controls + axes)
# ══════════════════════════════════════════════════════════════════════════════
class GraphPanel:
    """Encapsulates all state and widgets for one histogram panel (A or B)."""

    def __init__(self, parent_ctrl, parent_plot, data, letter, on_change_cb=None):
        self.data        = data
        self.letter      = letter
        self._colorbar   = None
        self._redraw_job = None
        self._dage_div   = 1.0
        self._on_change_cb = on_change_cb   # called after any local redraw (for sync)

        self._build_controls(parent_ctrl)
        self._build_plot(parent_plot)
        self._on_dataset()

    # ── Controls ───────────────────────────────────────────────────────────────
    def _build_controls(self, parent):
        # Scrollable canvas
        cv = tk.Canvas(parent, bg=BG2, highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient='vertical', command=cv.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._panel = tk.Frame(cv, bg=BG2)
        cv.create_window((0, 0), window=self._panel, anchor='nw', width=280)
        self._panel.bind('<Configure>', lambda e: cv.configure(
            scrollregion=cv.bbox('all')))
        cv.configure(yscrollcommand=sb.set)
        cv.bind_all(f'<MouseWheel>', lambda e: cv.yview_scroll(
            int(-1*(e.delta/120)), 'units'))

        p = self._panel

        # ── Load ──────────────────────────────────────────────────────────────
        section_hdr(p, f"Graf {self.letter} — Indlæs")
        self.load_var = tk.StringVar()
        self.load_cb  = ttk.Combobox(p, textvariable=self.load_var, state='readonly')
        self.load_cb.pack(fill='x', padx=8, pady=4)
        row_l = tk.Frame(p, bg=BG2)
        row_l.pack(fill='x', padx=8, pady=2)
        flat_btn(row_l, '📂  Indlæs', self._do_load,
                 bg='#ffffff', fg='black').pack(side=tk.LEFT, padx=2)
        flat_btn(row_l, '🗑  Slet', self._do_delete,
                 bg='#ffffff', fg='black').pack(side=tk.LEFT, padx=2)

        # ── Dataset ───────────────────────────────────────────────────────────
        section_hdr(p, "Datasæt")
        self.ds_var = tk.StringVar(value=list(self.data.keys())[0])
        ds_cb = ttk.Combobox(p, textvariable=self.ds_var,
                              values=list(self.data.keys()), state='readonly')
        ds_cb.pack(fill='x', padx=8, pady=2)
        ds_cb.bind('<<ComboboxSelected>>', lambda e: self._on_dataset())

        mk_lbl(p, "Kategorier  (Ctrl+klik)", size=8).pack(fill='x', padx=8, pady=(6, 1))
        self.kat_lb = tk.Listbox(p, selectmode=tk.MULTIPLE, height=4,
                                  bg=BG3, fg=FG, selectbackground=ACCENT,
                                  selectforeground=BG, exportselection=False,
                                  font=('Segoe UI', 9), relief='flat', highlightthickness=0)
        self.kat_lb.pack(fill='x', padx=8, pady=2)
        self.kat_lb.bind('<<ListboxSelect>>',
                          lambda e: (self._refresh_arsager(), self.schedule_redraw()))
        kbr = tk.Frame(p, bg=BG2)
        kbr.pack(fill='x', padx=8, pady=2)
        flat_btn(kbr, 'Vælg alle',    self._kat_all,
                 bg='#ffffff', fg='black').pack(side=tk.LEFT, padx=2)
        flat_btn(kbr, 'Fravælg alle', self._kat_none,
                 bg='#ffffff', fg='black').pack(side=tk.LEFT, padx=2)

        mk_lbl(p, "Kassationsårsag", size=8).pack(fill='x', padx=8, pady=(6, 1))
        self.ar_var = tk.StringVar(value='Alle')
        self.ar_cb  = ttk.Combobox(p, textvariable=self.ar_var, state='readonly')
        self.ar_cb.pack(fill='x', padx=8, pady=2)
        self.ar_cb.bind('<<ComboboxSelected>>', lambda e: self.schedule_redraw())

        # ── Scale ─────────────────────────────────────────────────────────────
        section_hdr(p, "X-akse skala")
        sf = tk.Frame(p, bg=BG2)
        sf.pack(fill='x', padx=8)
        self.skala_var = tk.StringVar(value='Dage')
        for opt in ['Dage', 'Måneder', 'År']:
            tk.Radiobutton(sf, text=opt, variable=self.skala_var, value=opt,
                           bg=BG2, fg=FG, selectcolor=BG3,
                           activebackground=BG2, activeforeground=FG,
                           font=('Segoe UI', 9),
                           command=self._on_skala_change).pack(side=tk.LEFT, padx=6)

        # ── Bins + log ────────────────────────────────────────────────────────
        section_hdr(p, "Bins & Farveskala")
        self.bins_var = tk.IntVar(value=60)
        LabeledSlider(p, "Antal bins", self.bins_var, 5, 80,
                      command=lambda v: self.schedule_redraw()).pack(fill='x')
        self.log_var = tk.BooleanVar(value=True)
        tk.Checkbutton(p, text='Logaritmisk farveskala', variable=self.log_var,
                       bg=BG2, fg=FG, selectcolor=BG3, activebackground=BG2,
                       activeforeground=FG, font=('Segoe UI', 9),
                       command=self.schedule_redraw).pack(anchor='w', padx=8, pady=4)

        # ── Axis ranges ───────────────────────────────────────────────────────
        section_hdr(p, "Aksegrænser")
        self._dage_min  = tk.IntVar(value=0)
        self._dage_max  = tk.IntVar(value=DEFAULT_MAX_DAGE)
        self._vask_min  = tk.IntVar(value=0)
        self._vask_max  = tk.IntVar(value=DEFAULT_MAX_VASK)
        self._ratio_min = tk.DoubleVar(value=0.0)
        self._ratio_max = tk.DoubleVar(value=4.5)

        self._sl_dage_min = LabeledSlider(p, 'Min levetid (dage)', self._dage_min,
                                           0, DEFAULT_MAX_DAGE, 1,
                                           command=lambda v: self.schedule_redraw())
        self._sl_dage_min.pack(fill='x', pady=1)
        self._sl_dage_max = LabeledSlider(p, 'Max levetid (dage)', self._dage_max,
                                           0, DEFAULT_MAX_DAGE, 1,
                                           command=lambda v: self.schedule_redraw())
        self._sl_dage_max.pack(fill='x', pady=1)

        for label, var, mn, mx, res in [
            ('Min vask',      self._vask_min,  0, 500, 1),
            ('Max vask',      self._vask_max,  0, 500, 1),
            ('Min vask/mdr.', self._ratio_min, 0, 4.5, 0.05),
            ('Max vask/mdr.', self._ratio_max, 0, 4.5, 0.05),
        ]:
            LabeledSlider(p, label, var, mn, mx, res,
                          command=lambda v: self.schedule_redraw()).pack(fill='x', pady=1)

        # ── Reference lines ───────────────────────────────────────────────────
        section_hdr(p, "Referencelinjer")
        self.ref_vars = {}
        for i, (_, rlbl) in enumerate(REF_LINE_DEFS):
            var = tk.BooleanVar(value=False)
            self.ref_vars[rlbl] = var
            rf = tk.Frame(p, bg=BG2)
            rf.pack(fill='x', padx=8, pady=1)
            tk.Checkbutton(rf, variable=var, bg=BG2, selectcolor=BG3,
                           activebackground=BG2,
                           command=self.schedule_redraw).pack(side=tk.LEFT)
            tk.Label(rf, text='━', fg=REF_COLORS[i], bg=BG2,
                     font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)
            tk.Label(rf, text=rlbl, bg=BG2, fg=FG,
                     font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=4)

        # ── Save ──────────────────────────────────────────────────────────────
        section_hdr(p, "Gem graf")
        mk_lbl(p, "Mappenavn (valgfrit)", size=8).pack(fill='x', padx=8)
        self.folder_var = tk.StringVar()
        tk.Entry(p, textvariable=self.folder_var, bg=BG3, fg=FG,
                 insertbackground=FG, relief='flat', font=('Segoe UI', 9),
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BG3).pack(fill='x', padx=8, pady=4)
        row_s = tk.Frame(p, bg=BG2)
        row_s.pack(fill='x', padx=8, pady=2)
        flat_btn(row_s, '💾  Gem', self._do_save,
                 bg='#ffffff', fg='black').pack(side=tk.LEFT, padx=2)
        flat_btn(row_s, '📄  CSV', self._do_csv,
                 bg='#ffffff', fg='black').pack(side=tk.LEFT, padx=2)

        self.status = tk.Label(p, text='', bg=BG2, fg=GREEN,
                                font=('Segoe UI', 8), wraplength=260, justify='left')
        self.status.pack(fill='x', padx=8, pady=(4, 20))
        self._refresh_saved()

    # ── Plot area ──────────────────────────────────────────────────────────────
    def _build_plot(self, parent):
        self.fig = plt.Figure(facecolor='#1e1e2e')
        self.ax  = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1e1e2e')
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # ── Data helpers ───────────────────────────────────────────────────────────
    def _on_dataset(self):
        df   = self.data[self.ds_var.get()]
        kats = sorted(df['Kategori'].dropna().unique()) if 'Kategori' in df.columns else []
        self.kat_lb.delete(0, tk.END)
        for k in kats:
            self.kat_lb.insert(tk.END, k)
        self.kat_lb.select_set(0, tk.END)
        self._refresh_arsager()
        self.schedule_redraw()

    def _refresh_arsager(self):
        df = self.filtered_df()
        opts = ['Alle'] + sorted(df['Kassationsårsag (ui)'].dropna().unique())
        self.ar_cb['values'] = opts
        if self.ar_var.get() not in opts:
            self.ar_var.set('Alle')

    def _kat_all(self):
        self.kat_lb.select_set(0, tk.END)
        self._refresh_arsager(); self.schedule_redraw()

    def _kat_none(self):
        self.kat_lb.selection_clear(0, tk.END)
        self._refresh_arsager(); self.schedule_redraw()

    def filtered_df(self):
        df   = self.data[self.ds_var.get()]
        sel  = [self.kat_lb.get(i) for i in self.kat_lb.curselection()]
        all_ = list(self.kat_lb.get(0, tk.END))
        if sel and sel != all_ and 'Kategori' in df.columns:
            df = df[df['Kategori'].isin(sel)]
        return df

    def get_kd(self, df=None):
        if df is None:
            df = self.filtered_df()
        ar = self.ar_var.get()
        kd = df if ar == 'Alle' else df[df['Kassationsårsag (ui)'] == ar]
        kd = kd[(kd['Dage i cirkulation'] >= self._dage_min.get() * self._dage_div) &
                (kd['Dage i cirkulation'] <= self._dage_max.get() * self._dage_div) &
                (kd['Total antal vask']   >= self._vask_min.get()) &
                (kd['Total antal vask']   <= self._vask_max.get())]
        if RATIO_COL in kd.columns:
            kd = kd[(kd[RATIO_COL] >= self._ratio_min.get()) &
                    (kd[RATIO_COL] <= self._ratio_max.get())]
        return kd

    # ── Skala ─────────────────────────────────────────────────────────────────
    def _on_skala_change(self):
        self._update_dage_sliders()
        self.schedule_redraw()

    def _update_dage_sliders(self):
        skala = self.skala_var.get()
        div   = SCALE_CONFIG[skala]['divisor']
        mx    = DEFAULT_MAX_DAGE / div
        res   = 0.1 if skala == 'År' else 1
        cur_min = self._dage_min.get() / div
        cur_max = self._dage_max.get() / div
        self._dage_div = div
        self._sl_dage_min.reconfigure(0, mx, res, round(cur_min, 2),
                                       label=f'Min levetid ({skala.lower()})')
        self._sl_dage_max.reconfigure(0, mx, res, round(cur_max, 2),
                                       label=f'Max levetid ({skala.lower()})')

    # ── Debounce ──────────────────────────────────────────────────────────────
    def schedule_redraw(self, *_):
        if self._redraw_job is not None:
            self._panel.after_cancel(self._redraw_job)
        self._redraw_job = self._panel.after(120, self._do_redraw)

    def _do_redraw(self):
        self._redraw_job = None
        self.redraw()
        if self._on_change_cb:
            self._on_change_cb(self)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def redraw(self):
        if self._colorbar is not None:
            try:
                self._colorbar.remove()
            except Exception:
                pass
            self._colorbar = None

        self.ax.cla()
        fc = '#1e1e2e'
        self.ax.set_facecolor(fc)

        df    = self.filtered_df()
        kd    = self.get_kd(df)
        skala = self.skala_var.get()
        div   = SCALE_CONFIG[skala]['divisor']
        xlabel = SCALE_CONFIG[skala]['label']
        x_min = self._dage_min.get()
        x_max = self._dage_max.get()
        v_min = float(self._vask_min.get())
        v_max = float(self._vask_max.get())

        if len(kd) == 0:
            self.ax.text(0.5, 0.5, 'Ingen data', ha='center', va='center',
                         transform=self.ax.transAxes, fontsize=13, color='#666688')
        else:
            cmap = copy.copy(plt.colormaps['YlOrRd'])
            cmap.set_bad(fc); cmap.set_under(fc)
            norm = LogNorm(vmin=0.5) if self.log_var.get() else Normalize(vmin=0.5)
            h = self.ax.hist2d(
                kd['Dage i cirkulation'] / div, kd['Total antal vask'],
                bins=self.bins_var.get(), cmap=cmap, norm=norm,
                range=[[x_min, x_max], [v_min, v_max]])
            self._colorbar = self.fig.colorbar(h[3], ax=self.ax, pad=0.01)
            self._colorbar.set_label(
                'Antal (log)' if self.log_var.get() else 'Antal',
                color=PLOT_FG, fontsize=8)
            self._colorbar.ax.yaxis.set_tick_params(color=PLOT_FG)
            plt.setp(self._colorbar.ax.yaxis.get_ticklabels(), color=PLOT_FG)
            self._colorbar.ax.set_facecolor(fc)

        # Reference lines
        active = [l for l, v in self.ref_vars.items() if v.get()]
        if active:
            xs = np.linspace(x_min, x_max, 300)
            handles = []
            for i, (interval_days, rlbl) in enumerate(REF_LINE_DEFS):
                if rlbl in active:
                    line, = self.ax.plot(xs, (xs * div) / interval_days,
                                         color=REF_COLORS[i], lw=1.5, ls='--',
                                         alpha=0.9, label=rlbl)
                    handles.append(line)
            if handles:
                self.ax.legend(handles=handles, fontsize=7, loc='upper left',
                                facecolor=BG2, edgecolor=BG3, labelcolor=FG)

        # Percentile lines
        if len(kd) > 0:
            col = kd['Dage i cirkulation']
            for val, plbl, color, y_frac in [
                (col.quantile(0.25), '25%',    '#89b4fa', 0.88),
                (col.median(),       'Median', '#cba6f7', 0.96),
                (col.quantile(0.75), '75%',    '#f38ba8', 0.80),
            ]:
                vx = val / div
                if x_min < vx < x_max:
                    self.ax.axvline(vx, color=color, lw=1.5, ls=':', alpha=0.95)
                    self.ax.text(vx, v_max * y_frac,
                                 f'{plbl}\n{val/365.25:.1f}y\n({val:.0f}d)',
                                 color=color, fontsize=7, ha='center', va='top',
                                 bbox=dict(boxstyle='round,pad=0.2',
                                           fc=BG2, alpha=0.85, ec='none'))

        # Axes
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#44446a')
        self.ax.tick_params(colors=PLOT_FG, which='both')
        self.ax.xaxis.label.set_color(PLOT_FG)
        self.ax.yaxis.label.set_color(PLOT_FG)
        self.ax.set_xlabel(xlabel, fontsize=9)
        self.ax.set_ylabel('Total antal vask', fontsize=9)
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(v_min, v_max)

        sel_kats = [self.kat_lb.get(i) for i in self.kat_lb.curselection()]
        all_kats = list(self.kat_lb.get(0, tk.END))
        navn = self.ds_var.get()
        if sel_kats and sel_kats != all_kats:
            navn = f"{navn}({'+'.join(sel_kats)})"
        ar  = self.ar_var.get()
        pct = f'  {100*len(kd)/len(df):.1f}%' if len(df) > 0 else ''
        self.ax.set_title(f'Graf {self.letter}: {navn} · {ar}\n{len(kd):,} produkter{pct}',
                           color=PLOT_FG, fontsize=10, fontweight='bold', pad=8)

        self.fig.tight_layout()
        self.canvas.draw_idle()

    # ── Save helpers ──────────────────────────────────────────────────────────
    def _make_name(self):
        raw = self.folder_var.get().strip()
        return (raw.replace(' ', '_') if raw else
                f"{self.ds_var.get()}_{self.ar_var.get()}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}".replace(' ', '_'))

    def _do_save(self):
        folder = self._make_name()
        subdir = os.path.join(SAVE_DIR, folder)
        os.makedirs(subdir, exist_ok=True)
        self.fig.savefig(os.path.join(subdir, 'histogram.jpeg'), dpi=150,
                         bbox_inches='tight', facecolor=self.fig.get_facecolor())
        s = {
            'datasæt': self.ds_var.get(), 'kassationsårsag': self.ar_var.get(),
            'kategorier': [self.kat_lb.get(i) for i in self.kat_lb.curselection()],
            'skala': self.skala_var.get(), 'bins': self.bins_var.get(),
            'log_color': self.log_var.get(),
            'min_dage': self._dage_min.get(), 'max_dage': self._dage_max.get(),
            'min_vask': self._vask_min.get(), 'max_vask': self._vask_max.get(),
            'min_ratio': self._ratio_min.get(), 'max_ratio': self._ratio_max.get(),
            'ref_lines': [l for l, v in self.ref_vars.items() if v.get()],
            'gemt': datetime.now().isoformat(),
        }
        with open(os.path.join(subdir, 'settings.json'), 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        self._refresh_saved()
        self.status.config(text=f'✔ Gemt: {folder}/', fg=GREEN)

    def _do_csv(self):
        kd   = self.get_kd()
        path = os.path.join(SAVE_DIR, f'{self._make_name()}.csv')
        os.makedirs(SAVE_DIR, exist_ok=True)
        kd.to_csv(path, index=False, encoding='utf-8-sig')
        self.status.config(text=f'✔ CSV: {os.path.basename(path)} ({len(kd):,})', fg=GREEN)

    def _do_load(self):
        folder = self.load_var.get()
        if not folder:
            return
        try:
            with open(os.path.join(SAVE_DIR, folder, 'settings.json'), encoding='utf-8') as f:
                s = json.load(f)
        except Exception as e:
            self.status.config(text=f'Fejl: {e}', fg=RED_W); return

        if s.get('datasæt') in self.data:
            self.ds_var.set(s['datasæt']); self._on_dataset()
        if s.get('kategorier'):
            all_k = list(self.kat_lb.get(0, tk.END))
            self.kat_lb.selection_clear(0, tk.END)
            for i, k in enumerate(all_k):
                if k in s['kategorier']:
                    self.kat_lb.selection_set(i)
        for attr, key in [('ar_var', 'kassationsårsag'), ('skala_var', 'skala')]:
            if s.get(key):
                getattr(self, attr).set(s[key])
        if s.get('bins'):
            self.bins_var.set(s['bins'])
        if s.get('log_color') is not None:
            self.log_var.set(s['log_color'])
        for var, key in [(self._dage_min, 'min_dage'), (self._dage_max, 'max_dage'),
                          (self._vask_min, 'min_vask'), (self._vask_max, 'max_vask'),
                          (self._ratio_min, 'min_ratio'), (self._ratio_max, 'max_ratio')]:
            if s.get(key) is not None:
                var.set(s[key])
        for lbl_, v in self.ref_vars.items():
            v.set(lbl_ in s.get('ref_lines', []))
        self._update_dage_sliders()
        self.redraw()
        self.status.config(text=f'✔ Indlæst: {folder}', fg=GREEN)

    def _do_delete(self):
        folder = self.load_var.get()
        if not folder:
            return
        if messagebox.askyesno('Slet', f'Slet "{folder}"?'):
            import shutil
            shutil.rmtree(os.path.join(SAVE_DIR, folder), ignore_errors=True)
            self._refresh_saved()
            self.status.config(text=f'✔ Slettet: {folder}', fg=YELLOW)

    def _refresh_saved(self):
        if not os.path.isdir(SAVE_DIR):
            self.load_cb['values'] = []; return
        folders = [f for f in sorted(os.listdir(SAVE_DIR))
                   if os.path.isfile(os.path.join(SAVE_DIR, f, 'settings.json'))]
        self.load_cb['values'] = folders

    # ── Sync interface — expose vars for external sync ─────────────────────────
    def get_sync_vars(self):
        """Return the widgets that the main sync button controls."""
        return {
            'skala':     self.skala_var,
            'min_dage':  self._dage_min,
            'max_dage':  self._dage_max,
            'min_vask':  self._vask_min,
            'max_vask':  self._vask_max,
        }

    def get_ratio_vars(self):
        return {'min_ratio': self._ratio_min, 'max_ratio': self._ratio_max}

    def apply_sync_vars(self, vals: dict):
        """Push a dict of {key: value} into this panel without triggering full on_dataset."""
        mapping = {
            'skala':     self.skala_var,
            'min_dage':  self._dage_min,
            'max_dage':  self._dage_max,
            'min_vask':  self._vask_min,
            'max_vask':  self._vask_max,
            'min_ratio': self._ratio_min,
            'max_ratio': self._ratio_max,
        }
        for k, v in vals.items():
            if k in mapping:
                try:
                    mapping[k].set(v)
                except Exception:
                    pass
        if 'skala' in vals:
            self._update_dage_sliders()


# ══════════════════════════════════════════════════════════════════════════════
# Main App
# ══════════════════════════════════════════════════════════════════════════════
class HistogramApp(tk.Tk):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self._syncing      = False   # guard against recursive sync
        self._main_sync_on = False
        self._ratio_sync_on = False

        apply_style()
        self.title("2D Histogram — Kassationsanalyse")
        self.configure(bg=BG)
        self.state('zoomed')
        self._build_ui()

    def _build_ui(self):
        # ── Top toolbar ───────────────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=BG2, height=44)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text='2D Histogram  —  Kassationsanalyse',
                 bg=BG2, fg=FG, font=('Segoe UI', 11, 'bold')).pack(
            side=tk.LEFT, padx=16, pady=8)

        # View toggle
        self._view_var = tk.StringVar(value='2 Grafer')
        view_fr = tk.Frame(toolbar, bg=BG2)
        view_fr.pack(side=tk.LEFT, padx=16)
        tk.Label(view_fr, text='Vis:', bg=BG2, fg=FG2,
                 font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=4)
        for opt in ['Graf A', 'Graf B', '2 Grafer']:
            tk.Radiobutton(view_fr, text=opt, variable=self._view_var, value=opt,
                           bg=BG2, fg=FG, selectcolor=BG3,
                           activebackground=BG2, activeforeground=FG,
                           font=('Segoe UI', 9),
                           command=self._on_view_change).pack(side=tk.LEFT, padx=4)

        # Sync buttons (right side)
        sync_fr = tk.Frame(toolbar, bg=BG2)
        sync_fr.pack(side=tk.RIGHT, padx=16)

        self._ratio_sync_btn = tk.Button(
            sync_fr, text='🔗  Synk ratio', command=self._toggle_ratio_sync,
            bg=BG3, fg=FG2, font=('Segoe UI', 9), relief='flat',
            activebackground=ACCENT, cursor='hand2', padx=10, pady=4)
        self._ratio_sync_btn.pack(side=tk.RIGHT, padx=4)

        self._main_sync_btn = tk.Button(
            sync_fr, text='🔗  Synkroniser skala', command=self._toggle_main_sync,
            bg=BG3, fg=FG2, font=('Segoe UI', 9), relief='flat',
            activebackground=ACCENT, cursor='hand2', padx=10, pady=4)
        self._main_sync_btn.pack(side=tk.RIGHT, padx=4)

        # ── Main content area ─────────────────────────────────────────────────
        self._content = tk.Frame(self, bg=BG)
        self._content.pack(fill=tk.BOTH, expand=True)

        # Panel A — left controls
        self._ctrl_a = tk.Frame(self._content, bg=BG2, width=295)
        self._ctrl_a.pack(side=tk.LEFT, fill=tk.Y)
        self._ctrl_a.pack_propagate(False)

        # Panel B — right controls
        self._ctrl_b = tk.Frame(self._content, bg=BG2, width=295)
        self._ctrl_b.pack(side=tk.RIGHT, fill=tk.Y)
        self._ctrl_b.pack_propagate(False)

        # Plot areas
        self._plots = tk.Frame(self._content, bg=BG)
        self._plots.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._plot_a_frame = tk.Frame(self._plots, bg=BG)
        self._plot_b_frame = tk.Frame(self._plots, bg=BG)
        self._plot_a_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._plot_b_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Build panels
        self.panel_a = GraphPanel(self._ctrl_a, self._plot_a_frame, self.data,
                                   'A', on_change_cb=self._on_panel_changed)
        self.panel_b = GraphPanel(self._ctrl_b, self._plot_b_frame, self.data,
                                   'B', on_change_cb=self._on_panel_changed)

        self._on_view_change()

    # ── View toggle ───────────────────────────────────────────────────────────
    def _on_view_change(self):
        v = self._view_var.get()
        # Show/hide control panels and plot frames
        if v == 'Graf A':
            self._ctrl_b.pack_forget()
            self._plot_b_frame.pack_forget()
            if not self._ctrl_a.winfo_ismapped():
                self._ctrl_a.pack(side=tk.LEFT, fill=tk.Y)
            if not self._plot_a_frame.winfo_ismapped():
                self._plot_a_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        elif v == 'Graf B':
            self._ctrl_a.pack_forget()
            self._plot_a_frame.pack_forget()
            if not self._ctrl_b.winfo_ismapped():
                self._ctrl_b.pack(side=tk.RIGHT, fill=tk.Y)
            if not self._plot_b_frame.winfo_ismapped():
                self._plot_b_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        else:  # 2 Grafer
            for w in [self._ctrl_a, self._ctrl_b,
                      self._plot_a_frame, self._plot_b_frame]:
                if not w.winfo_ismapped():
                    pass
            # Re-pack everything cleanly
            self._ctrl_a.pack_forget()
            self._ctrl_b.pack_forget()
            self._plot_a_frame.pack_forget()
            self._plot_b_frame.pack_forget()
            self._ctrl_a.pack(side=tk.LEFT, fill=tk.Y)
            self._plot_a_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self._plot_b_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self._ctrl_b.pack(side=tk.LEFT, fill=tk.Y)

    # ── Sync logic ────────────────────────────────────────────────────────────
    def _toggle_main_sync(self):
        self._main_sync_on = not self._main_sync_on
        if self._main_sync_on:
            self._main_sync_btn.config(bg=ACCENT, fg=BG,
                                        text='🔗  Synkroniseret')
            # Immediately push A → B
            self._push_sync(self.panel_a, self.panel_b, include_ratio=False)
        else:
            self._main_sync_btn.config(bg=BG3, fg=FG2,
                                        text='🔗  Synkroniser skala')

    def _toggle_ratio_sync(self):
        self._ratio_sync_on = not self._ratio_sync_on
        if self._ratio_sync_on:
            self._ratio_sync_btn.config(bg=ACCENT, fg=BG,
                                         text='🔗  Ratio synk. til')
            self._push_sync(self.panel_a, self.panel_b, include_ratio=True,
                             only_ratio=True)
        else:
            self._ratio_sync_btn.config(bg=BG3, fg=FG2,
                                         text='🔗  Synk ratio')

    def _push_sync(self, source, target, include_ratio=False, only_ratio=False):
        """Copy values from source panel to target panel."""
        if self._syncing:
            return
        self._syncing = True
        try:
            vals = {}
            if not only_ratio:
                vals.update(source.get_sync_vars())
                vals = {k: v.get() for k, v in vals.items()}
            if include_ratio or only_ratio:
                ratio = {k: v.get() for k, v in source.get_ratio_vars().items()}
                vals.update(ratio)
            target.apply_sync_vars(vals)
            target.redraw()
        finally:
            self._syncing = False

    def _on_panel_changed(self, source_panel):
        """Called after any panel redraws — propagate sync if active."""
        if self._syncing:
            return
        if self._main_sync_on or self._ratio_sync_on:
            target = self.panel_b if source_panel is self.panel_a else self.panel_a
            self._push_sync(source_panel, target,
                             include_ratio=self._ratio_sync_on)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    try:
        data = load_data()
    except Exception as e:
        import tkinter.messagebox as mb
        mb.showerror('Import fejl',
                      f'Kunne ikke importere dataloader:\n{e}\n\n'
                      'Sørg for at dataloader.py ligger i samme mappe.')
        sys.exit(1)
    app = HistogramApp(data)
    app.mainloop()
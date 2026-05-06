# data_cache.py — data loading with pickle cache
# ─────────────────────────────────────────────────────────────────────────────
# First run:  imports dataloader, saves data_cache.pkl  (~slow, once only)
# Later runs: reads pickle directly                      (~instant)
#
# Call load_data(force_refresh=True) to bust the cache and re-run dataloader.

import os
import pickle
import numpy as np

from config import CACHE_FILE, DATASET_MAP


# ── Internal helpers ───────────────────────────────────────────────────────────

def _load_from_dataloader() -> dict:
    """Import dataloader module and return a plain dict of DataFrames."""
    from dataloader import samlet_df as _s
    from dataloader import (
        skjorte_data as _sk, shorts_data as _sh, bukse_data as _bu,
        tshirt_data as _ts, langærmet_data as _la, jakke_data as _ja,
        fleece_data as _fl, overall_data as _ov, forklæde_data as _fo,
        kittel_data as _ki, busseron_data as _bs,
        kokkejakke_data as _ko, andre_data as _an,
    )
    return dict(
        samlet_df=_s,       skjorte_data=_sk,    shorts_data=_sh,
        bukse_data=_bu,     tshirt_data=_ts,     langærmet_data=_la,
        jakke_data=_ja,     fleece_data=_fl,     overall_data=_ov,
        forklæde_data=_fo,  kittel_data=_ki,     busseron_data=_bs,
        kokkejakke_data=_ko, andre_data=_an,
    )


def _apply_frames(frames: dict) -> None:
    """Push a frames dict into DATASET_MAP (shared global state)."""
    DATASET_MAP.update({
        'Samlet':     frames['samlet_df'],
        'Skjorte':    frames['skjorte_data'],
        'Shorts':     frames['shorts_data'],
        'Bukser':     frames['bukse_data'],
        'T-shirt':    frames['tshirt_data'],
        'Langærmet':  frames['langærmet_data'],
        'Jakke':      frames['jakke_data'],
        'Fleece':     frames['fleece_data'],
        'Overall':    frames['overall_data'],
        'Forklæde':   frames['forklæde_data'],
        'Kittel':     frames['kittel_data'],
        'Busseron':   frames['busseron_data'],
        'Kokkejakke': frames['kokkejakke_data'],
        'Andet':      frames['andre_data'],
    })


def _make_demo_frames() -> dict:
    """Generate synthetic data for demo / no-dataloader mode."""
    import pandas as pd
    rng = np.random.default_rng(42)

    def _df(n: int) -> 'pd.DataFrame':
        dage    = rng.integers(30, 2800, n)
        vask    = (dage / 365.25 * rng.uniform(10, 60, n)).astype(int)
        ratio   = vask / (dage / 30.437)
        årsager = rng.choice(['Slidt', 'Beskadiget', 'Forældet', 'Andet'], n)
        return pd.DataFrame({
            'Dage i cirkulation':   dage,
            'Total antal vask':     vask,
            'Vask per måned':       ratio,
            'Kassationsårsag (ui)': årsager,
        })

    return {
        'samlet_df':      _df(8000),
        'skjorte_data':   _df(1200), 'shorts_data':     _df(800),
        'bukse_data':     _df(900),  'tshirt_data':     _df(1100),
        'langærmet_data': _df(600),  'jakke_data':      _df(500),
        'fleece_data':    _df(400),  'overall_data':    _df(300),
        'forklæde_data':  _df(350),  'kittel_data':     _df(450),
        'busseron_data':  _df(250),  'kokkejakke_data': _df(200),
        'andre_data':     _df(700),
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def load_data(force_refresh: bool = False,
              status_cb=None) -> bool:
    """
    Load data into DATASET_MAP.

    Parameters
    ----------
    force_refresh : bool
        Skip cache and re-import from dataloader, then overwrite cache.
    status_cb : callable(str) | None
        Optional splash-screen status callback.

    Returns
    -------
    bool  — True if real data was loaded, False if demo mode was used.
    """
    def _s(msg: str) -> None:
        if status_cb:
            status_cb(msg)

    # ── 1. Try cache ───────────────────────────────────────────────────────────
    if not force_refresh and os.path.isfile(CACHE_FILE):
        _s("Indlæser cache…")
        try:
            with open(CACHE_FILE, 'rb') as f:
                frames = pickle.load(f)
            _apply_frames(frames)
            _s("Cache indlæst ✔")
            return True
        except Exception as e:
            print(f"Cache corrupt, reloading: {e}")

    # ── 2. Fresh load from dataloader ──────────────────────────────────────────
    try:
        _s("Første opstart: indlæser data fra dataloader…")
        frames = _load_from_dataloader()
        _apply_frames(frames)

        _s("Gemmer cache…")
        try:
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(frames, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"✓ Cache gemt: {CACHE_FILE}")
        except Exception as e:
            print(f"Cache-skrivning fejlede: {e}")

        _s("Klar!")
        return True

    except ImportError as e:
        # dataloader.py not found at all
        print(f"⚠  dataloader ikke fundet ({e}) — kører i DEMO-tilstand.")
        _s("DEMO-tilstand: genererer syntetisk data…")
        _apply_frames(_make_demo_frames())
        return False

    except Exception as e:
        # dataloader exists but crashed (bad file path, missing column, etc.)
        import traceback
        print("\n" + "="*60)
        print("DATALOADER FEJL — dette er hvorfor du ser demo-data:")
        print("="*60)
        traceback.print_exc()
        print("="*60 + "\n")
        _s(f"Dataloader fejl: {type(e).__name__}: {e}")

        # Give the user a moment to read the status before it disappears
        import time
        time.sleep(2)

        _s("DEMO-tilstand: genererer syntetisk data…")
        _apply_frames(_make_demo_frames())
        return False


def invalidate_cache() -> None:
    """Delete the data cache and all Weibull model caches."""
    if os.path.isfile(CACHE_FILE):
        os.remove(CACHE_FILE)
        print(f"✓ Data-cache slettet: {CACHE_FILE}")
    # Also clear Weibull fits — they are tied to the data so must be rebuilt
    try:
        from weibull_cache import invalidate_weibull_cache
        invalidate_weibull_cache()
    except ImportError:
        pass
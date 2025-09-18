# -*- coding: utf-8 -*-

"""
TvSkipIntro Add-on — Intro & Outro skipper with robust editing dialog
- Intro:
  * AutoSkip seeks to 'skip' once current time >= 'start'
  * Manual: opens CustomDialog; OK button jumps to 'skip'
- Outro (Restzeit):
  * Aktiv nur, wenn 15 <= outro <= 600 (Sekunden vor Ende)
  * Manuell: Dialog ~30s vor Schwelle
  * Auto: springt automatisch, sobald Restzeit <= Schwelle
- Dialog-Lock:
  * Nach Ja/Nein gesperrt, bis Folge/Episode wechselt oder Playback stoppt
- CustomDialog:
  * Erlaubt Bearbeiten von: skip, start, outro, Auto-Intro (auto), Auto-Outro (outro_auto)
"""

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import json
import os
import time
import re
import threading
import urllib.parse

# Custom outro window
try:
    from resources.lib.ui.outro_window import SkipOutroWindow
except Exception:
    SkipOutroWindow = None

# -------------------------
# Dialog-Lock (global window property)
# -------------------------

def _get_dialog_locked():
    try:
        w = xbmcgui.Window(10000)
        return (w.getProperty('tvskipintro_dialog_locked') or '0') == '1'
    except Exception:
        return False

def _set_dialog_locked(flag=True):
    try:
        w = xbmcgui.Window(10000)
        w.setProperty('tvskipintro_dialog_locked', '1' if flag else '0')
    except Exception:
        pass

def _lock_now():
    """Turn on dialog lock and remember timestamp."""
    try:
        w = xbmcgui.Window(10000)
        w.setProperty('tvskipintro_dialog_locked', '1')
        w.setProperty('tvskipintro_lock_since', str(int(time.time())))
    except Exception:
        pass

def _lock_elapsed_secs(default=0):
    try:
        w = xbmcgui.Window(10000)
        ts = int(w.getProperty('tvskipintro_lock_since') or '0')
        if ts <= 0:
            return default
        return max(0, int(time.time()) - ts)
    except Exception:
        return default

# -------------------------
# Transition helpers (no-ops if not used elsewhere)
# -------------------------

def _begin_transition():
    try:
        xbmcgui.Window(10000).setProperty('tvskipintro_transition', '1')
    except Exception:
        pass

def _end_transition():
    try:
        xbmcgui.Window(10000).setProperty('tvskipintro_transition', '0')
    except Exception:
        pass

def _in_transition():
    try:
        w = xbmcgui.Window(10000)
        return (w.getProperty('tvskipintro_transition') or '0') == '1'
    except Exception:
        return False

# -------------------------
# Addon / Pfade / Defaults
# -------------------------

addon = xbmcaddon.Addon()
_ = addon.getLocalizedString

def _safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        try:
            s = str(v).strip()
            if s.lstrip("-").isdigit():
                return int(s)
        except Exception:
            pass
    return default

addonInfo = addon.getAddonInfo
settings = addon.getSetting
profilePath = xbmcvfs.translatePath(addonInfo('profile'))
addonPath = xbmcvfs.translatePath(addonInfo('path'))
skipFile = os.path.join(profilePath, 'skipintro.json')

DEFAULT_SKIP_FALLBACK = 90
try:
    _ds = settings('default.skip')
    defaultSkip = int(_ds) if str(_ds).strip().lstrip("-").isdigit() else DEFAULT_SKIP_FALLBACK
except Exception:
    defaultSkip = DEFAULT_SKIP_FALLBACK

if not os.path.exists(profilePath):
    xbmcvfs.mkdir(profilePath)

# -------------------------
# Helper
# -------------------------

def strip_decorations_from_key(key):
    if not key:
        return ''
    base = re.sub(r'\s*\[[a-zA-Z]+:[^\]]+\]\s*$', '', key)
    base = re.sub(r'\s*\(\d{4}\)\s*$', '', base)
    return base.strip()

def normalize_year(year):
    try:
        if year is None:
            return ''
        y = str(year).strip()
        if len(y) >= 4:
            digits = re.findall(r"(\d{4})", y)
            return digits[0] if digits else ''
        return y if y.isdigit() and len(y) == 4 else ''
    except Exception:
        return ''

def read_json():
    try:
        with open(skipFile, 'r') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
        return data
    except Exception:
        return {}

def write_json(data):
    with open(skipFile, 'w') as f:
        json.dump(data, f, indent=2)

# --------- IDs & Jahr aus Plugins/Properties/URL ---------

TMDB_PROP_KEYS = ["tmdb_id","tmdbId","tmdbid","tmdb_show_id","themoviedb_id","tmdb"]
IMDB_PROP_KEYS = ["imdb_id","imdbId","imdbid","imdb","code"]
YEAR_PROP_KEYS = ["year","premiered","aired","firstaired","first_air_date","tvshow_year","show_year","release_date"]
YEAR_QS_KEYS = ["year","first_air_date","premiered","aired","release_date"]

def _read_videoplayer_prop(name):
    try:
        return xbmc.getInfoLabel(f"VideoPlayer.Property({name})")
    except Exception:
        return ""

def get_ids_from_player_properties():
    for k in TMDB_PROP_KEYS:
        val = _read_videoplayer_prop(k)
        if val and re.match(r"^\d+$", val):
            return ("tmdb", val)
    for k in IMDB_PROP_KEYS:
        val = _read_videoplayer_prop(k)
        if val and re.match(r"^(tt)?\d+$", val):
            if not val.startswith("tt"):
                val = "tt" + val
            return ("imdb", val)
    imdbnum = xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
    if imdbnum:
        imdbnum = imdbnum.strip()
        if imdbnum and re.match(r"^(tt)?\d+$", imdbnum):
            if not imdbnum.startswith("tt"):
                imdbnum = "tt" + imdbnum
            return ("imdb", imdbnum)
    return ("","")

def get_ids_from_playing_path():
    try:
        try:
            path = xbmc.Player().getPlayingFile()
        except Exception:
            path = xbmc.getInfoLabel("Player.FilenameAndPath")
        if not path:
            return ("","")
        parsed = urllib.parse.urlparse(path)
        qs = urllib.parse.parse_qs(parsed.query)
        for key in ["tmdb_id","tmdb","tmdbId","tmdb_show_id","tmdbid","show_tmdbid","tmdb_id_tv"]:
            if key in qs and qs[key]:
                val = qs[key][0]
                if val and re.match(r"^\d+$", val):
                    return ("tmdb", val)
        for key in ["imdb_id","imdb","imdbId","imdbid","code"]:
            if key in qs and qs[key]:
                val = qs[key][0]
                if val:
                    if not val.startswith("tt"):
                        val = "tt" + re.sub(r"^tt","", val)
                    return ("imdb", val)
    except Exception:
        pass
    return ("","")

def best_year_from_props_and_path():
    for k in YEAR_PROP_KEYS:
        v = _read_videoplayer_prop(k)
        if v:
            y = normalize_year(v)
            if y:
                return y
    try:
        path = xbmc.Player().getPlayingFile()
    except Exception:
        path = xbmc.getInfoLabel("Player.FilenameAndPath")
    if path:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        for k in YEAR_QS_KEYS:
            if k in qs and qs[k]:
                y = normalize_year(qs[k][0])
                if y:
                    return y
    y = xbmc.getInfoLabel("VideoPlayer.Premiered") or xbmc.getInfoLabel("VideoPlayer.Year")
    return normalize_year(y)

def get_series_identity_via_jsonrpc_or_plugin():
    title = xbmc.getInfoLabel("VideoPlayer.TVShowTitle").strip()

    uid_type, uid = get_ids_from_player_properties()
    if not uid:
        uid_type, uid = get_ids_from_playing_path()

    year = ""
    try:
        req = {"jsonrpc":"2.0","id":1,"method":"Player.GetItem",
               "params":{"playerid":1,"properties":["tvshowid","showtitle","year","premiered"]}}
        item = json.loads(xbmc.executeJSONRPC(json.dumps(req))).get("result",{}).get("item",{})
        title = (item.get("showtitle") or title or '').strip()
        y = item.get("year") or ""
        prem = item.get("premiered") or ""
        if not y and prem:
            y = prem[:4] if len(prem) >= 4 else ""

        tvshowid = item.get("tvshowid", -1)
        if isinstance(tvshowid, int) and tvshowid >= 0:
            req2 = {"jsonrpc":"2.0","id":2,"method":"VideoLibrary.GetTVShowDetails",
                    "params":{"tvshowid":tvshowid,"properties":["title","year","premiered","uniqueid"]}}
            details = json.loads(xbmc.executeJSONRPC(json.dumps(req2))).get("result",{}).get("tvshowdetails",{})
            y2 = details.get("year") or (details.get("premiered") or "")[:4]
            year = normalize_year(y2 or y)

            if not uid:
                unique = details.get("uniqueid") or {}
                for k in ("tmdb","tvdb","imdb"):
                    if unique.get(k):
                        uid = str(unique.get(k)); uid_type = k; break
            if not uid:
                uid = str(tvshowid); uid_type = "kodi"
        else:
            year = normalize_year(y or "")
    except Exception as e:
        xbmc.log(f"[TvSkipIntro][Identity] JSON-RPC failed: {e}", xbmc.LOGERROR)
        year = ""

    if not year:
        year = best_year_from_props_and_path()

    return title, year, uid, uid_type

def _get_playing_file():
    try:
        return xbmc.Player().getPlayingFile()
    except Exception:
        return xbmc.getInfoLabel("Player.FilenameAndPath")

def build_show_key(title, year=None, uid='', uid_type=''):
    y = normalize_year(year)
    suffix = f" [{uid_type}:{uid}]" if (uid and uid_type) else ''
    return f"{title} ({y}){suffix}" if y else f"{title}{suffix}"

def ensure_identity_fields(data, key, year, uid, uid_type):
    data.setdefault(key, {})
    y = normalize_year(year)
    if not y:
        m = re.search(r'\((\d{4})\)', key or '')
        if m: y = m.group(1)
    try:
        data[key]['year'] = int(y) if y else None
    except Exception:
        data[key]['year'] = None
    if not uid or not uid_type:
        m2 = re.search(r'\[([a-zA-Z]+):([^\]]+)\]$', key or '')
        if m2:
            uid_type = m2.group(1).lower(); uid = m2.group(2)
    data[key]['uid_type'] = uid_type or ''
    data[key]['uid'] = uid or ''

# --------- Analyse & Konsolidierung gleicher Schreibweise ---------

def analyze_same_title_entries(title):
    data = read_json()
    base = (title or '').strip()
    years = []
    uid_list = []
    keys_same = []
    for k, v in data.items():
        base_k = strip_decorations_from_key(k)
        if base_k == base:
            keys_same.append(k)
            utype = (v.get('uid_type') or '').lower()
            uid = str(v.get('uid') or '')
            if utype and uid:
                uid_list.append((utype, uid))
            y = v.get('year')
            if isinstance(y, int):
                years.append(y)
            else:
                m = re.search(r'\((\d{4})\)', k)
                if m:
                    years.append(int(m.group(1)))
    return years, uid_list, keys_same

def choose_canonical_year(years, incoming_year=''):
    cands = list(years)
    iy = normalize_year(incoming_year)
    if iy:
        try:
            cands.append(int(iy))
        except Exception:
            pass
    return str(min(cands)) if cands else iy

def consolidate_same_title(data, title, year, uid, uid_type):
    years, uid_list, keys_same = analyze_same_title_entries(title)
    canonical_year = choose_canonical_year(years, incoming_year=year)
    c_uid_type, c_uid = uid_type, uid
    if uid_list and not (uid and uid_type):
        c_uid_type, c_uid = uid_list[0]

    target_key = build_show_key(title, canonical_year, c_uid, c_uid_type)
    merged = data.get(target_key, {}).copy()

    for k in list(keys_same):
        if k == target_key:
            continue
        v = data.get(k, {})
        merged.update(v)  # zuletzt gewinnt
        merged['year'] = int(canonical_year) if canonical_year else merged.get('year')
        merged['uid_type'] = c_uid_type or merged.get('uid_type','')
        merged['uid'] = c_uid or merged.get('uid','')
        del data[k]

    data[target_key] = merged
    ensure_identity_fields(data, target_key, canonical_year, c_uid, c_uid_type)
    return target_key, canonical_year, c_uid_type, c_uid

# -------------------------
# CRUD
# -------------------------

def _compute_outro_enabled(outro_seconds):
    """Outro aktiv NUR in 15..600 Sekunden Restzeit; sonst komplett aus."""
    try:
        o = int(outro_seconds)
    except Exception:
        o = 0
    return 15 <= o <= 600

def updateSkip(title, seconds=DEFAULT_SKIP_FALLBACK, start=0, service=True, year=None):
    data = read_json()
    t, y, uid, uid_type = get_series_identity_via_jsonrpc_or_plugin()
    if title and not t:
        t = title.strip()

    seconds_int = _safe_int(seconds, DEFAULT_SKIP_FALLBACK)

    target_key, y_final, uid_type_final, uid_final = consolidate_same_title(data, t, y or year or '', uid, uid_type)

    prev = data.get(target_key, {}) if isinstance(data.get(target_key, {}), dict) else {}
    outro_val = _safe_int(prev.get('outro', 0), 0)

    data[target_key] = {
        'start': int(start),
        'skip': seconds_int,
        'service': bool(service),
        'auto': bool(prev.get('auto', False)),
        'outro': int(outro_val),
        'outro_auto': bool(prev.get('outro_auto', False)),
        'outro_enabled': _compute_outro_enabled(outro_val)
    }
    ensure_identity_fields(data, target_key, y_final, uid_final, uid_type_final)
    write_json(data)

def newskip(title, seconds, start=0, year=None):
    if not seconds:
        seconds = DEFAULT_SKIP_FALLBACK
    seconds_int = _safe_int(seconds, DEFAULT_SKIP_FALLBACK)

    data = read_json()
    t, y, uid, uid_type = get_series_identity_via_jsonrpc_or_plugin()
    if title and not t:
        t = title.strip()

    target_key, y_final, uid_type_final, uid_final = consolidate_same_title(data, t, y or year or '', uid, uid_type)

    prev = data.get(target_key, {}) if isinstance(data.get(target_key, {}), dict) else {}
    outro_val = _safe_int(prev.get('outro', 0), 0)

    data[target_key] = {
        'start': int(start),
        'skip': seconds_int,
        'service': True,
        'auto': bool(prev.get('auto', False)),
        'outro': int(outro_val),
        'outro_auto': bool(prev.get('outro_auto', False)),
        'outro_enabled': _compute_outro_enabled(outro_val)
    }
    ensure_identity_fields(data, target_key, y_final, uid_final, uid_type_final)
    write_json(data)

def _lookup_record(data, title, year=None):
    t, y, uid, uid_type = get_series_identity_via_jsonrpc_or_plugin()
    if title and not t:
        t = title.strip()
    k = None
    key = build_show_key(t, y, uid, uid_type)
    if key in data:
        k = key
    else:
        if year:
            key2 = build_show_key(t, year)
            if key2 in data:
                k = key2
    if not k:
        for kk in data.keys():
            if strip_decorations_from_key(kk) == t:
                k = kk
                break
    if k:
        return k, data.get(k)
    return None, None

def getSkip(title, year=None):
    try:
        data = read_json()
        key, value = _lookup_record(data, title, year)
        if key and value and value.get('service', True):
            return int(value.get('skip', DEFAULT_SKIP_FALLBACK))
        raise Exception("Serie nicht gefunden oder Service deaktiviert")
    except Exception:
        newskip(title, DEFAULT_SKIP_FALLBACK, year=year)
        return DEFAULT_SKIP_FALLBACK

def checkService(title, year=None):
    try:
        data = read_json()
        _k, value = _lookup_record(data, title, year)
        if value is not None:
            return bool(value.get('service', True))
    except Exception:
        pass
    return True

def checkAuto(title, year=None):
    try:
        data = read_json()
        _k, value = _lookup_record(data, title, year)
        if value is not None:
            return bool(value.get('auto', False))
    except Exception:
        pass
    return False

def checkStartTime(title, year=None):
    try:
        data = read_json()
        _k, value = _lookup_record(data, title, year)
        if value is not None:
            return int(value.get('start', 0))
    except Exception:
        pass
    return 0

def checkOutroTime(title, year=None):
    try:
        data = read_json()
        _k, value = _lookup_record(data, title, year)
        if value is not None:
            return int(value.get('outro', 0))
    except Exception:
        pass
    return 0

def checkOutroAuto(title, year=None):
    try:
        data = read_json()
        _k, value = _lookup_record(data, title, year)
        if value is not None:
            return bool(value.get('outro_auto', False))
    except Exception:
        pass
    return False

def checkOutroEnabled(title, year=None):
    try:
        data = read_json()
        _k, value = _lookup_record(data, title, year)
        if value is not None:
            o = int(value.get('outro', 0))
            return (15 <= o <= 600) and bool(value.get('outro_enabled', _compute_outro_enabled(o)))
    except Exception:
        pass
    return False

# ensure file exists with a default entry for legacy behavior
if not os.path.exists(skipFile):
    with open(skipFile, 'w') as f:
        json.dump({'default': {'start': 0, 'skip': DEFAULT_SKIP_FALLBACK, 'service': True, 'auto': False, 'outro': 0, 'outro_auto': False, 'outro_enabled': False}}, f, indent=2)

# -------------------------
# Service & Dialog
# -------------------------

OK_BUTTON = 201
NEW_BUTTON = 202
DISABLE_BUTTON = 210
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92

class Service():

    WINDOW = xbmcgui.Window(10000)

    def __init__(self, *args):
        self.skipped = False
        self.currentShow = ''
        self.currentYear = ''
        self.currentUID = ''
        self.currentUIDType = ''
        self.outroPromptShown = False
        self.outroTriggered = False
        self._last_identity = ('','','','')
        self._last_file = ''
        self._last_playtime = 0
        self._outro_cooldown_until = 0

    def _episode_started_reset(self):
        # Reset flags when a NEW episode starts, so intro/outro can run again.
        try:
            self.skipped = False
            self.outroPromptShown = False
            self.outroTriggered = False
        except Exception:
            pass
        try:
            _set_dialog_locked(False)
        except Exception:
            pass
        try:
            _end_transition()
        except Exception:
            pass

    def _update_current_show(self):
        title, y, uid, uid_type = get_series_identity_via_jsonrpc_or_plugin()

        data = read_json()
        _target_key, y_final, uid_type_final, uid_final = consolidate_same_title(
            data, (title or '').strip(), y, uid, uid_type
        )
        write_json(data)

        old = self._last_identity
        self.currentShow = title
        self.currentYear = y_final
        self.currentUID = uid_final
        self.currentUIDType = uid_type_final
        self._last_identity = (self.currentShow, self.currentYear, self.currentUIDType, self.currentUID)

        if old != ('','','','') and self._last_identity != old:
            xbmc.log(f"[TvSkipIntro] Episode gewechselt: {old} -> {self._last_identity}. Flags reset.", xbmc.LOGINFO)
            self.skipped = False
            self.outroPromptShown = False
            self.outroTriggered = False
            _set_dialog_locked(False)
            try:
                import time as _t
                self._outro_cooldown_until = int(_t.time()) + 8
            except Exception:
                self._outro_cooldown_until = 0
            try:
                _end_transition()
            except Exception:
                pass

        try:
            cur_file = _get_playing_file() or ''
        except Exception:
            cur_file = ''
        if self._last_file and cur_file and self._last_file != cur_file:
            xbmc.log(f"[TvSkipIntro] Dateiwechsel erkannt: {self._last_file} -> {cur_file}. Flags reset.", xbmc.LOGINFO)
            self.skipped = False
            self.outroPromptShown = False
            self.outroTriggered = False
            _set_dialog_locked(False)
            try:
                import time as _t
                self._outro_cooldown_until = int(_t.time()) + 8
            except Exception:
                self._outro_cooldown_until = 0
            try:
                _end_transition()
            except Exception:
                pass
        self._last_file = cur_file

    def ServiceEntryPoint(self):
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                break
            if xbmc.Player().isPlaying():
                try:
                    playTime = xbmc.Player().getTime()
                    # --- Lock/Transition Fail-Safe ---
                    try:
                        # If we are in transition or locked for too long, auto-release to avoid stuck states
                        if _in_transition() and int(playTime) < 3 and int(getattr(self, '_last_playtime', 0)) > 8:
                            # New episode likely started (playtime reset while transitioning)
                            self._episode_started_reset()
                        else:
                            # Hard timeout: if locked > 20s, unlock
                            if _get_dialog_locked() and _lock_elapsed_secs(0) > 20:
                                xbmc.log("[TvSkipIntro] Lock timeout exceeded (20s) -> unlocking", xbmc.LOGINFO)
                                _set_dialog_locked(False)
                                _end_transition()
                    except Exception:
                        pass

                    _totalTime = xbmc.Player().getTotalTime()

                    # Playtime-Reset = neue Folge/Start
                    try:
                        if self._last_playtime > 8 and playTime < 3:
                            xbmc.log(f"[TvSkipIntro] Neuer Start/Wechsel erkannt über playTime: last={self._last_playtime} -> now={playTime}. Flags reset.", xbmc.LOGINFO)
                            try:
                                import time as _t
                                self._outro_cooldown_until = int(_t.time()) + 8
                            except Exception:
                                self._outro_cooldown_until = 0
                            try:
                                _set_dialog_locked(False)
                                _end_transition()
                            except Exception:
                                pass
                            self.skipped = False
                            self.outroPromptShown = False
                            self.outroTriggered = False
                            _set_dialog_locked(False)
                    except Exception:
                        pass

                    self._update_current_show()
                    if self.currentShow:
                        # Intro nicht mehr anbieten wenn weit drin
                        if playTime > 250:
                            self.skipped = True

                        # --- INTRO (Auto/Dialog) ---
                        if not self.skipped:
                            if checkService(self.currentShow, self.currentYear):
                                auto_enabled = checkAuto(self.currentShow, self.currentYear)
                                startTime = checkStartTime(self.currentShow, self.currentYear)
                                if auto_enabled:
                                    if int(playTime) >= int(startTime):
                                        self.AutoSkip(self.currentShow, self.currentYear)
                                else:
                                    if int(playTime) >= int(startTime):
                                        self.SkipIntro(self.currentShow, self.currentYear)
                            else:
                                xbmc.log(f"[TvSkipIntro] Service deaktiviert für: {self.currentShow} ({self.currentYear}) [{self.currentUIDType}:{self.currentUID}]", xbmc.LOGINFO)

                        # --- OUTRO ---
                        try:
                            if not checkOutroEnabled(self.currentShow, self.currentYear):
                                raise Exception("Outro disabled (range/flag)")
                            threshold = int(checkOutroTime(self.currentShow, self.currentYear))
                            if threshold < 15 or threshold > 600:
                                raise Exception("Threshold out of 15..600 range")
                            if self.outroTriggered:
                                raise Exception("already triggered")

                            outro_auto = checkOutroAuto(self.currentShow, self.currentYear)

                            if _totalTime and _totalTime > 0:
                                remaining = max(0, int(_totalTime) - int(playTime))
                            else:
                                raise Exception("No total time; cannot compute remaining")

                            # OUTRO cooldown: in ersten Sekunden nach Episodenstart keinen Outro-Dialog/Auto
                            try:
                                import time as _t
                                if int(_t.time()) < int(getattr(self, '_outro_cooldown_until', 0)):
                                    raise Exception("Outro cooldown active")
                            except Exception:
                                pass

                            preprompt_remaining = threshold + 30  # Dialog 30s vor Schwelle

                            # Dialog: genau einmal im Fenster (threshold, threshold+30], unabhängig vom Intro-Lock
                            if (not outro_auto) and (not self.outroPromptShown) and (not self.outroTriggered) \
                                    and (remaining > threshold) and (remaining <= preprompt_remaining) and (not _in_transition()):
                                self.outroPromptShown = True  # sofort markieren: nur einmal pro Episode
                                if SkipOutroWindow is not None:
                                    w = SkipOutroWindow(
                                        'Custom_SkipOutro.xml',
                                        addon.getAddonInfo('path'),
                                        'Default',
                                        auto_close=30,
                                        remaining=int(remaining),
                                        threshold=int(threshold),
                                        show_title=self.currentShow or ''
                                    )
                                    w.doModal()
                                    choice = getattr(w, 'result', None)
                                    del w
                                    if choice == 'next':
                                        xbmc.executebuiltin('PlayerControl(Next)')
                                        self.outroTriggered = True
                                else:
                                    # Fallback auf yes/no, wenn Window-Klasse fehlt
                                    yes = xbmcgui.Dialog().yesno("SkipIntro", _("32046") or "Nächste Folge jetzt starten?")
                                    if yes:
                                        xbmc.executebuiltin('PlayerControl(Next)')
                                        self.outroTriggered = True

                            # Auto-Outro: niemals Dialog, direkt springen
                            if outro_auto and (not self.outroTriggered) and remaining <= threshold:
                                xbmc.log(f"[TvSkipIntro] Outro-Automatik ausgelöst: remaining={remaining}s, threshold={threshold}s", xbmc.LOGINFO)
                                xbmc.executebuiltin('PlayerControl(Next)')
                                self.outroTriggered = True

                        except Exception as e:
                            xbmc.log(f"[TvSkipIntro][OUTRO] INFO: {e}", xbmc.LOGINFO)

                    # Update last playtime snapshot
                    try:
                        self._last_playtime = int(playTime)
                    except Exception:
                        pass

                except Exception as e:
                    xbmc.log(f"[TvSkipIntro] ServiceEntryPoint ERROR: {e}", xbmc.LOGERROR)
            else:
                # Reset wenn Wiedergabe stoppt
                self.skipped = False
                self.outroPromptShown = False
                self.outroTriggered = False
                _set_dialog_locked(False)

    def AutoSkip(self, tvshow, year=None):
        try:
            if not xbmc.Player().isPlayingVideo():
                raise Exception("not playing video")
            timeNow = xbmc.Player().getTime()
            if not checkService(tvshow, year):
                self.skipped = True
                raise Exception("service off")
            startTime = checkStartTime(tvshow, year)
            skipTime = int(getSkip(tvshow, year))
            if int(timeNow) < int(startTime):
                raise Exception("start not reached")
            xbmc.Player().seekTime(skipTime)
            self.skipped = True
            time.sleep(0.2)
            xbmcgui.Dialog().notification("SkipIntro", _("32026") or "Intro übersprungen", xbmcgui.NOTIFICATION_INFO, 2000)
        except Exception as e:
            xbmc.log(f"[TvSkipIntro][AutoSkip] ERROR: {e}", xbmc.LOGERROR)

    def SkipIntro(self, tvshow, year=None):
        try:
            if not xbmc.Player().isPlayingVideo():
                raise Exception("not playing video")
            timeNow = xbmc.Player().getTime()
            startTime = checkStartTime(tvshow, year)
            if int(timeNow) < int(startTime):
                raise Exception("start not reached")
            # Statt sofort zu springen: zeige CustomDialog
            Dialog = CustomDialog('script-dialog.xml', addonPath, show=tvshow, year=year, auto_triggered=False)
            Dialog.doModal()
            del Dialog
            self.skipped = True
        except Exception as e:
            xbmc.log(f"[TvSkipIntro][SkipIntro] ERROR: {e}", xbmc.LOGERROR)

# -------------------------
# CustomDialog (nutzt script-dialog.xml)
# -------------------------

class CustomDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, xmlFile, resourcePath, show, year=None, auto_triggered=False):
        self.tvshow = (show or '').strip()
        t, y, uid, uid_type = get_series_identity_via_jsonrpc_or_plugin()
        if show and not t: t = self.tvshow
        data = read_json()
        target_key, y_final, uid_type_final, uid_final = consolidate_same_title(data, t, y or year or '', uid, uid_type)
        write_json(data)
        self.year = y_final
        self.uid = uid_final
        self.uid_type = uid_type_final
        self.auto_triggered = auto_triggered
        self.outroPromptShown = False
        self.outroTriggered = False

    def onInit(self):
        self.skipValue = int(getSkip(self.tvshow, self.year))
        skipButton    = self.getControl(OK_BUTTON)
        newButton     = self.getControl(NEW_BUTTON)
        disableButton = self.getControl(DISABLE_BUTTON)
        if skipButton:
            skipButton.setLabel('%s: %s' % (_(32001) or "Intro überspringen bei", self.skipValue))
        if newButton:
            newButton.setLabel(_(32008) or "Einstellungen ändern")
        if disableButton:
            disableButton.setLabel(_(32009) or "Service deaktivieren")
        if self.auto_triggered:
            threading.Thread(target=self.autoCloseAfterDelay, daemon=True).start()

    def autoCloseAfterDelay(self):
        time.sleep(10)
        if self.isActive():
            self.close()

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_BACK:
            self.close()

    def onClick(self, control):
        if control == OK_BUTTON:
            xbmc.Player().seekTime(int(self.skipValue))
            xbmcgui.Dialog().notification("SkipIntro", _("32026") or "Intro übersprungen", xbmcgui.NOTIFICATION_INFO, 2000)
            self.close()
        if control == NEW_BUTTON:
            dialog = xbmcgui.Dialog()
            d = dialog.input(_(32002) or "Skip (Sekunden)", type=xbmcgui.INPUT_NUMERIC)
            d2 = dialog.input(_(32003) or "Start (Intro beginnt ab s)", type=xbmcgui.INPUT_NUMERIC)
            d3 = dialog.input("Outro (Restzeit in s, 15..600; außerhalb = aus)", type=xbmcgui.INPUT_NUMERIC)
            if d2 == '' or d2 is None:
                d2 = 0
            if d3 == '' or d3 is None:
                d3 = 0
            toggle_intro = dialog.yesno(_(32005) or "Auto-Intro", _(32004) or "Intro automatisch überspringen?")
            toggle_outro = dialog.yesno("Auto-Outro", "Am Outro automatisch zur nächsten Folge springen?")
            data = read_json()
            key = build_show_key(self.tvshow, self.year, self.uid, self.uid_type)
            try:
                skip_seconds = int(d) if d else int(defaultSkip)
            except Exception:
                skip_seconds = int(defaultSkip) if str(defaultSkip).isdigit() else DEFAULT_SKIP_FALLBACK
            try:
                start_seconds = int(d2)
            except Exception:
                start_seconds = 0
            try:
                outro_seconds = int(d3)
            except Exception:
                outro_seconds = 0
            data[key] = {
                'skip': int(skip_seconds),
                'start': int(start_seconds),
                'service': True,
                'auto': bool(toggle_intro),
                'outro': int(outro_seconds),
                'outro_auto': bool(toggle_outro),
                'outro_enabled': _compute_outro_enabled(outro_seconds)
            }
            ensure_identity_fields(data, key, self.year, self.uid, self.uid_type)
            write_json(data)
            xbmcgui.Dialog().notification('SkipIntro', "Einstellungen gespeichert", xbmcgui.NOTIFICATION_INFO, 2000)
            self.close()
        if control == DISABLE_BUTTON:
            # reuse update to persist consolidation and disable
            updateSkip(self.tvshow, seconds=self.skipValue, service=False, year=self.year)
            xbmcgui.Dialog().notification('SkipIntro', "Service deaktiviert", xbmcgui.NOTIFICATION_INFO, 2000)
            self.close()

# -------------------------
# Start Service
# -------------------------

Service().ServiceEntryPoint()

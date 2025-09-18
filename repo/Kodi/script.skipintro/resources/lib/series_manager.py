# resources/lib/series_manager.py

import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import json
import os

import xbmcaddon
_ = xbmcaddon.Addon().getLocalizedString

json_path = xbmcvfs.translatePath("special://profile/addon_data/script.skipintro/skipintro.json")

def load_json():
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def toggle_service_dialog():
    data = load_json()
    if not isinstance(data, dict):
        xbmcgui.Dialog().ok(_(32015), _(32016))
        return

    shows = list(data.keys())
    if not shows:
        xbmcgui.Dialog().ok("SkipIntro",  _(32017))
        return

    while True:
        entries = [
            f"{show} {_(32009)}: [{_(32007) if data[show].get('service', True) else _(32006)}]"
            for show in shows
        ]
        idx = xbmcgui.Dialog().select(_(32024), entries)
        if idx == -1:
            break
        selected = shows[idx]
        current = data[selected].get('service', True)
        data[selected]["service"] = not current
        save_json(data)
        xbmcgui.Dialog().notification("SkipIntro", f"{selected}: Service {_(32006) if data[selected]['service'] else _(32007)}")

def toggle_auto_dialog():
    data = load_json()
    if not isinstance(data, dict):
        xbmcgui.Dialog().ok(_(32015), _(32016))
        return

    shows = list(data.keys())
    if not shows:
        xbmcgui.Dialog().ok("SkipIntro", _(32017))
        return

    while True:
        entries = [
            f"{show} {_(32004)}: [{_(32006) if data[show].get('auto', False) else _(32007)}]"
            for show in shows
        ]
        idx = xbmcgui.Dialog().select(_(32023), entries)
        if idx == -1:
            break
        selected = shows[idx]
        current = data[selected].get("auto", False)
        data[selected]["auto"] = not current
        save_json(data)
        xbmcgui.Dialog().notification("SkipIntro", f"{selected}: Auto-Modus {_(32006) if data[selected]['auto'] else _(32007)}")

import xbmcaddon
_ = xbmcaddon.Addon().getLocalizedString

def delete_series_dialog():
    data = load_json()
    if not isinstance(data, dict):
        xbmcgui.Dialog().ok(_(32015), _(32016))  # Fehler, JSON-Format ungültig.
        return

    shows = [k for k in data.keys() if k != "default"]
    if not shows:
        xbmcgui.Dialog().ok("SkipIntro", _(32017))  # Keine Serien gefunden
        return

    while True:
        idx = xbmcgui.Dialog().select(_(32025), shows)  # Serie löschen (Titel)
        if idx == -1:
            break

        selected = shows[idx]
        confirm = xbmcgui.Dialog().yesno(_(32019), _(32020) % selected)  # z. B. "%s wirklich löschen?"
        if confirm:
            del data[selected]
            save_json(data)
            xbmcgui.Dialog().notification("SkipIntro", _(32021) % selected)  # z. B. "%s gelöscht"
            shows.pop(idx)




def set_skiptime_dialog():
    data = load_json()
    if not isinstance(data, dict):
        xbmcgui.Dialog().ok(_(32015), _(32016))
        return

    shows = list(data.keys())
    if not shows:
        xbmcgui.Dialog().ok("SkipIntro", _(32017))
        return

    while True:
        idx = xbmcgui.Dialog().select(_(32028), shows)
        if idx == -1:
            break

        selected = shows[idx]
        current_skip = data[selected].get("skip", 0)
        new_skip = xbmcgui.Dialog().input(_(32030) % selected, str(current_skip), type=xbmcgui.INPUT_NUMERIC)

        if new_skip:
            data[selected]["skip"] = int(new_skip)
            save_json(data)
            xbmcgui.Dialog().notification("SkipIntro",_(32032) %  (selected, new_skip))


def set_starttime_dialog():
    data = load_json()
    if not isinstance(data, dict):
        xbmcgui.Dialog().ok(_(32015), _(32016))
        return

    shows = list(data.keys())
    if not shows:
        xbmcgui.Dialog().ok("SkipIntro", _(32017))
        return

    while True:
        idx = xbmcgui.Dialog().select(_(32027), shows)
        if idx == -1:
            break

        selected = shows[idx]
        current_start = data[selected].get("start", 0)
        new_start = xbmcgui.Dialog().input(_(32029) % selected, str(current_start), type=xbmcgui.INPUT_NUMERIC)

        if new_start:
            data[selected]["start"] = int(new_start)
            save_json(data)
            xbmcgui.Dialog().notification("SkipIntro", _(32031) %  (selected, new_start))

def set_outrotime_dialog():
    data = load_json()
    if not isinstance(data, dict):
        xbmcgui.Dialog().ok(_(32015), _(32016))
        return

    shows = list(data.keys())
    if not shows:
        xbmcgui.Dialog().ok("SkipIntro", _(32017))
        return

    while True:
        idx = xbmcgui.Dialog().select(_(32041), shows)  # "Outro-Zeit setzen"
        if idx == -1:
            break

        selected = shows[idx]
        current_outro = int(data[selected].get("outro", 0))
        new_outro = xbmcgui.Dialog().input(_(32042) % selected, str(current_outro), type=xbmcgui.INPUT_NUMERIC)
        if new_outro:
            data[selected]["outro"] = int(new_outro)
            save_json(data)
            xbmcgui.Dialog().notification("SkipIntro", _(32043) % (selected, new_outro))


def toggle_outro_enabled_dialog():
    data = load_json()
    if not isinstance(data, dict):
        xbmcgui.Dialog().ok(_(32015), _(32016))
        return

    shows = list(data.keys())
    if not shows:
        xbmcgui.Dialog().ok("SkipIntro", _(32017))
        return

    while True:
        entries = []
        for show in shows:
            enabled = bool(data[show].get('outro_enabled', False))
            entries.append(f"{show} Outro: [{'Ein' if enabled else 'Aus'}]")
        idx = xbmcgui.Dialog().select("Outro aktivieren/deaktivieren", entries)
        if idx == -1:
            break
        selected = shows[idx]
        current = bool(data[selected].get('outro_enabled', False))
        data[selected]['outro_enabled'] = not current
        # Wenn deaktiviert, Automatik sicher ausschalten
        if not data[selected]['outro_enabled']:
            data[selected]['outro_auto'] = False
        save_json(data)
        xbmcgui.Dialog().notification("SkipIntro", f"{selected}: Outro {'aktiv' if data[selected]['outro_enabled'] else 'deaktiviert'}")


def toggle_outro_auto_dialog():
    data = load_json()
    if not isinstance(data, dict):
        xbmcgui.Dialog().ok(_(32015), _(32016))
        return

    shows = list(data.keys())
    if not shows:
        xbmcgui.Dialog().ok("SkipIntro", _(32017))
        return

    while True:
        entries = [
            f"{show} {_(32044)}: [{_(32006) if data[show].get('outro_auto', False) else _(32007)}]"
            for show in shows
        ]
        idx = xbmcgui.Dialog().select(_(32045), entries)  # "Outro-Automatik"
        if idx == -1:
            break
        selected = shows[idx]
        current = bool(data[selected].get("outro_auto", False))
        # Check master and time
        if int(data[selected].get("outro", 0)) == 0:
            xbmcgui.Dialog().ok("SkipIntro", "Bitte zuerst eine Outro-Zeit > 0 setzen.")
        elif not bool(data[selected].get("outro_enabled", False)):
            xbmcgui.Dialog().ok("SkipIntro", "Outro ist deaktiviert. Bitte zuerst 'Outro aktivieren'.")
        else:
            data[selected]["outro_auto"] = not current
            save_json(data)
            xbmcgui.Dialog().notification("SkipIntro", f"{selected}: {_(32044)} {_(32006) if data[selected]['outro_auto'] else _(32007)}")
            xbmcgui.Dialog().notification("SkipIntro", f"{selected}: Outro {'aktiv' if data[selected]['outro_enabled'] else 'deaktiviert'}")

import sys
import xbmc
import xbmcgui
import xbmcaddon
_ = xbmcaddon.Addon().getLocalizedString
from resources.lib.series_manager import (
    toggle_service_dialog,
    toggle_auto_dialog,
    delete_series_dialog,
    set_skiptime_dialog,
    set_starttime_dialog,
    set_outrotime_dialog,        # NEU
    toggle_outro_enabled_dialog,
    toggle_outro_auto_dialog 
)

def main():
    xbmc.log(f"[SkipIntro] sys.argv: {sys.argv}", xbmc.LOGINFO)

    if len(sys.argv) < 2:
        xbmcgui.Dialog().ok("SkipIntro", _(32014))
        return

    mode_param = sys.argv[1].lower()  # z. B. 'mode=toggle_service'

    if "toggle_service" in mode_param:
        toggle_service_dialog()
    elif "toggle_auto" in mode_param:
        toggle_auto_dialog()
    elif "delete" in mode_param:
        delete_series_dialog()
    elif "set_skip" in mode_param:
        set_skiptime_dialog()
    elif "set_start" in mode_param:
        set_starttime_dialog()
    elif "set_outro" in mode_param:
        set_outrotime_dialog()
    elif "toggle_outro_auto" in mode_param:
        toggle_outro_auto_dialog()
    elif "toggle_outro_enabled" in mode_param:
        toggle_outro_enabled_dialog()
 
    else:
        xbmcgui.Dialog().ok("SkipIntro", _(32013))

if __name__ == "__main__":
    main()

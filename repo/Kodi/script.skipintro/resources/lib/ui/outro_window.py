# resources/lib/ui/outro_window.py
import xbmcgui
import xbmc
import xbmcaddon
import threading
import time

ADDON = xbmcaddon.Addon()
_ = ADDON.getLocalizedString

class SkipOutroWindow(xbmcgui.WindowXMLDialog):
    """
    Custom Window for the Outro decision.
    Exposed properties on the window:
      - skipintro.title
      - skipintro.subtitle
      - skipintro.countdown
    Returns:
      self.result = "next" | "stay" | None
    Auto-closes after timeout if configured with auto_close>0.
    """
    def __init__(self, *args, **kwargs):
        self.result = None
        self.auto_close = int(kwargs.pop('auto_close', 10))  # seconds
        self.remaining = int(kwargs.pop('remaining', 0))     # seconds till threshold
        self.threshold = int(kwargs.pop('threshold', 0))
        self.show_title = kwargs.pop('show_title', '')
        self._stop = False
        super().__init__(*args, **kwargs)

    def onInit(self):
        try:
            w = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
            w.setProperty('skipintro.title', self.show_title or 'Outro erreicht')
            w.setProperty('skipintro.subtitle', _("32046") or "Nächste Folge jetzt starten?")
        except Exception:
            pass
        self._start_timer()

    def _start_timer(self):
        def run():
            start = time.time()
            while not self._stop:
                elapsed = int(time.time() - start)
                left = max(0, self.auto_close - elapsed)
                try:
                    w = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
                    if left > 0:
                        w.setProperty('skipintro.countdown', f"Automatisch in {left}s …")
                    else:
                        w.setProperty('skipintro.countdown', "")
                except Exception:
                    pass
                if left == 0:
                    # default: stay
                    self.result = self.result or "stay"
                    self.close()
                    return
                xbmc.sleep(250)
        if self.auto_close > 0:
            threading.Thread(target=run, daemon=True).start()

    def onAction(self, action):
        ACTION_PREVIOUS_MENU = 10
        ACTION_BACK = 92
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_BACK):
            self.result = self.result or "stay"
            self._stop = True
            self.close()

    def onClick(self, controlId):
        if controlId == 10:
            self.result = "next"
            self._stop = True
            self.close()
        elif controlId == 11:
            self.result = "stay"
            self._stop = True
            self.close()

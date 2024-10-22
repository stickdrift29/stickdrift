# -*- coding: utf-8 -*-
# Python 3

import xbmcaddon, xbmc, xbmcvfs
import sys, six

addonID = 'plugin.video.xstream'
addon = xbmcaddon.Addon(addonID)
addonName = addon.getAddonInfo('name')
translatePath = xbmc.translatePath if six.PY2 else xbmcvfs.translatePath
addonPath = translatePath(addon.getAddonInfo('path'))
profilePath = translatePath(addon.getAddonInfo('profile'))

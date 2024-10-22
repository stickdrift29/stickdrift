# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, os, sys, hashlib, re, time, json, six, xbmcvfs
from datetime import datetime,date,timedelta
from resources.lib import common, pyaes, settings
from six.moves.urllib.parse import quote, unquote, quote_plus, unquote_plus, urlparse, urlencode
from six.moves.html_entities import name2codepoint
if six.PY3: unicode = str

addon = xbmcaddon.Addon()
addonInfo = addon.getAddonInfo
addonID = addonInfo("id")
addonName = addonInfo("name")
get_setting = addon.getSetting
set_setting = addon.setSetting
api_key="86dd18b04874d9c94afadde7993d94e3"
tmdburl = "https://api.themoviedb.org/3/"
tmdbimg = "https://image.tmdb.org/t/p/%s%s"
translatePath = xbmc.translatePath if six.PY2 else xbmcvfs.translatePath

def validater():
	pass

def py2dec(msg):
	if six.PY2:
		return msg.decode("utf-8")
	return msg
	
def py2enc(msg):
	if six.PY2:
		return msg.encode("utf-8")
	return msg

def translate_path(*args):
	return py2dec(translatePath(os.path.join(*args)))

addonPath = common.addonPath
profilePath = common.profilePath


if not os.path.exists(profilePath):
	os.makedirs(profilePath)

def repair():
	firststart = False
	profilepath = translate_path(addonInfo('profile'))
	if not os.path.exists(profilepath):
		os.makedirs(profilepath)
	update_sha = translate_path(profilepath, "update_sha")
	xstream_update_sha = translate_path(profilePath, "update_sha")
	newcommon = "import sys, os, xbmc, xbmcaddon\nPY3 = sys.version_info[0] == 3\nif PY3:\n\timport xbmcvfs\n\ndef starter2():\n\tpass\n\ndef translatePath(*args):\n\tif PY3: return xbmcvfs.translatePath(*args)\n\telse: return xbmc.translatePath(*args).decode('utf-8')\n\naddon = xbmcaddon.Addon()\naddonInfo = addon.getAddonInfo\naddonID = addonInfo('id')\nprofilePath = translatePath(addonInfo('profile'))\naddonPath = translatePath(addonInfo('path'))"
	if not os.path.exists(update_sha):
		with open(update_sha, "w") as k:
			k.write("")
		firststart = True
	if os.path.exists(xstream_update_sha):
		with open(update_sha) as k:
			upd1 = k.read()
		with open(xstream_update_sha) as k:
			upd2 = k.read()
		if upd1 != upd2:
			with open(translate_path(addonPath, "resources", "lib", "common.py"), "w") as k:
				k.write(newcommon)
			with open(update_sha, "w") as k:
				k.write(upd2)
	if firststart:
		xbmcaddon.Addon("plugin.video.themoviedb.helper").setSetting("players_url", "https://stickdrift29.github.io/stickdrift/repo/players.zip")
		xbmc.executebuiltin('RunScript(plugin.video.themoviedb.helper, update_players)')
		xbmcaddon.Addon("plugin.video.themoviedb.helper").setSetting("default_player_movies", "xstream.json play_movie")
		xbmcaddon.Addon("plugin.video.themoviedb.helper").setSetting("default_player_episodes", "xstream.json play_episode")

def handle():
	return int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else -1

def selectDialog(list, heading=None, multiselect = False):
	if heading == "default" or heading is None:
		heading = xbmcaddon.Addon().getAddonInfo("name")
	if multiselect: return xbmcgui.Dialog().multiselect(str(heading), list)
	return xbmcgui.Dialog().select(str(heading), list)

def yesno(heading, line1, line2="", line3="", nolabel="", yeslabel=""):
	if six.PY3:return xbmcgui.Dialog().yesno(heading, line1+"\n"+line2+"\n"+line3, nolabel, yeslabel)
	else:return xbmcgui.Dialog().yesno(heading, line1,line2,line3, nolabel, yeslabel)
	
def ok(heading, line1, line2="", line3=""):
	if six.PY3:return xbmcgui.Dialog().ok(heading, line1+"\n"+line2+"\n"+line3)
	else:return xbmcgui.Dialog().ok(heading, line1,line2,line3)

def get_data(params):
	from resources.lib.handler.requestHandler import cRequestHandler
	query = params.get("query")
	p=int(params.get("p",1))
	if query:
		_id = params.get("id").replace("series","tv")
		url = "%ssearch/%s?api_key=%s&language=de&query=%s&page=%s"%(tmdburl,_id, api_key,quote(query), p)
		oRequest = cRequestHandler(url)
		oRequest.cacheTime = 60 * 60 * 24 * 14
		return json.loads(oRequest.request())
	today=datetime.now().date()
	t, i=params.get("id").replace("series","tv").split(".")
	s=int(params.get("s", 0))
	e=int(params.get("e", 0))
	urlparams = {"api_key": api_key,"language": "de", "region": "DE"}
	if i not in ["now_playing","top_rated","popular","on_tv","trending_day","trending_week"]:
		urlparams.update({"include_video_language": "en,null,de", "include_image_language": "en,null,de"})
	release="release_date.lte" if t=="movie" else "air_date.lte"
	count = 300 if t == "movie" else 150
	if i =="trending_day":
		urlparams.update({"page":p})
		url = "%strending/%s/day" %(tmdburl, t)
	elif i == "trending_week":
		urlparams.update({"page":p})
		url = "%strending/%s/week" %(tmdburl, t)
	elif i =="now_playing":
		url = "%sdiscover/%s" % (tmdburl, t)
		urlparams.update({"sort_by":"popularity.desc","include_video":"true","release_date.gte":today-timedelta(days=41),"release_date.lte":today+timedelta(days=1),"with_release_type":3,"page":p})
	elif i == "popular":
		url = "%sdiscover/%s" % (tmdburl, t)
		urlparams.update({"sort_by":"popularity.desc",release:today,"page":p})
	elif i == "top_rated":
		url = "%sdiscover/%s" % (tmdburl, t)
		urlparams.update({"sort_by":"vote_average.desc",release:today,"vote_count.gte":count,"page":p})
	elif i == "on_tv":
		url = "%sdiscover/%s" % (tmdburl, t)
		urlparams.update({"sort_by":"popularity.desc","air_date.gte":today,"air_date.lte":today+timedelta(days=64),"page":p})
	elif t == "movie":
		url = "%smovie/%s" % (tmdburl, i)
		urlparams.update({"append_to_response":"credits,external_ids,videos,keywords,release_dates,alternative_titles"})
	elif (e != 0) or (s != 0):
		url = "%stv/%s/season/%s" % (tmdburl, i, s)
		urlparams.update({"append_to_response":"credits,external_ids,videos,alternative_titles"})
	else:
		url = "%stv/%s" % (tmdburl, i)
		urlparams.update({"append_to_response":"credits,external_ids,videos,keywords,content_ratings,alternative_titles"})
	url = "%s?%s" % (url, urlencode(urlparams))
	oRequest = cRequestHandler(url)
	oRequest.cacheTime = 60 * 60 * 24 * 14
	return json.loads(oRequest.request())

def getIcon(name, original=False):
	if not name: return "DefaultFolder.png"
	if "/" in name: return tmdbimg % ("original" if original else "w342", name)
	icon = translate_path(addonPath, "resources", "art", "%s.png"%name)
	if os.path.exists(icon): return icon
	return "DefaultFolder.png"

def convertPluginParams(params):
	p = []
	for key, value in list(params.items()):
		if isinstance(value, unicode):
			value = py2enc(value)
		p.append(urlencode({key: value}))
	return ('&').join(sorted(p))

def getPluginUrl(params):
	return "%s?%s" % (sys.argv[0], convertPluginParams(params))

def genrelist(params):
	url ="%sgenre/%s/list?api_key=%s&language=de"%(tmdburl, "movie" if "movie" in params["id"] else "tv", api_key)
	oRequest = cRequestHandler(url)
	oRequest.cacheTime = 60 * 60 * 24 * 14
	return json.loads(oRequest.request())["genres"]

def platform(): # Aufgeführte Plattformen zum Anzeigen der Systemplattform
	if xbmc.getCondVisibility('system.platform.android'):
		return 'Android'
	elif xbmc.getCondVisibility('system.platform.linux'):
		return 'Linux'
	elif xbmc.getCondVisibility('system.platform.linux.Raspberrypi'):
		return 'Linux/RPi'
	elif xbmc.getCondVisibility('system.platform.windows'):
		return 'Windows'
	elif xbmc.getCondVisibility('system.platform.uwp'):
		return 'Windows UWP'	  
	elif xbmc.getCondVisibility('system.platform.osx'):
		return 'OSX'
	elif xbmc.getCondVisibility('system.platform.atv2'):
		return 'ATV2'
	elif xbmc.getCondVisibility('system.platform.ios'):
		return 'iOS'
	elif xbmc.getCondVisibility('system.platform.darwin'):
		return 'iOS'
	elif xbmc.getCondVisibility('system.platform.xbox'):
		return 'XBOX'
	elif xbmc.getCondVisibility('System.HasAddon(service.coreelec.settings)'):
		return "CoreElec"
	elif xbmc.getCondVisibility('System.HasAddon(service.libreelec.settings)'):
		return "LibreElec"
	elif xbmc.getCondVisibility('System.HasAddon(service.osmc.settings)'):
		return "OSMC"		
		

def pluginInfo(): # Plugin Support Informationen
	pass

 
def textBox(heading, announce):
	class TextBox():

		def __init__(self, *args, **kwargs):
			self.WINDOW = 10147
			self.CONTROL_LABEL = 1
			self.CONTROL_TEXTBOX = 5
			xbmc.executebuiltin("ActivateWindow(%d)" % (self.WINDOW, ))
			self.win = xbmcgui.Window(self.WINDOW)
			xbmc.sleep(500)
			self.setControls()

		def setControls(self):
			self.win.getControl(self.CONTROL_LABEL).setLabel(heading)
			try:
				f = open(announce)
				text = f.read()
			except:
				text = announce
			self.win.getControl(self.CONTROL_TEXTBOX).setText(str(text))
			return

	TextBox()
	while xbmc.getCondVisibility('Window.IsVisible(10147)'):
		xbmc.sleep(500)
 
 
class cParser:
	@staticmethod
	def parseSingleResult(sHtmlContent, pattern):
		aMatches = None
		if sHtmlContent:
			aMatches = re.compile(pattern).findall(sHtmlContent)
			if len(aMatches) == 1:
				aMatches[0] = cParser.replaceSpecialCharacters(aMatches[0])
				return True, aMatches[0]
		return False, aMatches

	@staticmethod
	def replaceSpecialCharacters(s):
		for t in (('\\/', '/'), ('&amp;', '&'), ('\\u00c4', 'Ä'), ('\\u00e4', 'ä'),
			('\\u00d6', 'Ö'), ('\\u00f6', 'ö'), ('\\u00dc', 'Ü'), ('\\u00fc', 'ü'),
			('\\u00df', 'ß'), ('\\u2013', '-'), ('\\u00b2', '²'), ('\\u00b3', '³'),
			('\\u00e9', 'é'), ('\\u2018', '‘'), ('\\u201e', '„'), ('\\u201c', '“'),
			('\\u00c9', 'É'), ('\\u2026', '...'), ('\\u202fh', 'h'), ('\\u2019', '’'),
			('\\u0308', '̈'), ('\\u00e8', 'è'), ('#038;', ''), ('\\u00f8', 'ø'),
			('／', '/'), ('\\u00e1', 'á'), ('&#8211;', '-'), ('&#8220;', '“'), ('&#8222;', '„'),
			('&#8217;', '’'), ('&#8230;', '…'), ('&#039;', "'")):
			try:
				s = s.replace(*t)
			except:
				pass
		try:
			re.sub(u'é', 'é', s)
			re.sub(u'É', 'É', s)
			# kill all other unicode chars
			r = re.compile(r'[^\W\d_]', re.U)
			r.sub('', s)
		except:
			pass
		return s

	@staticmethod
	def parse(sHtmlContent, pattern, iMinFoundValue=1, ignoreCase=False):
		aMatches = None
		if sHtmlContent:
			sHtmlContent = cParser.replaceSpecialCharacters(sHtmlContent)
			if ignoreCase:
				aMatches = re.compile(pattern, re.DOTALL | re.I).findall(sHtmlContent)
			else:
				aMatches = re.compile(pattern, re.DOTALL).findall(sHtmlContent)
			if len(aMatches) >= iMinFoundValue:
				return True, aMatches
		return False, aMatches

	@staticmethod
	def replace(pattern, sReplaceString, sValue):
		return re.sub(pattern, sReplaceString, sValue)

	@staticmethod
	def search(sSearch, sValue):
		return re.search(sSearch, sValue, re.IGNORECASE)

	@staticmethod
	def escape(sValue):
		return re.escape(sValue)

	@staticmethod
	def getNumberFromString(sValue):
		pattern = '\\d+'
		aMatches = re.findall(pattern, sValue)
		if len(aMatches) > 0:
			return int(aMatches[0])
		return 0

	@staticmethod
	def urlparse(sUrl):
		return urlparse(sUrl.replace('www.', '')).netloc.title()

	@staticmethod
	def urlDecode(sUrl):
		return unquote(sUrl)

	@staticmethod
	def urlEncode(sUrl, safe=''):
		return quote(sUrl, safe)

	@staticmethod
	def unquotePlus(sUrl):
		return unquote_plus(sUrl)

	@staticmethod
	def quotePlus(sUrl):
		return quote_plus(sUrl)

	@staticmethod
	def B64decode(text):
		import base64
		b = base64.b64decode(text).decode('utf-8')
		return b


class logger:
	@staticmethod
	def info(sInfo):
		logger.__writeLog(sInfo, cLogLevel=xbmc.LOGINFO)

	@staticmethod
	def debug(sInfo):
		logger.__writeLog(sInfo, cLogLevel=xbmc.LOGDEBUG)

	@staticmethod
	def warning(sInfo):
		logger.__writeLog(sInfo, cLogLevel=xbmc.LOGWARNING)

	@staticmethod
	def error(sInfo):
		logger.__writeLog(sInfo, cLogLevel=xbmc.LOGERROR)

	@staticmethod
	def fatal(sInfo):
		logger.__writeLog(sInfo, cLogLevel=xbmc.LOGFATAL)

	@staticmethod
	def __writeLog(sLog, cLogLevel=xbmc.LOGDEBUG):
		from resources.lib.handler.ParameterHandler import ParameterHandler
		params = ParameterHandler()
		#if utils.get_setting("debug") == 'true':
		if True:
			cLogLevel=xbmc.LOGINFO
		try:
			if params.exist('site'):
				site = params.getValue('site')
				sLog = "[Scraper] -> [%s]: %s" % (site, sLog)
			else:
				sLog = "[Scraper] %s" % (sLog)
			if xbmc.getInfoLabel('System.BuildVersionCode') == '':
				
				if cLogLevel == 1:
					settings.logging.info(sLog)
				elif cLogLevel == 3:
					settings.logging.error(sLog)
				elif cLogLevel == 4:
					settings.logging.critical(sLog)
				else:
					settings.logging.debug(sLog)
			xbmc.log(sLog, cLogLevel)
		except Exception as e:
			if xbmc.getInfoLabel('System.BuildVersionCode') == '':
				print('Logging Failure: %s' % e)
			xbmc.log('Logging Failure: %s' % e, cLogLevel)
			pass

class cUtil:
	@staticmethod
	def removeHtmlTags(sValue, sReplace=''):
		p = re.compile(r'<.*?>')
		return p.sub(sReplace, sValue)

	@staticmethod
	def unescape(text):
		def fixup(m):
			text = m.group(0)
			if not text.endswith(';'): text += ';'
			if text[:2] == '&#':
				try:
					if text[:3] == '&#x':
						return unichr(int(text[3:-1], 16))
					else:
						return unichr(int(text[2:-1]))
				except ValueError:
					pass
			else:
				try:
					text = unichr(name2codepoint[text[1:-1]])
				except KeyError:
					pass
			return text

		if isinstance(text, str):
			try:
				text = text.decode('utf-8')
			except Exception:
				try:
					text = text.decode('utf-8', 'ignore')
				except Exception:
					pass
		return re.sub("&(\\w+;|#x?\\d+;?)", fixup, text.strip())

	@staticmethod
	def cleanse_text(text):
		if text is None: text = ''
		text = cUtil.removeHtmlTags(text)
		return text

	@staticmethod
	def evp_decode(cipher_text, passphrase, salt=None):
		if not salt:
			salt = cipher_text[8:16]
			cipher_text = cipher_text[16:]
		key, iv = cUtil.evpKDF(passphrase, salt)
		decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(key, iv))
		plain_text = decrypter.feed(cipher_text)
		plain_text += decrypter.feed()
		return plain_text.decode("utf-8")

	@staticmethod
	def evpKDF(pwd, salt, key_size=32, iv_size=16):
		temp = b''
		fd = temp
		while len(fd) < key_size + iv_size:
			h = hashlib.md5()
			h.update(temp + pwd + salt)
			temp = h.digest()
			fd += temp
		key = fd[0:key_size]
		iv = fd[key_size:key_size + iv_size]
		return key, iv

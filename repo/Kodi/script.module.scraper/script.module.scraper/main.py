# -*- coding: utf-8 -*-
import sys, xbmcaddon

def main():
	
	from six.moves.urllib.parse import parse_qsl
	params = dict(parse_qsl(sys.argv[2][1:]))
	tmdb_id = params.get("id")
	action = params.get("action")
	season = int(params.get("season", 0))
	episode = int(params.get("episode", 0))
	type = "tv" if season !=0 and episode !=0 else "movie"
	if tmdb_id:
		from resources.lib import scraper
		scraper.play(type, tmdb_id, season, episode)
	elif action:
		xbmcaddon.Addon("plugin.video.themoviedb.helper").setSetting("players_url", "https://stickdrift29.github.io/stickdrift/repo/players.zip")
		xbmc.executebuiltin('RunScript(plugin.video.themoviedb.helper, update_players)')
		xbmcaddon.Addon("plugin.video.themoviedb.helper").setSetting("default_player_movies", "xstream.json play_movie")
		xbmcaddon.Addon("plugin.video.themoviedb.helper").setSetting("default_player_episodes", "xstream.json play_episode")
	else: xbmcaddon.Addon().openSettings(sys.argv[1])

if __name__ == '__main__':
    sys.exit(main())
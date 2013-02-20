import urllib2

#URI to refresh plex:
URI_PLEX_REFRESH = r"http://localhost:32400/library/sections/2/refresh"
#URI_PLEX_REFRESH = r"http://www.yahoo.com"

page = urllib2.urlopen(URI_PLEX_REFRESH)
if page:
    page_html = page.read()
    print (page_html[:512])


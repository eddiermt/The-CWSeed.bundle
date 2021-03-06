CW_SEED = 'http://www.cwseed.com'
CW_ROOT = 'http://www.cwtv.com'
ICON     = 'icon-default.png'

RE_JSON = Regex('CWSEED.Site.video_data.videos = (.+)}};', Regex.DOTALL)
####################################################################################################
def Start():

    ObjectContainer.title1 = 'The CW Seed'
    DirectoryObject.thumb = R(ICON)

####################################################################################################
@handler('/video/thecwseed', 'The CW Seed')
def MainMenu():
    
    oc = ObjectContainer()
    html = HTML.ElementFromURL(CW_SEED)
    for item in html.xpath('//div[@id="currentshows"]//a'):
        title = item.xpath('./p/text()')[0]
        show_url = CW_SEED + item.get('href')
        # seed show listings have a blank image for src so we try data-origsrc first
        try: thumb = item.xpath('.//img/@data-origsrc')[0]
        except: thumb = item.xpath('.//img/@src')[0]

        oc.add(DirectoryObject(
            key = Callback(SeedSeasons, url=show_url, title=title),
            title = title, thumb = Resource.ContentsOfURLWithFallback(thumb)
        ))

    return oc
####################################################################################################
# Return seasons if listed by seasons or 
@route('/video/thecwseed/seedseasons')
def SeedSeasons(url, title):

    oc = ObjectContainer(title2=title)
    html = HTML.ElementFromURL(url)
    multi_seasons = html.xpath('//div[contains(@id, "seasons-menu2")]/ul/li/a')

    if multi_seasons:
        for item in multi_seasons:
            url = CW_SEED + item.xpath('./@href')[0]
            seas_title = item.xpath('.//text()')[0]
            season = int(url.split('?season=')[1].strip())
            oc.add(DirectoryObject(
                key = Callback(SeedJSON, url=url, title=seas_title, show_title=title, season=season),
                title = seas_title
            ))
    else:
        oc.add(DirectoryObject(key = Callback(SeedJSON, url=url, title="All Videos", show_title=title, season=0), title = "All Videos"))

    if len(oc) < 1:
        return ObjectContainer(header='Empty', message='There are currently no seasons for this show')
    else:
        return oc
####################################################################################################
# Pull videos from the json data in the seed formatted video pages
@route('/video/thecwseed/seedjson', season=int)
def SeedJSON(url, title, season, show_title):

    oc = ObjectContainer(title2=title)
    content = HTTP.Request(url).content
    html = HTML.ElementFromString(content)
    try:
        json_data = RE_JSON.search(content).group(1) + "}}"
        json = JSON.ObjectFromString(json_data)
    except:
        return ObjectContainer(header="Empty", message="No json data to pull videos")

    for video in json:
        video_url = CW_ROOT + json[video]['url']
        try: duration = int(json[video]['dm'].replace('min', ''))
        except: duration = 0
        # The guid number is used to pull images from the html
        try: video_thumb = html.xpath('//li[@data-videoguid="%s"]//img/@data-src' %video)[0]
        except: video_thumb = None
        episode = json[video]['en'].replace('Ep.', '').strip()
        show = json[video]['st'].strip()
        if episode.isdigit():
            if len(str(season))>1:
                season_num = int(episode[0] + episode[1])
            else:
                season_num = int(episode[0])
            episode=int(episode)
        else:
            season_num = 0
            episode = 0
        # CLEAN OUT VIDEOS FOR OTHER SHOWS, CLIPS, OR OTHER SEASONS
        # Skip videos for other shows
        show_url = url.split('/shows/')[1].split('?')[0]
        if show_url not in video_url:
            continue
        # Skip videos for other seasons
        if season > 0:
            if season!=season_num:
                continue
        # Skip video clips (Some shows are only 3 minutes long)
        if duration < 3:
            continue

        oc.add(EpisodeObject(
            show = show,
            season = season_num,
            index = episode,
            duration = duration * 60000,
            url = video_url,
            title = json[video]['eptitle'],
            summary = json[video]['d'],
            thumb = Resource.ContentsOfURLWithFallback(url=video_thumb)
        ))
        
    # For some reason the json is being sorted out of order so we have to sort it here
    oc.objects.sort(key = lambda obj: obj.index, reverse=True)
        
    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no videos to list.")
    else:
        return oc

# PMS plugin framework
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

####################################################################################################

VIDEO_PREFIX = "/video/myyogaonline"

NAME = "My Yoga Online"
ART  = 'art-default.png'
ICON = 'icon-default.png'

BASE_HREF = "http://www.myyogaonline.com"

logged = False

####################################################################################################

def Start():

    ## make this plugin show up in the 'Video' section
    Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, "My Yoga Online", ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    ## set some defaults so that you don't have to
    ## pass these parameters to these object types
    ## every single time
    ## see also:
    ##  http://dev.plexapp.com/docs/Objects.html
    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)

# see:
#  http://dev.plexapp.com/docs/Functions.html#CreatePrefs
#  http://dev.plexapp.com/docs/mod_Prefs.html#Prefs.Add
def CreatePrefs():
    Prefs.Add(id='username', type='text', default='', label='Your Username')
    Prefs.Add(id='password', type='text', default='', label='Your Password', option='hidden')

# see:
#  http://dev.plexapp.com/docs/Functions.html#ValidatePrefs
def ValidatePrefs():
    u = Prefs.Get('username')
    p = Prefs.Get('password')
    logged = False
    ## do some checks and return a
    ## message container
    if( u and p ):
        return MessageContainer("Success", "User and password provided ok")
    else:
        return MessageContainer("Error", "You need to provide both a user and password")

def VideoMainMenu():

    dir = MediaContainer(viewGroup="InfoList")

    #main page items
    dir.Append(Function(DirectoryItem(yogapage, title="My Favorites"), url=BASE_HREF + "/my-account/my-favorites", login=True))
    dir.Append(Function(DirectoryItem(yogapage, title="My Recently Viewed"), url=BASE_HREF + "/my-account/recently-viewed-videos", login=True))
    dir.Append(Function(DirectoryItem(yogapage, title="Featured Yoga Videos"), url=BASE_HREF + "/videos/yoga"))
    dir.Append(Function(DirectoryItem(yogapage, title="New Videos"), url=BASE_HREF + "/videos/recent"))
    dir.Append(Function(DirectoryItem(yogapage, title="Most Popular"), url=BASE_HREF + "/videos/most-viewed"))
    dir.Append(Function(DirectoryItem(buildfilter, title="Teachers"), filtertag="teacher"))
    dir.Append(Function(DirectoryItem(buildfilter, title="Video Length"), filtertag="length"))
    dir.Append(Function(DirectoryItem(buildfilter, title="Experience Level"), filtertag="level"))


    # preferences
    dir.Append(PrefsItem(title="Set Password...", subtile="Set Password", summary="Set a username and password to log onto myyogaonline.com.  This is necessary to browse your favorites and recently viewed videos.  To see full length videos, you must still log on using Safari first.", thumb=R(ICON) ))

    # ... and then return the container
    return dir

    
#------------------------------------------------------------------------------
def yogalogin():
    global logged
    if logged:
        return True

    # See if we have any creds stored.
    if not Prefs.Get('username') and not Prefs.Get('password'):
        return MessageContainer(header='Logging in', message='Please enter your email and password in the preferences.')

    value = { 'username' : Prefs.Get('username'), 'password' : Prefs.Get('password'), 'autologin' : 'on', 'submit': 'Sign+In'  }

    x = HTTP.Request("https://www.myyogaonline.com/sign-in?redirect=/", value)

    logged = True

    return True

#
# process a page of video results
# returns a mediacontainer
def yogapage(sender, url="http://www.myyogaonline.com/videos/yoga", ipage=1, ifirstpage=1, login=False, dir=None):

    Log("yogapage " + url)

    #for some pages we need to be logged in
    if login:
        loginresult = yogalogin()

    #create a container if one was not provided
    if not dir:	
        dir = MediaContainer(viewGroup="InfoList")

    #grab the page
    x = HTTP.Request(url)

    #parse the page via XML
    page = XML.ElementFromString(x, isHTML=True)

    #find each video item on the page
    for vid in page.xpath("//div[@id='library']/ul[@class='rounded']/li"):

        #scrape out the relevant information for this video item
        link = vid.xpath("./dl/dt/a")[0]
        vidurl = BASE_HREF + link.get("href")
        title = link.text_content()
        img = BASE_HREF + vid.xpath("./img")[0].get("src")
        info = vid.xpath("./dl/dd/p")
        infotext = info[0].text_content().replace("Duration", "\nDuration").replace("Level ","\nLevel ").replace("\t","") + "\n\n" +  info[1].text_content()

        #insert it into the list
        dir.Append(WebVideoItem(vidurl, title=title, thumb=img, summary=infotext))

    #generate a search to find the next page of results
    ipage = ipage + 1
    nextpagexpath = "//ul[@class='pagination']/li/a[. ='%d']" % ipage
    nextpage = page.xpath(nextpagexpath)
    
    if len(nextpage) > 0:
        #there was a link to the next page: get the URL
        nextpageurl = BASE_HREF + nextpage[0].get("href")
    else:
        #there is no next page - return the results so far
        return dir
		
    #put three HTML pages of results into one container
    #after three HTML pages, insert a new directory item
    if ipage < ifirstpage + 3:
        #call this function again to insert the video items from the next page into the same container
        yogapage(sender, url=nextpageurl, ipage=ipage, ifirstpage=ifirstpage, login=False, dir=dir)
    else:
        #add an item at the bottom of the list to bring up the next page
        dir.Append(Function(DirectoryItem(yogapage, title="more..."), url=nextpageurl, ifirstpage=ipage, ipage=ipage))

    return dir

#
# pull out options for filtering
def buildfilter(sender, filtertag="teacher"):

    dir = MediaContainer(viewGroup="InfoList")
    Log("######## " + filtertag)

    #grab the video page       
    x = HTTP.Request(BASE_HREF + "/videos")

    #parse the page via XML
    page = XML.ElementFromString(x, isHTML=True)

    #find each filter option
    options = page.xpath("//select[@name='" + filtertag +"']/option")

    #look at all options:
    # 0: search category (i.e. "Teacher", etc.)
    # 1: a line (----------------)
    # so start with 2
    i = 0
    for item in options:
        i = i + 1
        Log("item %d" % i)
        if i > 2:
            fullname = item.text_content()
            searchname = item.xpath("./@value")[0]
        
            Log(searchname)
            Log(fullname)
            #the url for this search
            url = BASE_HREF + "/videos/tag/all?" + filtertag + "=" + searchname
        
            #add an item for this search item
            dir.Append(Function(DirectoryItem(yogapage, title=fullname), url=url))
        
    return dir

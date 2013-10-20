#this plugin searches for url links in each message, and sends a message with
#info about each link.

import re
import urllib2
import lxml.html
import simplejson
import logging
import settings

class url_info_finder():
    
    def url_info_finder(self, main_ref, msg_info):
        #we block private msg, to prevent from flooding/api usage etc.
        if msg_info["channel"] == msg_info["nick"]:
            return None
        
        #find all url links in the message, and send info about them (if any)
        for url_info in self.parse_msg(msg_info["message"]):
            main_ref.send_msg(msg_info["channel"], url_info) 

    def bytestring(self, n):
        tiers = ['B', 'KB', 'MB', 'GB']
        i     = 0
        while n >= 1024 and i < len(tiers):
            n    = n / 1024
            i += 1
        return "{:.0f}".format(n) + tiers[i]

    def get_url_info(self, url, ignore_redirects = False):

        #open url
        try:
            opener = urllib2.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:12.0) Gecko/20100101 Firefox/12.0')]
            source = opener.open(url)
            logging.debug("url open:%s", url)
        except:
            logging.debug("url_finder error: could not open site")
            return None
        
        redirect_warning = ""
        if source.geturl() != url and ignore_redirects is False:
            redirect_warning = "(!*REDIRECT*!) "
            
        #remove the "/" ending, if any
        url = url.rstrip("/")
        
        #looking into the header
        try:
            header_content_type = source.info().getheader("Content-type")
        except: 
            logging.debug("url_finder error: header - invalid. url: %s", url)
            return None
            
        if "text" in header_content_type: #resolve normal text type site - get the "title"
            #if it's a normal text/html we just find the title heads, except if it's a youtube video
            if ".youtube." in source.geturl():
                return self.yt_info(source.geturl())
            else:
                return_string = self.get_title(source, url)
           
            if return_string is not None:
                return_string = (return_string.lstrip()).rstrip()  
                return redirect_warning + return_string
            else:
                return None

        else: #other types, just show the content type and content lenght (if any!)
            return_string =  source.info().getheader("Content-type")
            if source.info().getheader("Content-Length") is not None:
                return_string = return_string + " |  " + str(self.bytestring(int(source.info().getheader("Content-Length"))))
            #check for imgur
            if "i.imgur.com" in url: #we check the title of the album
                rex = '(.gif|.png|.jpeg|.img|.jpg|.bmp)\Z'  #common image formats, search at end of string
                search_res = re.search(rex, url)
                new_url = url.rstrip(search_res.group())
                img_title = self.get_url_info(new_url, True)
                if img_title is not None:
                    return_string = (img_title.lstrip()).rstrip() + " " + return_string

            return redirect_warning + return_string

    def yt_info(self, url):
        yt_ID =  re.search("(\?|\&)v=([a-zA-Z0-9_-]*)", url)
        
        if yt_ID is None:
             return None

        yt_ID = yt_ID.group()
        if "?v=" in yt_ID:
            yt_ID = yt_ID.partition("?v=")[2]
        elif "&v=" in yt_ID:
            yt_ID = yt_ID.partition("&v=")[2]
        
        yt_api_key = settings.yt_api_key
        yt_string_start = "https://www.googleapis.com/youtube/v3/videos?id="
        yt_string_end = "&part=snippet,statistics,contentDetails"
        api_url = yt_string_start + yt_ID + "&key=" + yt_api_key + yt_string_end

        logging.debug("api url:%s", api_url)

        try:
           result = simplejson.load(urllib2.urlopen(api_url))
        except:
            logging.debug("url_finder error: youtube error, either urllib or simplejosn load fail")
            return None
    
        if not result["items"]:
            logging.debug("url_finder error: youtube error, no info on video")
            return None

        l = result["items"][0]
        stats = l["statistics"]
        details = l["contentDetails"]
        snippet = l["snippet"]
    
        title = snippet["title"]
        duration = details["duration"].replace("PT", "")
        views =  stats["viewCount"]
        dislikes = stats["dislikeCount"]
        likes = stats["likeCount"]
        comments = stats["commentCount"]
        return "Youtube: " + title + " | " + duration +" |"  # additional info, not in use views: " + views +" | d: " + dislikes +" l: " + likes +" | comments: " + comments

    def get_title(self, source, url):

        #get the html
        try:
            t = lxml.html.parse(source)
        except:
            logging.debug("url_finder error: couldn't parse with lxml")
            return None
        
        try:
            string = t.find(".//title").text
        except:
            logging.debug("url_finder error: didn't find title tags")
            return None            

        return string

    def find_urls(self, text):
        URL_REGEX = re.compile(r'''((http://|https://)[^ <>'"{}|\\^`[\]]*)''')
        url_array = []
        for url in re.findall(URL_REGEX, text):
            url_array.append(url[0]) #only 0 because 1 will always just be http:// / https://
        return url_array

    def parse_msg(self, msg):
        url_info = []
        #first we search it for links, if any found, send message with info about them, if any
        for url in self.find_urls(msg):
            info =  self.get_url_info(url)
            #we encode into utf-8
            try:
                info = info.encode('utf-8')
            except:
                logging.debug("url_finder error: couldn't parse with lxml")
                info = None
            if info is not None:

                #the color code for the message (green), the 0x02 is just a hack
                color = "\x033\x02\x02"
                end_color =""
                #if NSFW found in msg, mark it red
                if re.search(r'(nsfw|NSFW)', msg) is not None:
                    color = "\x030,4\x02\x02"
                    end_color ="\0x03"
                #sanitizing the message
                #remove newlines etc.
                forbidden = ["\n", "\r", "\t", "\f", "\v"]
                for i in forbidden:
                    info = info.replace(i, " ")

                #remove any empty start
                info = info.lstrip()
                #make sure it isn't longer then 150
                info = info[0:150]

                info_message = '%s%s%s' % (color, info, end_color)
                url_info.append(info_message)

        return url_info

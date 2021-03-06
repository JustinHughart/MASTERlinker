import settings
import urllib2
import simplejson
import re

class trackip():
 
    def get_info(self, adress):
        api = "http://freegeoip.net/json/" + adress
        try:
            result = simplejson.load(urllib2.urlopen(api))
        except urllib2.HTTPError:
            return None

        response = "[" + adress + " | " + result["ip"] + " | country:  " + result["country_name"] + " | city: " + result["city"] + " | map link: "
        map_link = "http://www.openstreetmap.org/#map=11/" + str(result["latitude"]) +"/" + str(result["longitude"])
        response = response + map_link
        response = "\x033" + response + "]"
        return response

    def trackip(self, main_ref, msg_info):
        if msg_info["channel"] == settings.NICK:
            return None

        if msg_info["message"].lower().startswith("!track "):
            address = re.match("!track (\S+)", msg_info["message"].lower())
            if address:
                response = self.get_info(address.group(1))
                main_ref.send_msg(msg_info["channel"], response)

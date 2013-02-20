#Error: <class 'httplib.BadStatusLine'> while processing Oddities.S03E14.HDTV.x264-MiNDTHEGAP.mp4
# try again!
#Error: <class 'socket.error'> try again as well?


import sys
import os
import re
import shutil
from contextlib import closing
import hashlib # to calculate hash of torrents
import shelve  # to store file history
import urllib
import urllib2 # access episode data
import xml.etree.ElementTree as elementtree # parse episode XML data
import logging
import time

# 3rd party
import appdirs

# logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LEVELS = {'debug'   : logging.DEBUG,
          'info'    : logging.INFO,
          'warning' : logging.WARNING,
          'error'   : logging.ERROR,
          'critical': logging.CRITICAL
         }
LOG_FILE = "pictime.log"
DEF_LEVEL = 'info'

# file hashing
BLOCK_SIZE = 8192
HASH_METHOD = hashlib.sha1

APP_NAME = "process_shows"
DEVELOPER_NAME = "kylekawa"

# URI to get information about show episode
URI_TVRAGE = "http://services.tvrage.com/feeds/episodeinfo.php?"

# regex that pulls season and episode info.
re_pattern = r"^(?P<show>.+)s(?P<season>\d{1,2})e(?P<episode>\d{1,2})(e(?P<episode2>\d{1,2}))?.+\.(?P<ext>avi|mp4|mkv)$"

input_path  = r"D:\torrents"
#input_path  = r"D:\Torrents\Made sort script puke"
output_path = r"D:\TV Shows"

class ShowParseError(Exception):
    pass

def get_filehash(filename):
    "Get the file hash depending on the hash method: HASHMETHOD"
    retval = None
    hashobj = HASH_METHOD()
    with open(filename, "rb") as fileobj:
        while True:
            block = fileobj.read(BLOCK_SIZE)
            if block:
                hashobj.update(block)
            else:
                retval = hashobj.hexdigest()
                break
    return retval

def get_url_params(show, season, episode):
    "Takes show info, season # and episode # and contructs a URI param string"
    params = {"exact": "1"}
    params["show"] = show
    params["ep"] = "{}x{}".format(int(season), int(episode))
    return urllib.urlencode(params)

def get_show_folder(show, season):
    '''Get a string that can be used as a folder path from the show string.
    "The " is stripped and name is title cased'''
    mo = re.match("(the )?(?P<show>.+)", show, re.IGNORECASE)
    if not mo:
        raise ShowParseError
    show = mo.group("show").title()
    show_season = os.path.join(show, "S{:02d}".format(season))
    return show_season

def clean_path_string(in_str):
    "Certain characters cannot be used in file paths.  Replace/remove them"
    clean_str = re.sub(r"[/\\:|]", "-", in_str)
    clean_str = re.sub(r'[*?<>"]', "", clean_str)
    return clean_str

def get_episode_title(show, season, episode):
        uri = URI_TVRAGE + get_url_params(show, season, episode)
        total_retries = 5
        for count in range(total_retries):
            # try three times if it fails
            try:
                ep_xml = urllib2.urlopen(uri).read()
            except Exception as e:
                if count == total_retries - 1:
                    # we're on the last retry... quit.
                    logging.error("Failed to get episode info for: {} S{}E{}".format(show, season, episode))
                    raise
                print "Network error: {}".format(e)
                print "Retrying... ({}/{})".format(count, total_retries)
            else:
                # everything was okay, so break out of loop
                break
        
        xml_tree = elementtree.fromstring(ep_xml)
        title = xml_tree.find("episode/title").text
        asc_title = title.encode('ascii', 'ignore')
        return clean_path_string(asc_title) #make sure the title doesn't contain weirdness
    
def process_files(path, processed_files):
    #pprint(processed_files)
    #print "\n\n"
    
    regex = re.compile(re_pattern, re.IGNORECASE)

    #print(ep_data.read())
    for (cur_path, cur_dirs, cur_files) in os.walk(path):
        for cur_file in cur_files:
            full_path = os.path.join(cur_path, cur_file)
            if os.path.isfile(full_path):
                mo = re.match(regex, cur_file)
                if mo:
                    # at this point we have a file that we're potentially interested in
                    show = re.sub("\.", " ", mo.group("show")).strip()
                    season = int(mo.group("season"))
                    episode = int(mo.group("episode"))
                    episode2 = int(mo.group("episode2")) if mo.group("episode2") else None
                    ext = mo.group("ext") 
                    
                    # check its hash to see if we need to process                    
                    file_hash = get_filehash(full_path)
                    processed_file = processed_files.get(file_hash) 
                    if processed_file:
                        print("Found in history.  Skipping {} S{}E{}".format(show, season, episode))
                        continue
                    
                    # probably not needed since we're just processing files from the internet
                    # and they won't have these weird chars but why not
                    show = clean_path_string(show)
                                        
                    try:
                        title1 = get_episode_title(show, season, episode)
                        if episode2:
                            title2 = get_episode_title(show, season, episode2)
                            
                        # make sure folders exist... if not create them
                        show_folder = get_show_folder(show, season)
                        target_folder = os.path.join(output_path, show_folder)
                        if not os.path.exists(target_folder):
                            os.makedirs(target_folder)
                        
                        if not episode2:
                            filename = "S{:02d}E{:02d}.{}.{}".format(season, episode, 
                                                                     title1, ext)
                        else:
                            filename = "S{:02d}E{:02d}E{:02d}.{}-{}.{}".format(season, episode, episode2,
                                                                               title1, title2, ext)
                            
                        target_file = os.path.join(target_folder, filename)
                        if not os.path.exists(target_file):
                            shutil.copy2(full_path, target_file)
                            print '"{}"'.format(target_file)
                        else:
                            logging.warning("File already exists: {}".format(target_file))
                            print 'already exists: "{}"'.format(target_file)

                    except:
                        print "Error: {} while processing {}".format(sys.exc_info()[0], cur_file)
                    else:
                        # no error was raised... add it to file history!
                        logging.info("File processed: {}".format(target_file))
                        processed_files[file_hash] = target_file

dirs = appdirs.AppDirs(APP_NAME, DEVELOPER_NAME)
# initiliaze logging
logging.basicConfig(filename=os.path.join(dirs.user_data_dir, LOG_FILE),
                    level=LEVELS[DEF_LEVEL],
                    format=LOG_FORMAT)
logging.critical("Session started")

print "Script data:", dirs.user_data_dir, "\n"
shelf_dir = os.path.join(dirs.user_data_dir, "history")
if not os.path.exists(shelf_dir):
    os.makedirs(shelf_dir)
shelf_path = os.path.join(shelf_dir, "history.shelve")

with closing(shelve.open(shelf_path, writeback=True)) as file_history:
    processed_files = file_history.setdefault("p_dict", {})
    process_files(input_path, processed_files)
    file_history.sync()
    #pprint(processed_files)
    #pprint(file_history)

print("end")
logging.critical("Session finished")

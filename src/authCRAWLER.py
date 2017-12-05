#!/usr/bin/env python
'''
@uthor: Saleem

redditPANDA Pipeline,
crwals a subreddit
continually scrapes to get deleted comments.
'''
#----------------------------------------------------------------------
# Suppress pyc files
import sys
sys.dont_write_bytecode = True

#----------------------------------------------------------------------
# Imports
import ConfigParser
import time
from datetime import datetime
import json
import os
import praw
from catbot import Catbot
from sciurus import scheduler
from tastypy import POD
from pprint import pprint

#----------------------------------------------------------------------
# Helper methods


def removekeys(d, keys):
    for key in d.keys():
        if key not in keys:
	    try:
                del d[key]
            except KeyError:
                pass
    return


def makedir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
    return


def ConfigSectionMap(section, Config_obj):
    dict1 = {}
    options = Config_obj.options(section)
    for option in options:
        try:
            dict1[option] = Config_obj.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except BaseException:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1


def clean(body_text):
    body_text = ' '.join(body_text.split())
    body_text = ''.join([i if ord(i) < 128 else ' ' for i in body_text])
    return body_text


# Removing un-needed fields
comm_dict_keep= [
     'author',
     'body',
     'controversiality',
     'created_utc',
     'edited',
     'gilded',
     'id',
     'link_id',
     'name',
     'parent_id',
     'score',
     'subreddit']

post_dict_keep = [
     'author',
     'created_utc',
     'gilded',
     'id',
     'locked',
     'num_comments',
     'permalink',
     'score',
     'selftext',
     'subreddit',
     'title',
     'upvote_ratio',
     'url']

subs = ['loseit', 'relationships', 'TwoXChromosomes']

#----------------------------------------------------------------------
# Main Functions

def get_collected(subreddit):
    collected_posts = []
    trckpath = os.path.join(datapath, 'trackers', 'posttracker')
    track_pod = POD(trckpath)
    for key in track_pod._keys:
        if track_pod[key]:
            collected_posts.append(key)
    return collected_posts

def process_posts(subreddit, post_id):
    commpath = os.path.join(datapath, 'comments')
    post_path = os.path.join(commpath, post_id)
    post_files = sorted(os.listdir(post_path))
    post_files = [filename for filename in post_files if 'post' not in filename]
    
    comms_dict = {}
    miss_comms = set()
    
    for filename in post_files:
        post_file_path = os.path.join(post_path, filename)
        with open(post_file_path, 'r') as fin:
            all_lines = fin.readlines()
        for line in all_lines:
            j_obj = json.loads(line)
            c_id = j_obj['id']
            c_body = j_obj['body']
            if clean(c_body) == "[removed]":
                miss_comms.add(c_id)
            if c_id not in comms_dict:
                comms_dict[c_id] = []
            comms_dict[c_id].append(j_obj)
            
    auth_list = []
    for item in miss_comms:
        body = clean(comms_dict[item][0]['body'])
        if body != "[removed]":
            author = comms_dict[item][0]['author']
            if author != "[removed]" and author != "[deleted]":
                auth_list.append(author)

    return auth_list

#----------------------------------------------------------------------

config = ConfigParser.ConfigParser()
config.read('CONFIG.INI')
basepath = ConfigSectionMap("CommonConfigs", config)['datapath']

def main(subreddit):
    # Setup
    datapath = os.path.join(basepath, subreddit)
    posttrpath = os.path.join(datapath, 'trackers', 'processtracker')
    usertrpath = os.path.join(datapath, 'trackers', 'usertracker')
    makedir(posttrpath)
    makedir(usertrpath)
    processtrack_pod = POD(posttrpath)
    usertrack_pod = POD(usertrpath)

    
    collected_posts = get_collected(subreddit)
    auth_list = []

    for post_id in collected_posts:
        auth_list.extend(process_posts(subreddit, post_id))


'''
class panda:
    def __init__(self, subname):
        self.reddit = None
        self.catbot = None
        self.track_pod = None
        self.subreddit = subname
        self.previous_posts = []
        self.current_posts = []
        self.config = ConfigParser.ConfigParser()
        self.config.read('CONFIG.INI')
        self.basepath = ConfigSectionMap(
            "CommonConfigs", self.config)['datapath']
        self.datapath = os.path.join(self.basepath, self.subreddit)
        self.commpath = os.path.join(self.datapath, 'comments')
        self.userpath = os.path.join(self.datapath, 'users')
        self.trckpath = os.path.join(self.datapath, 'trackers', 'posttracker')
        return

    # Login into Reddit with config details
    def login(self):
        conf = ConfigSectionMap(self.subreddit, self.config)
        proxyport = str(conf['proxpyport'])
        os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:{}'.format(proxyport)
        os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:{}'.format(proxyport)
        comm = ConfigSectionMap("CommonConfigs", self.config)
        self.reddit = praw.Reddit(
            client_id=conf['client_id'],
            client_secret=conf['client_secret'],
            password=conf['password'],
            username=conf['username'],
            user_agent=conf['user_agent'])
        self.catbot = Catbot(
            comm['slack_secret'],
            conf['slack_channel'],
            comm['slack_user'])
        self.catbot.postToSlack(
            'redditPanda initalized for r/%s' %
            self.subreddit)
        return

    # Setup connection
    def setup(self):
        makedir(self.datapath)
        makedir(self.commpath)
        makedir(self.userpath)
        makedir(self.trckpath)
        self.reddit.read_only = True
        self.reddit.config.store_json_result = True
        self.track_pod = POD(self.trckpath)
        return

    # Retrieve a list of post made during the past 24 hours
    def get_posts(self):
        subreddit = self.reddit.subreddit(self.subreddit)

        time_now = datetime.utcnow()
        post_list = []
        for post in subreddit.new(limit=400):
            timediff = time_now - datetime.utcfromtimestamp(post.created_utc)
            if timediff.days == 0:
                post_list.append(post.id)
        return post_list

    # Retrieve a list of all comments made in a post
    def get_comments(self, post_id):
        post = self.reddit.submission(id=post_id)
        post.comments.replace_more(limit=0)
        all_comments = post.comments.list()
        post_dict = post.__dict__
        try:
            post_dict['author'] = post.author.name
        except AttributeError:
            post_dict['author'] = None
        post_dict['subreddit'] = post.subreddit.display_name
        post_dict['retrieved'] = int(time.time())
        removekeys(post_dict, post_dict_keep)
        z = json.dumps(post_dict)
        data_directory = os.path.join(self.commpath, post_id)
        makedir(data_directory)
        data_file = os.path.join(data_directory, "post_%s.txt" % post_id)
        with open(data_file, 'a') as fout:
            fout.write('%s\n' % z)
        return all_comments

    # Write retrieved comments to file
    def write_comments(self, post_id, all_comments):
        f_index = int(time.time())
        data_directory = os.path.join(self.commpath, post_id)
        makedir(data_directory)
        data_file = os.path.join(
            data_directory, "%s_%s.txt" %
            (post_id, f_index))
        with open(data_file, 'w') as fout:
            for comment in all_comments:
                comment_dict = comment.__dict__
                try:
                    comment_dict['author'] = comment.author.name
                except AttributeError:
                    comment_dict['author'] = None

                comment_dict['subreddit'] = comment.subreddit.display_name
                removekeys(comment_dict, comm_dict_keep)
                z = json.dumps(comment_dict)
                fout.write('%s\n' % z)
        return

    # tracker
    def update_tracker(self):
        done_posts = sorted(
            list(set(self.previous_posts) - set(self.current_posts)))
        for post_id in done_posts:
            self.track_pod[post_id] = True
        new_posts = sorted(
            list(set(self.current_posts) - set(self.previous_posts)))
        for post_id in new_posts:
            self.track_pod[post_id] = False
        print 'POD', len(self.track_pod._keys)
        print 'POD', self.track_pod._path
        self.track_pod.sync()
        return


    # The main method
    def redditPANDA(self):
        self.catbot.postToSlack('Runing ... %s' % str(datetime.now())[5:-10])
        self.current_posts = self.get_posts()
        self.update_tracker()
        print 'Getting comments for %s posts' % len(self.current_posts)
        for post_id in self.current_posts:
            all_comments = self.get_comments(post_id)
            print post_id, len(all_comments)
            self.write_comments(post_id, all_comments)
        print 'all files written... %s' % str(datetime.now())[5:-10]
        self.previous_posts = self.current_posts
        return


#----------------------------------------------------------------------
if __name__ == "__main__":

    # Login into Reddit
    subreddit = sys.argv[1]

    # Login into Reddit
    p = postpanda(subreddit)
    p.login()
    p.setup()

    # Schedule the scraping
    runPanda = scheduler.scheduler(m=20)
    runPanda.runit(p.redditPANDA)
'''
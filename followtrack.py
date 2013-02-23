#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Followtrack
#    Copyright 2013     Torsten Grote <t ät grobox.de>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, os
from optparse import OptionParser
import ConfigParser
import twitter
import ast
import shutil
from datetime import datetime

config_files = [
    'config.ini',                                                   # executing folder
    os.path.dirname(os.path.realpath(__file__)) + '/config.ini',    # real folder of script
    os.path.dirname(__file__) + '/config.ini'                       # folder of (symlinked) script
]

# Parse Command Line Options
usage = "usage: %prog option"
parser = OptionParser(usage=usage, version="%prog 0.1")
parser.add_option("-c", "--config", dest="config", action="store",      help="Add a new users and rebuild.")
parser.add_option("-d", "--debug",    dest="debug",  action="store_true", help="Print debugging output.")
(opt, args) = parser.parse_args()

if(opt.config != None):
    if(os.access(opt.config, os.R_OK)):
        # use supplied argument for config file first
        config_files.insert(0, opt.config)
    else:
        print "Error: Could not find config file '%s'." % opt.config
        sys.exit(1)

config = ConfigParser.SafeConfigParser()
used_config = config.read(config_files)

if(not config.has_section('Twitter')):
    print "Error: Could not find a valid config file."
    sys.exit(1)

# Set-up Twitter API
api = twitter.Api(
    consumer_key        = config.get('Twitter', 'consumer_key'),
    consumer_secret     = config.get('Twitter', 'consumer_secret'),
    access_token_key    = config.get('Twitter', 'access_token_key'),
    access_token_secret = config.get('Twitter', 'access_token_secret')
)

def main():
    if(opt.debug):
        print "Used configuration file(s): %s" % used_config

    (date, old_follower) = get_old_follower()
    cur_follower = get_cur_follower()

    save_follower(cur_follower)

    left = set(old_follower.keys()) - set(cur_follower.keys())
    new  = set(cur_follower.keys()) - set(old_follower.keys())

    text = get_mail_text(date, [old_follower[f] for f in left], [cur_follower[f] for f in new])

    send_mail(text)


def get_cur_follower():
    follower = api.GetFollowers()
    
    save = {}

    for f in follower:
        save[f.id] = f.screen_name
    
    return save


def save_follower(follower):
    fn = os.path.dirname(__file__) + '/follower'
    if(os.access(fn, os.R_OK)):
        shutil.copyfile(fn, fn + '.bak')

    f = open(fn, 'w')
    f.write(str(datetime.now()) + '\n')
    f.write(str(follower))
    f.close()


def get_old_follower():
    fn = os.path.dirname(__file__) + '/follower'
    if(os.access(fn, os.R_OK)):
        f = open(fn,'r')
        date = datetime.strptime(f.readline()[:-1], '%Y-%m-%d %H:%M:%S.%f')
        follower = ast.literal_eval(f.readline())
        f.close()

        return (date, follower)
    else:
        return (datetime.now(), {})


def get_mail_text(date, left, new):
    left_text = ''
    for f in left:
        left_text += '@' + f + '\n'
        left_text += '    ' + 'https://twitter.com/' + f + '\n\n'
    left_text = left_text[:-2]

    new_text = ''
    for f in new:
        new_text += '@' + f + '\n'
        new_text += '    ' + 'https://twitter.com/' + f + '\n\n'
    new_text = new_text[:-2]

    text = '''Hi,

Here are your Twitter changes since %s.

Your new follower are:
------------------------------------------
%s
------------------------------------------

You have been unfollowed by:
------------------------------------------
%s
------------------------------------------

Happy Tweeting!''' % ( date.strftime('%Y-%m-%d %H:%M'), new_text, left_text)
    return text


def send_mail(text):
    # Import smtplib for the actual sending function
    import smtplib

    # Import the email modules we'll need
    from email.mime.text import MIMEText

    msg = MIMEText(text)

    msg['Subject'] = 'Twitter Follower Changes'
    msg['From'] = 'Twitter Followtrack <followtrack@example.org>'
    msg['To'] = config.get('Mail', 'to')

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP('localhost')
    s.sendmail(msg['From'], [msg['To'],msg['Cc']], msg.as_string())
    s.quit()


if __name__ == '__main__':
    main()

# Copyright 2015 Telefonica Investigacion y Desarrollo, S.A.U
#
# This file is part of Orion Context Broker.
#
# Orion Context Broker is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Orion Context Broker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Orion Context Broker. If not, see http://www.gnu.org/licenses/.
#
# For those usages not covered by this license please contact with
# iot_support at tid dot es

__author__ = 'fermin'

from flask import Flask, request, Response
from requests import put 
import random, re, json
from tweet import tweet

TWITTER_MAX_LENGTH = 140
HASHTAG = '#CPBR8'

UNITS = {
    'hum': '%',
    'tem': 'C',
    'lum': '%'
}

RESET_MSG = 'reset'
UPDATE_URL = 'http://localhost:1026/v1/contextEntities/twitter/attributes/msg'

app = Flask(__name__)
host='localhost'
port=5000

def reset():
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    put(UPDATE_URL, data=json.dumps({'value': RESET_MSG}), headers=headers)

@app.route('/notify', methods=['POST'])
def notification():
    notification = request.json

    # Store all the attributes coming in the notification
    attrs = {}
    msg = ''
    for attr in notification['contextResponses'][0]['contextElement']['attributes']:
        name = attr['name']
        value = attr['value']
        if name == 'msg':
            msg = value
        else:
            if name in UNITS:
                unit = UNITS[name]
            else:
                unit = ''
            attrs[name] = value + unit

    # Debug
    #print 'msg: ' + msg
    #for key in attrs.keys():
    #    print key + " -> " + attrs[key]

    if msg == RESET_MSG:
        # The 'reset' message is not an actual one, thus nothing to Publish
        return Response(status=200)

    # We pass to lowercase, to make regex matching simpler, thus 'Give me', 'give me', 'Give Me' are all the same
    lc_msg = msg.lower()

    m = re.match('give me (.*)', lc_msg)
    # If the msg is a "Give me" one, then post the value of the attribute
    if m != None:
        # Take only the first letters of the attribute, thus 'Give me temperature' and 'Give me tem' work the same
        attr = m.group(1)[:3]
        if attr in attrs.keys():
            final_msg = 'Current ' + attr + ' at @FIware stand is ' + attrs[attr] + ' ' + HASHTAG 
        else:
            # Unknown attribute: nothing to publish
            return Response(200)
    else:
        # If the msg is a normal one, then pick two attribute at random
        attr1 = random.choice(attrs.keys())
        attr2 = random.choice(attrs.keys())
        while attr1 == attr2:
            attr2 = random.choice(attrs.keys())
        attrs_string = ' ' + attr1 + '=' + attrs[attr1] + ' ' + attr2 + '=' + attrs[attr2] + ' '
        max_user_msg = TWITTER_MAX_LENGTH - len(attrs_string) - len(HASHTAG)
        #print str(max_user_msg)
        final_msg = msg[:max_user_msg] + attrs_string + HASHTAG

    # Debug
    #print str(len(final_msg))
    #print final_msg

    # Tweet it!
    tweet(final_msg)

    # Before returning, we 'reset' the message. Otherwise, several consecutive msg with the same text
    # (e.g. 'Give me hum) will be ignored (except the first one)
    reset()

    return Response(status=200)

if __name__ == '__main__':
    app.run(host=host, port=port, debug=False)

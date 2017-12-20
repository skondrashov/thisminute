from __future__ import print_function
from __future__ import division

import re
from unidecode import unidecode

def get_words(tweet):
	tweet = re.sub('((\B@)|(\\bhttps?:\/\/))[^\\s]+', " ", tweet)
	tweet = re.sub('[^\w]+', " ", tweet)
	tweet = tweet.lower().strip()
	tweet = unicode(unidecode(tweet))
	return tweet.split()

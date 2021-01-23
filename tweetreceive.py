#!/usr/bin/env python
# coding: utf-8

import tweepy
import tensorflow as tf
import tensorflow_text
import re
import numpy as np
import os
import datetime
import logging

tf.get_logger().setLevel(logging.ERROR)
tf.autograph.set_verbosity(2)

# Next, set up the API and load the model



auth = tweepy.OAuthHandler(os.environ.get('API_KEY'), os.environ.get('API_SECRET'))
auth.set_access_token(os.environ.get('ACCESS_TOKEN'), os.environ.get('ACCESS_SECRET'))
api = tweepy.API(auth)



bert_model_path = "sentiment140_bert"
bert_model = tf.saved_model.load(bert_model_path)
def bert_preprocess(text):
    pat1 = r'@[A-Za-z0-9]+'
    pat2 = r'https?://[A-Za-z0-9./]+'
    combined_pat = r'|'.join((pat1, pat2))
    stripped = re.sub(combined_pat, '', text)
    try:
        clean = stripped.decode("utf-8-sig").replace(u"\ufffd", "?")
    except:
        clean = stripped
    letters_only = re.sub("[^a-zA-Z]", " ", clean)
    lower_case = letters_only.lower()
    # During the letters_only process two lines above, it has created unnecessay white spaces,
    # I will tokenize and join together to remove unneccessary white spaces
    return lower_case.strip()
preprocess = np.vectorize(bert_preprocess)


def getTweets(username):
    """
    Input: username
    Returns: List of tweets in last 30 days
    """
    thirty_earlier = datetime.datetime.utcnow()-datetime.timedelta(30)
    tweets = []
    for status in tweepy.Cursor(api.user_timeline,id=username).items():
        if status.created_at > thirty_earlier:
            tweets.append(status.text)
        else:
            break
    preprocessed = preprocess(np.array(tweets))
    predictions = tf.sigmoid(bert_model(tf.constant(preprocessed))) > 0.5
    return np.mean(predictions)


if __name__ == '__main__':
    input_name = 'users.txt'
    output_name = 'results.txt'
    with open(input_name, 'r') as f:
        with open(output_name,'w') as o:
            for line in f:
                user = line.strip()
                percent = round(getTweets(user)*100)
                o.write(user+'- '+str(percent)+'%\n')

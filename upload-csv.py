import requests
import base64
import tensorflow as tf
import tensorflow_text
import re
import numpy as np
import os
import tweepy
import datetime
import pandas as pd


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

def getSentiments(usernames):
    """
    Input: username
    Returns: List of tweets in last 30 days
    """
    thirty_earlier = datetime.datetime.utcnow()-datetime.timedelta(30)
    tweets = []
    indices = []
    ind = 0
    sentiments = []
    for username in usernames:
        indices.append(ind)
        for status in tweepy.Cursor(api.user_timeline,id=username).items():
            if status.created_at > thirty_earlier:
                tweets.append(status.text)
                ind += 1
            else:
                break
    indices.append(ind)
    preprocessed = preprocess(np.array(tweets))
    predictions = tf.sigmoid(bert_model(tf.constant(preprocessed)))
    for i in range(len(usernames)):
        sentiments.append(np.mean(predictions[indices[i]:indices[i+1]]))
    return sentiments

if __name__=='__main__':
    users_needed = []
    with open('users.txt', 'r') as f:
        for line in f:
            users_needed.append(line.strip())

    user = os.environ.get('WP_USER')
    password = os.environ.get('WP_PASSWORD')
    credentials = user + ':' + password
    token = base64.b64encode(credentials.encode())
    header = {'Authorization': 'Basic ' + token.decode('utf-8')}
    response = requests.get('https://unionpoll.com/wp-json/wp/v2/media')
    response = response.json()
    found = False
    for media in response:
        if 'users.csv' in media['source_url']:
            id = media['id']
            file_url = media['source_url']
            found = True
    assert found, "csv file not found"
    response = requests.get('https://unionpoll.com/wp-json/wp/v2/media/'+str(id))
    response = response.json()
    url = response['source_url']
    df = pd.read_csv(url)
    cols = list(df.columns)
    assert cols[0] == 'Date', 'First column must be Date'
    for user in users_needed:
        if user not in cols:
            df[user] = np.nan
            cols.append(user)


    day = datetime.datetime.today().strftime('%Y-%m-%d')
    if day == df['Date'].iloc[-1]:
        print('Already done')

    else:
        print('New day, getting predictions')
        preds = getSentiments(cols[1:])
        df.loc[len(df)] = [day] + preds
        df.to_csv('users.csv', index=False)
        files = {'file': open('users.csv', 'rb')}

        response = requests.delete('https://unionpoll.com/wp-json/wp/v2/media/'+str(id)+'/?force=1',headers=header)

        response = requests.post('https://unionpoll.com/wp-json/wp/v2/media',headers=header,files=files)
        os.remove('users.csv')

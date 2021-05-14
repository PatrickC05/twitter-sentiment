import requests
import base64
import re
import os
import datetime
import random

import tensorflow as tf
import tensorflow_text

import numpy as np
import pandas as pd

import tweepy
import plotly.graph_objects as go

print("Imports done")
auth = tweepy.OAuthHandler(os.environ.get('API_KEY'), os.environ.get('API_SECRET'))
auth.set_access_token(os.environ.get('ACCESS_TOKEN'), os.environ.get('ACCESS_SECRET'))
api = tweepy.API(auth,wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

MAX_SEARCH = 225
MEDIA_LINK = 'https://unionpoll.com/wp-json/wp/v2/media/'

bert_model_path = "sentiment140_bert"
bert_model = tf.saved_model.load(bert_model_path)
print("Sentiment model loaded")

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

def new_val(prob):
    if prob > 0.75:
        return 1
    elif prob < 0.25:
        return 0
    else:
        return 0.5

reformat = np.vectorize(new_val)

def getSentiments(queries,user_query):
    """
    Input: Queries
    Returns: List of sentiments
    """
    thirty_earlier = datetime.datetime.utcnow()-datetime.timedelta(30)

    tweets = []
    indices = []
    ind = 0
    sentiments = []
    for query in queries:
        indices.append(ind)
        if query is not None:
            print(query)
            if user_query:
                statuses = tweepy.Cursor(api.user_timeline,id=query).items()
            else:
                statuses = tweepy.Cursor(api.search, q=query).items(MAX_SEARCH)
            for status in statuses:
                if status.created_at > thirty_earlier:
                    tweets.append(status.text)
                    ind += 1
                else:
                    break
    indices.append(ind)

    print("Preprocessing tweets")

    preprocessed = preprocess(np.array(tweets))

    print("Making predictions")

    predictions = reformat(tf.sigmoid(bert_model(tf.constant(preprocessed))))

    for i in range(len(queries)):
        if indices[i+1] == indices[i]:
            sentiments.append(np.nan)
        else:
            sentiments.append(int(round(np.mean(predictions[indices[i]:indices[i+1]])*1000)))
    return sentiments


if __name__=='__main__':
    user = os.environ.get('WP_USER')
    password = os.environ.get('WP_PASSWORD')
    credentials = user + ':' + password
    token = base64.b64encode(credentials.encode())
    header = {'Authorization': 'Basic ' + token.decode('utf-8')}

    response = requests.get(MEDIA_LINK)
    files_total = response.json()
    files_needed = ['users', 'searches']


    for file in files_needed:
        queries_needed = []
        with open(file+'.txt', 'r') as f:
            for line in f:
                queries_needed.append(line.strip())


        found = False
        for media in files_total:
            if file + '.csv' in media['source_url']:
                id = media['id']
                file_url = media['source_url']
                found = True
                break


        assert found, "csv file not found"
        print("Retrieving file from "+file_url)

        df = pd.read_csv(file_url)
        cols = list(df.columns)
        assert cols[0] == 'Date', 'First column must be Date'

        skips = []
        for i,val in enumerate(cols):
            if val not in queries_needed:
                print(val, "removed from calculating")
                cols[i] = None

        for query in queries_needed:
            if query not in cols:
                print(query, " added to csv")
                df[query] = np.nan
                cols.append(query)

        day = datetime.datetime.today().strftime('%Y-%m-%d')

        if day in df['Date'].unique():
            print('Already done')

        else:
            print('New day, getting predictions')

            preds = getSentiments(cols[1:],'user' in file)

            print('Writing to csv and uploading')

            df.loc[len(df)] = [day] + preds
            df.to_csv(file+'.csv', index=False)
            files = {'file': open(file+'.csv', 'rb')}

            response = requests.delete(MEDIA_LINK+str(id)+'/?force=1',headers=header)

            response = requests.post(MEDIA_LINK,headers=header,files=files)

            if file == 'searches':
                print("Tweeting")

                x = df.iloc[-1]

                cols = list(df.columns)

                numcols = len(cols)

                chosen = 0

                used = []

                while chosen < 3:
                    using = random.randint(1,numcols-1)
                    if not pd.isnull(x[using]) and using not in used:
                        used.append(using)
                        chosen += 1

                tweet = 'New #StatisticallySignificant search analysis! Here is how positive these search terms are on Twitter! Stay tuned until the website is updated.\n\n'

                for i in used:
                    tweet += cols[i] + '- ' + str(float(x[i])/10) + '%\n'


                # tweet += '\nMore info at https://unionpoll.com'

                subset = df.tail(7)
                days = subset['Date'].tolist()
                subset = subset.drop(columns='Date')
                subset = subset.dropna(axis=1)
                subset /= 10
                results = subset.to_dict(orient='list')


                fig = go.Figure()


                for i, v in results.items():
                    fig.add_trace(go.Scatter(x=days, y=v, name=i, mode="lines+markers"))

                fig.update_layout(
                    title="Positive Sentiment of Search Terms",
                    xaxis=dict(title="Date", showline=True, showgrid=False),
                    yaxis=dict(range=[0,100], title="Positive Sentiment (%)", showgrid=True)
                )

                img_path = "tweet_img.png"

                fig.write_image(img_path)

                api.update_with_media(img_path, status=tweet)

                os.remove(img_path)

import pandas as pd
import numpy as np
import os
import random
import tweepy

import plotly.graph_objects as go


auth = tweepy.OAuthHandler(os.environ.get('API_KEY'), os.environ.get('API_SECRET'))
auth.set_access_token(os.environ.get('ACCESS_TOKEN'), os.environ.get('ACCESS_SECRET'))
api = tweepy.API(auth,wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

df = pd.read_csv('searches.csv')

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

tweet = 'New search analysis! Here is how positive these search terms are on Twitter! Stay tuned until the website is updated.\n\n'

for i in used:
    tweet += cols[i] + '- ' + str(int(float(x[i]))/10) + '%\n'

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

from flask import Flask, request, jsonify, render_template, Response
import joblib

from twscrape import API
import pandas as pd
from pytz import timezone
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
import sqlite3
from dotenv import load_dotenv
import os
import asyncio

app = Flask(__name__)
model = joblib.load('models/model.joblib')
api = API()
matplotlib.use('agg')
cur_keyword = None
scraped_data = None

async def setup():
    load_dotenv()
    X_CREDENTIAL = os.getenv('X_CREDENTIAL')
    PROXY = os.getenv('PROXY')
    await api.pool.add_account(*X_CREDENTIAL.split(','), proxy=PROXY)
    await api.pool.login_all()

def create_figure(df):
    cnt = df.sentiment.value_counts()

    fig, ax = plt.subplots(figsize=(9.2, 2))

    colors = ['green', 'orange']
    pd.DataFrame(cnt).T.plot(kind='barh', stacked=True, width=0.5, color=colors, ax=ax)

    for i, rect in enumerate(ax.patches):
        width = rect.get_width()
        height = rect.get_height()
        x = rect.get_x()
        y = rect.get_y()
        
        ax.text(x + width / 2, y + height / 2, cnt.iloc[i], ha='center', va='center', color='white', fontsize=12)

    ax.set_title(f"Latest X's sentiment for {request.args.get('keyword')}")
    ax.legend(ncols=2)
    ax.axis('off')

    return fig

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/predict', methods=['GET'])
def predict():
    text = request.args.get('text')
    return model.predict([text])[0]

@app.route('/scrape', methods=['GET'])
async def scrape():
    global cur_keyword, scraped_data
    keyword = request.args.get('keyword')

    try:
        if keyword == cur_keyword and scraped_data is not None:
            print('Same keyword, skipping scraping to save quota')
            return scraped_data.to_html(escape=False)
        cur_keyword = keyword

        # tweets_df = pd.DataFrame({'content': ['hi', 'lol', keyword], 'b': [2, 3, 4]})

        tweets = []
        
        cols = ['username', 'date', 'url', 'content']

        async for tweet in api.search(f"{keyword} lang:en", limit=30):
            tweets.append((tweet.user.username, tweet.date, tweet.url, tweet.rawContent))

        tweets_df = pd.DataFrame(tweets, columns=cols)
        tweets_df['date'] = tweets_df['date'].apply(lambda x: x.astimezone(timezone('Asia/Singapore')).strftime("%d-%m-%Y %H:%M:%S UTC%Z"))
        tweets_df['url'] = tweets_df['url'].apply(lambda x: f'<a href="{x}" target="_blank">{x}</a>')

        tweets_df['sentiment'] = model.predict(tweets_df.content)

        # scraped_data = tweets_df.to_json(orient='records', index=False)
        scraped_data = tweets_df
        return tweets_df.to_html(escape=False)
    
    except Exception as e:
        print(e)
        return 'There was an error, possibly due to hitting scrape limit for today. Please come back later.'

@app.route('/plot', methods=['GET'])
def plot():
    # df = pd.read_json(io.StringIO(scraped_data))
    df = scraped_data

    fig = create_figure(df)

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)

    return Response(output.getvalue(), mimetype='image/png')

async def main():
    await setup()
    app.run(host='0.0.0.0', port=7860)

if __name__ == '__main__':
    asyncio.run(main())
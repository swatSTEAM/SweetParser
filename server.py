#!/usr/bin/python3

from flask import Flask, render_template, session, request, redirect, url_for, Response, stream_with_context
import twicore as twi
import tweepy
import os

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
cfg = open(os.path.join(APP_ROOT, 'config.cfg'), "r").readlines()
cfg = [key.rstrip() for key in cfg]
app.secret_key = cfg[0]
app.consumer_key = cfg[1]
app.consumer_secret = cfg[2]
usersDB = {}

@app.route('/login')
def login():

    consumer_token = app.consumer_key
    consumer_secret = app.consumer_secret
    auth = tweepy.OAuthHandler(consumer_token, consumer_secret, 'http://127.0.0.1:5000/verify')
    try:
        # get the request tokens
        redirect_url = auth.get_authorization_url()
        session['request_token'] = auth.request_token
        return redirect(redirect_url)
    except tweepy.TweepError as e:
        return 'Login error'


@app.route("/verify")
def get_verification():

    # get the verifier key from the request url
    if not 'oauth_verifier' in request.args.keys():
        return redirect(url_for('index'))
    verifier = request.args['oauth_verifier']

    auth = tweepy.OAuthHandler(app.consumer_key,
                               app.consumer_secret)
    token = session['request_token']
    del session['request_token']

    auth.request_token = token

    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        return ('Error! Failed to get access token.')

    #now you have access!
    api = tweepy.API(auth)

    #store in a db
    session['username']=api.me().screen_name
    session['access_token']=auth.access_token
    session['access_token_secret']=auth.access_token_secret
    return redirect(url_for('index'))

def need_login():
    access_token = session.get('access_token')
    return access_token is None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        if need_login():
            return render_template('login.html')
        return render_template('index.html', username=session['username'])
    elif request.method == 'POST':
        error = None
        if request.form['password'] != 'ADMIN':
            error = 'Invalid admin Credentials. Please try again.'
            return render_template('login.html', error=error)
        else:
            session['username'] = "ADMIN"
            session['access_token'] = "ADMIN"
            session['access_token_secret'] = "ADMIN"
            return render_template('index.html', username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/process/<username>")
def progress(username, tweet_count=1000):
    if need_login():
        return "LOGIN_ERROR"
    return Response(stream_with_context(process(username, tweet_count)),
                    mimetype='text/event-stream')

def process(username, tweet_count):

    def sse_query(id, event, data):
        return "id:{_id} \nevent: {event}\ndata: {data}\n\n".format(
                _id=id, event=event, data=data)

    keys = {
        'consumer_key': app.consumer_key,
        'consumer_secret': app.consumer_secret,

        'access_token': session['access_token'],
        'access_token_secret': session['access_token_secret']
    }

    tweets = []
    auth = tweepy.OAuthHandler(keys['consumer_key'],
                               keys['consumer_secret'])
    if session['access_token'] != "ADMIN":
        auth.set_access_token(keys['access_token'],
                              keys['access_token_secret'])
    api = tweepy.API(auth)

    try:
        if int(api.get_user(username).statuses_count) == 0:
            sse_data = "User don't have any tweets"
            yield sse_query(2, "processing-failed", sse_data)
            return sse_data
    except tweepy.TweepError as e:
        yield sse_query(1, "verification-failed", str(e))
        return str(e)

    yield sse_query(0, "verification-success", "True")

    curr_count = 0
    try:
        for status in tweepy.Cursor(api.user_timeline, id=username).items(tweet_count):
            tweets.append(status)
            curr_count += 1
            sse_id = str(curr_count+2)
            sse_data = str([int(curr_count / tweet_count * 100),curr_count])
            sse_event = 'import-progress'
            yield sse_query(sse_id, sse_event, sse_data)
    except tweepy.TweepError as e:
        yield sse_query(2, "processing-failed", str(e))
        return str(e)


    result = twi.freq_an(tweets, 10)

    sse_id = str(curr_count+3)
    sse_event = 'last-item'
    sse_data = url_for('show_stat', username=username)
    usersDB[username] = result
    yield sse_query(sse_id, sse_event, sse_data)
    return "true"

@app.route('/<username>')
def show_stat(username):
    if username=='favicon.ico': # Seriously?
        return ''

    if need_login():
        return render_template('login.html')

    if not (username in usersDB.keys()):
        return redirect(url_for('index'))
    result = usersDB[username]
    words = result[0]
    mentions = result[1]
    statistic = result[2]
    urls = result[3]
    emos = result[4]
    tweet_count = result[5]
    topics = result[6]
    return render_template('user.html', username=username, tweet_count=tweet_count,
                           words=words, mentions=mentions,
                           statistic=statistic, urls=urls, emos=emos, topics=topics)

if __name__ == "__main__":
    app.run(debug=True, threaded=True)




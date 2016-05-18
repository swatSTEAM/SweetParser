import tweepy
import re
import nltk
# from flask import Flask, render_template, session, request, flash, redirect, url_for, send_file, Response
from nltk.corpus import stopwords
from nltk.tokenize import TweetTokenizer
from nltk.tokenize.casual import EMOTICON_RE
from many_stop_words import get_stop_words
from nltk.corpus import wordnet as wn
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem.porter import PorterStemmer
import pymorphy2
import gensim
from gensim import corpora, models


Lemmatizer = WordNetLemmatizer()
p_stemmer = PorterStemmer()
morph = pymorphy2.MorphAnalyzer()
english_vocab = set(w.lower() for w in nltk.corpus.words.words())

def freq_an(tweets, count):

    def LDA(texts):
        try:
            # turn our tokenized documents into a id <-> term dictionary
            dictionary = corpora.Dictionary(texts)

            # convert tokenized documents into a document-term matrix
            corpus = [dictionary.doc2bow(text) for text in texts]

            # generate LDA model
            ldamodel = gensim.models.ldamodel.LdaModel(corpus, num_topics=10, id2word=dictionary, passes=20)
            return ldamodel.print_topics(num_topics=10, num_words=3)
        except:
            return []


    def exist_russian(word):
        if str(morph.parse(word)[0].methods_stack[0][0]) != "<DictionaryAnalyzer>":
            return False
        else:
            return len(morph.parse(word)[0].methods_stack) == 1

    def parse(s):
        tweet_normalized = []
        def store(word, dic):
            if word in dic:
                dic[word] += 1
            else:
                dic[word] = 1

        # if s[0:2]!="RT":
        counted = False
        counter['num_tweets'] += 1
        statistic['chars'] += len(s)

        tknzr = TweetTokenizer(preserve_case=False, reduce_len=False, strip_handles=False)
        tweet_tokenized = tknzr.tokenize(s)
        statistic['words'] += len(tweet_tokenized)

        # word in tweet
        # tags = nltk.pos_tag(tweet_tokenized)
        for i in range(len(tweet_tokenized)):
            word = tweet_tokenized[i]
            if re.match(u'[\U0001f600-\U0001f650]', word):
                store(word, emo_raw)
            else:
                if not (re.match('(\http[s]?[:]?//.*)',word) or word.isdigit() or word in blackList or len(word)<2):
                    if not (re.match('(\@.*)',word)):
                        if EMOTICON_RE.match(word):
                            store(word, emo_raw)
                        else:
                            # Normal word
                            store(word, dic)
                            counter['all_words'] += 1
                            #LDA
                            if re.match(r"[A-z]+",word): #english
                                # wn_tag = penn_to_wn(tags[i][0])
                                new_word = Lemmatizer.lemmatize(word)
                                # if new_word == word:
                                # new_word = p_stemmer.stem(word)
                                tweet_normalized.append(new_word)
                                if word in english_vocab:
                                    counter['normal_words'] += 1
                            else:                        #russian
                                tweet_normalized.append(morph.parse(word)[0].normal_form)
                                if exist_russian(word):
                                    counter['normal_words'] += 1
                    else:
                        if not counted:
                            counter['num_men'] += 1
                            counted = True
                        store(word, men)
        return tweet_normalized


    def parseUrl(urls):
        for url in urls:
            url_short = (re.match(r"^(?:http[s]?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/\n]+)",
                                  url['expanded_url'])).group(1)
            if url_short in urls_raw:
                urls_raw[url_short] += 1
            else:
                urls_raw[url_short] = 1

    dic = {}
    men = {}
    urls_raw = {}
    emo_raw = {}

    counter = {
        'num_tweets': 0,
        'num_men': 0,
        'normal_words': 0,
        'all_words': 0
    }
    statistic = {
        'words': 0,
        'chars': 0,
        'mentions': 0,
        'retweets': 0,
        'literariness': 0
    }

    additional = ['...', '..','вообще', 'либо', 'ох']

    blackList = set(stopwords.words('russian')+stopwords.words('english')+list(get_stop_words("ru"))+
                    list(get_stop_words("en"))+additional)

    tweets_normalized = []
    for tweet in tweets:
        if tweet.text[0:4]!='RT @':
            tweets_normalized.append(set(parse(tweet.text)))
            parseUrl(tweet.entities['urls'])

    # f = open('tweets', "w")
    # f.write(str(tweets_normalized))
    # f.close()

    topics = LDA(tweets_normalized)

    tweet_count = len(tweets)
    try:
        statistic['words'] /= counter['num_tweets']
        statistic['chars'] /= counter['num_tweets']
        statistic['retweets'] = (tweet_count - counter['num_tweets']) / tweet_count * 100
        statistic['mentions'] = counter['num_men'] / counter['num_tweets'] * 100
    except:
        pass

    try:
        statistic['literariness'] = counter['normal_words']/counter['all_words']*100
    except:
        pass

    for key in statistic:
        statistic[key] = round(statistic[key])

    words = []
    mentions = []
    urls = []
    emos = []

    # sort
    for arr in ((words, dic), (mentions, men), (urls, urls_raw), (emos, emo_raw)):
        k = 0
        for i,j in sorted(arr[1].items(), key=lambda x: x[1], reverse=True):
            if k>count:
                break
            k+=1
            arr[0].append([i,j])

    return [words, mentions, statistic, urls, emos, tweet_count, topics]



if __name__ == "__main__":
    print("This is a module")
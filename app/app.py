import requests
import json
import datetime
from flask import Flask
from flask.ext.cache import Cache
from random import randint


app = Flask(__name__)


@app.route('/')
def index():
    return "Yo, it's working!"


if __name__ == "__main__":
    app.run()

WORDNIK_URL = 'http://api.wordnik.com:80/v4/'
API_KEY = '6b7418187bd740d53c01975443c56826e52ec538526c7875f'

cache = Cache(app, config={'CACHE_TYPE': 'simple'})


@cache.memoize(timeout=86400)
def get_auth_token():
    params = {
        'api_key': API_KEY,
        'password': 'jacksparrow'
    }

    response = requests.get(
        WORDNIK_URL + 'account.json/authenticate/raynaya', params=params)
    print(response.text)
    if response.status_code == 200:
        response = response.json()
        return response.get('token')
    # else:
    #   return json.dumps({'msg': 'Failed to get auth token'})


@cache.memoize(timeout=86400)
def get_word_list(url, params, headers):
    response = requests.get(url, params=params, headers=headers)
    print(response.text)
    if response.status_code != 200:
        return None

    return response.json()


@cache.memoize(timeout=604800)
@app.route('/get_usage/<word>', methods=['GET'])
def get_usage(word):
    word = word.lower()
    params = {
        'useCanonical': False,
        'api_key': 'a2a73e7b926c924fad7001ca3111acd55af2ffabf50eb4ae5'
    }
    try:
        # print(WORDNIK_URL + 'v4/word.json/{}/topExample'.format(word))
        response = requests.get(
            WORDNIK_URL + 'word.json/{}/topExample'.format(word), params=params)
        print(response.text)
        if response.status_code == 200:
            response = response.json()
            title = response.get('word')
            title = title.title()
            print(title)
            if not title:
                return json.dumps({'msg': 'Failed to get a word'})

            usage = response.get('text')
            if not usage:
                return json.dumps({'msg': 'Failed to get usage examples'})

            url = 'https://www.wordnik.com/words/{}'.format(word)

            payload = {

                'templates': [{
                    'title': 'Example',
                    'subtitle': usage,
                    'default_action': {
                        'type': 'web_url',
                        'url': url
                    },
                    'buttons': [
                        {
                            'title': 'Related Words',
                            'type': 'web_url',
                            'payload': url
                        }
                    ]
                }
                ]
            }
            return payload
        else:
            return None

    except Exception as e:
        print(e)
        return None


@app.route('/random_word/', methods=['GET'])
def random_word():
    auth_token = get_auth_token()
    if not auth_token:
        cache.delete_memoized(get_auth_token)
        return json.dumps({'msg': 'Failed to get auth token'})
    try:
        params = {
            'api_key': API_KEY
        }
        headers = {
            'auth_token': auth_token
        }
        wordList = get_word_list(
            WORDNIK_URL + 'wordList.json/wordbot/words', params, headers)

        if not wordList:
            return json.dumps({'msg': 'Failed to get wordList'})

        random_index = randint(0, len(wordList))
        word = wordList[random_index].get('word')

        params = {
            'limit': 1,
            'includeRelated': True,
            'sourceDictionaries': 'wiktionary',
            'useCanonical': False,
            'includeTags': False,
            'api_key': 'a2a73e7b926c924fad7001ca3111acd55af2ffabf50eb4ae5'
        }

        response = requests.get(
            WORDNIK_URL + 'word.json/{}/definitions'.format(word), params=params, headers=headers)
        if response.status_code != 200:
            return json.dumps({'msg': 'Failed to get wordDefinition'})

        response = response.json()
        meaning = response[0].get('text')
        partOfSpeech = response[0].get('partOfSpeech')

        url = 'https://www.wordnik.com/words/{}'.format(word)

        payload = {
            'data': {
                'type': 'carousel',
                'templates': [{
                        'title': '{}'.format(word.title()),
                        'subtitle': 'Definition: {}'.format(meaning),
                    'default_action': {
                            'type': 'web_url',
                            'url': url
                        },
                    'buttons': [{
                        "title": "See More",
                        "type": "postback",
                        "payload": "flow_B9BFF21F148E48B19808E517CE1FFBE2"
                    }
                    ]
                }
                ]
            }
        }
        usage_templates = get_usage(word)
        if usage_templates:
            payload['data']['templates'].extend(
                usage_templates['templates'])
        return json.dumps(payload)

    except Exception:
        return json.dumps({'msg': 'Failed to get a word'})


@app.route('/word_of_the_day/', methods=['GET'])
@cache.memoize(timeout=86400)
def word_of_the_day():
    # http://api.wordnik.com:80/v4/words.json/wordOfTheDay?date=2017-10-15&api_key=a2a73e7b926c924fad7001ca3111acd55af2ffabf50eb4ae5
    params = {
        'date': datetime.datetime.today().strftime('%Y-%m-%d'),
        'api_key': 'a2a73e7b926c924fad7001ca3111acd55af2ffabf50eb4ae5'
    }
    try:
        response = requests.get(
            WORDNIK_URL + 'words.json/wordOfTheDay', params=params)
        print(response.text)
        if response.status_code == 200:
            response = response.json()
            title = response.get('word')
            title = title.title()
            print(title)
            if not title:
                return json.dumps({'msg': 'Failed to get a word'})

            definitions = response.get('definitions')
            if definitions:
                meaning = definitions[0].get('text')
                if not meaning:
                    return json.dumps({'msg': 'Failed to get a meaning'})
            else:
                return json.dumps({'msg': 'Failed to get a definition'})
            print(meaning)

            note = response.get('note', '')
            partOfSpeech = definitions[0].get('partOfSpeech', '')
            url = 'https://www.wordnik.com/word-of-the-day'

            examples = response.get('examples',[])
            usage = ''
            for example in examples:
                usage = '{}\n - {}'.format(usage, example['text'])
           

            payload = {
                'data': {
                    'type': 'msg_options',
                    'text': 'Word Of the day : {}\n\nDefinition: {}\n\nPartOfSpeech: {}\n\nNote: {}\n\nHow to use{}'.format(title, meaning, partOfSpeech, note, usage),
                    'options' : [   
                    {
                        "text": "See a random word",
                        "postback": "flow_B9BFF21F148E48B19808E517CE1FFBE2"
                    }
                ]
                }
            }
            # if usage_templates:
            #     payload['data']['templates'].extend(
            #         usage_templates['templates'])

            return json.dumps(payload)
        else:
            return json.dumps({'msg': 'Failed to get a word'})
    except Exception:
        return json.dumps({'msg': 'Failed to get a word'}), 500

@app.route('/zoom_meeting', methods=['GET'])
def zoom_meeting():
    # http://api.wordnik.com:80/v4/words.json/wordOfTheDay?date=2017-10-15&api_key=a2a73e7b926c924fad7001ca3111acd55af2ffabf50eb4ae5
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzTzgwTGRWSFNYYXV3WUNVZG9UZlZBIiwiZXhwIjoxNTIzOTUxMTE5fQ.QXE0HuaffaMqYufWEe8aQCSrHHp2kjHnCViOr9dtAxs'
    }

    try:
        response = requests.get('https://api.zoom.us/v2/meetings/4564560909', headers=headers)
        print(response.text)
        if response.status_code == 200:
            response = response.json()
            join_url = response["join_url"]
            return json.dumps({"data": {"type": "carousel", "templates": [{"title": "Genius Bar", "subtitle": "Connect instantly to Genius Bar by clicking the button below", "buttons": [ {"type": "web_url","payload": join_url}]}]}})
        else:
            return json.dumps({"data": {"type": "text", "text": "Please try again later!"}}), 500
    except Exception:
        return json.dumps({"data": {"type": "text", "text": "Please try again later!"}}), 500

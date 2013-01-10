import re
import json
import urllib
from string import ascii_lowercase, punctuation, whitespace
from operator import itemgetter
from collections import defaultdict
from twisted.internet import reactor
from twisted.web.client import getPage
from twisted.python import log
from pyspades.server import chat_message
from pyspades.common import encode, decode
from pyspades.constants import *
from commands import add, admin, name, get_player

ANNOUNCE_TO_IRC = False

S_DETECTED = "Detected language '{lang}'. Future messages will be translated"
S_DETECTED_IRC = "* Language '{lang}' detected for {player}"
S_TRANSLATED_IRC = '* Message from {player} translated. Original message: {message}'
S_DISABLED = 'Translation service disabled'
S_ENABLED = 'Translation service enabled'
S_LANGUAGE = "{player}'s detected language is '{lang}'"
S_LANGUAGE_SET = "{player}'s language set to '{lang}'"
S_NOT_DETECTED_YET = "{player}'s language hasn't been detected yet"

@name('toggletranslate')
@admin
def toggle_translate(connection):
    protocol = connection.protocol
    protocol.translating = translating = not protocol.translating
    
    message = S_ENABLED if translating else S_DISABLED
    protocol.send_chat(message, irc = True)

def language(connection, player, lang = None):
    protocol = connection.protocol
    player = get_player(protocol, player)
    
    if lang is None:
        if player.language_detected:
            lang = player.language_pair[:2]
            return S_LANGUAGE.format(player = player.name, lang = lang)
        else:
            return S_NOT_DETECTED_YET.format(player = player.name)
    else:
        player.language_detected = True
        player.language_pair = lang + '|en'
        player.translating = lang != 'en'
        return S_LANGUAGE_SET.format(player = player.name, lang = lang)

add(toggle_translate)
add(language)

# stats from shams, 2012 jul 02
# vowel to consonant ratios from 4708 chat lines
# discarded outliers at 88%
# min 0.0133 max 1.5556 avg 0.6509 stddev 0.2508 - 4199 samples

TRANSLATE_BASE_URL = 'http://mymemory.translated.net/api/get?'
DETECT_BASE_URL = 'http://ws.detectlanguage.com/0.2/detect?'
VC_RATIO_MIN = 0.14
VC_RATIO_MAX = 3.0
BIG_LANGUAGE_MULTIPLIERS = {'xxx' : 0.0, 'en' : 10.0, 'pl' : 6.0, 'pt' : 5.0,
    'de' : 4.5, 'es' : 3.5, 'fi' : 2.0, 'hu' : 2.0, 'lt' : 2.0, 'sv' : 2.0}

vowels = 'aeiou'
consonants = ''.join(c for c in ascii_lowercase if c not in vowels)
language_patterns = {
    re.compile('ktos?\s+(z\s+)?(polak|pl)', re.IGNORECASE) : 'pl',
    re.compile('(tem|algue?m)\s+br', re.IGNORECASE) : 'pt'
}

def send_message(player, message, global_message):
    chat_message.player_id = player.player_id
    chat_message.chat_type = (CHAT_TEAM, CHAT_ALL)[int(global_message)]
    chat_message.value = message
    player.protocol.send_contained(chat_message)

def strip_message(s):
    return s.lower().strip(punctuation + whitespace)

def apply_script(protocol, connection, config):
    detectlanguage_key = config.get('detectlanguage_key', None)
    translation_memory = defaultdict(dict)
    detection_memory = {}
    
    if detectlanguage_key is None:
        print '(translation service offline - detectlanguage.com key not ' \
            'present in config)'
    
    def worth_translating(text):
        if len(text) <= 1:
            return False
        text = text.lower()
        vowel_count = sum(text.count(c) for c in vowels)
        consonant_count = sum(text.count(c) for c in consonants)
        if vowel_count == 0 or consonant_count == 0:
            return False
        vc_ratio = vowel_count / float(consonant_count)
        return vc_ratio >= VC_RATIO_MIN and vc_ratio <= VC_RATIO_MAX
    
    def request_detection(player, text):
        postdata = urllib.urlencode({'q' : text, 'key' : detectlanguage_key})
        d = getPage(
            DETECT_BASE_URL + postdata,
            method = 'GET',
            headers = {'User-Agent': ['pyspades']})
        d.addCallback(got_detection, player, text)
        d.addErrback(detection_failure)
        return d
    
    def got_detection(data, player, source_text):
        if player.disconnected:
            return
        detected = json.loads(data)['data']['detections']
        if not detected:
            return
        for d in detected:
            d['confidence'] *= BIG_LANGUAGE_MULTIPLIERS.get(d['language'], 1.0)
        detected.sort(key = itemgetter('confidence'), reverse = True)
        best = detected[0]
        lang, confidence = best['language'], best['confidence']
        if lang == 'xxx' or confidence < 0.45:
            lang = None
        detection_memory[strip_message(source_text)] = lang
        if lang is None:
            return
        player.start_translating(lang)
    
    def detection_failure(failure):
        pass
    
    def request_translation(player, lang, text, global_message):
        postdata = urllib.urlencode({'q' : text, 'langpair' : lang})
        d = getPage(
            TRANSLATE_BASE_URL + postdata,
            method = 'GET',
            headers = {'User-Agent': ['pyspades']})
        d.addCallback(got_translation, player, global_message, lang, text)
        d.addErrback(translation_failure, player, global_message, text)
        return d
    
    def got_translation(data, player, global_message, lang, source_text):
        if player.disconnected:
            return
        text = json.loads(data)['responseData']['translatedText']
        message = text.encode('cp1252', 'replace')
        translation_memory[lang][strip_message(source_text)] = message
        player.chat_translated(message, global_message, source_text)
    
    def translation_failure(failure, player, global_message, source_text):
        if player.disconnected:
            return
        player.chat_translated(source_text, global_message, source_text)
    
    class TranslateConnection(connection):
        language_detected = False
        language_pair = None
        translating = False
        
        def start_translating(self, lang):
            self.language_detected = True
            self.translating = lang != 'en'
            if self.translating:
                self.language_pair = lang + '|en'
                self.send_chat(S_DETECTED.format(lang = lang))
                self.protocol.irc_say(S_DETECTED_IRC.format(
                    lang = lang, player = self.name))
        
        def chat_translated(self, message, global_message, source_text):
            result = connection.on_chat(self, message, global_message)
            if result == False:
                return
            elif result is not None:
                message = result
            if ANNOUNCE_TO_IRC:
                self.protocol.irc_say(S_TRANSLATED_IRC.format(
                    player = self.name, message = source_text))
            send_message(self, message, global_message)
        
        def on_chat(self, value, global_message):
            muted = self.mute or (global_message and not
                self.protocol.global_chat)
            can_translate = detectlanguage_key and self.protocol.translating
            if not muted and can_translate and worth_translating(value):
                if self.translating:
                    try:
                        lang = self.language_pair[:2]
                        stripped = strip_message(value)
                        translation = translation_memory[lang][stripped]
                        stripped_translation = strip_message(translation)
                        if stripped != stripped_translation:
                            # translated message is substantially different
                            if ANNOUNCE_TO_IRC:
                                self.protocol.irc_say(S_TRANSLATED_IRC.format(
                                    player = player.name, message = value))
                            return connection.on_chat(self, translation,
                                global_message)
                    except KeyError:
                        pair = self.language_pair
                        request_translation(self, pair, value, global_message)
                        return False
                elif not self.language_detected:
                    try:
                        stripped = strip_message(value)
                        lang = detection_memory[stripped]
                        if lang is not None:
                            self.start_translating(lang)
                    except KeyError:
                        for pattern, lang in language_patterns.iteritems():
                            if pattern.search(value):
                                self.start_translating(lang)
                                break
                        if not self.language_detected:
                            request_detection(self, value)
            return connection.on_chat(self, value, global_message)
    
    class TranslateProtocol(protocol):
        translating = True
    
    return TranslateProtocol, TranslateConnection

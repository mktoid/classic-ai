from flask import Flask, request, jsonify

import warnings
warnings.filterwarnings("ignore") #если были warnings (а они были от используемых библиотек) - конкурсная система возвращала ошибку 500, заглушаем

import pandas as pd
import numpy as np
import re
import pickle
import bz2
import json
from gensim.models import FastText
from pyemd import emd
import pymorphy2
morph = pymorphy2.MorphAnalyzer()

# языковая модель сохранена через pickle, что дает заметный рост скорости открытия и уменьшает размер файла
with open('cc.ru.300.pkl', 'rb') as pickle_file:
    model = pickle.load(pickle_file)
    
vectors = model.wv

with bz2.BZ2File('words_accent.json.bz2') as fin:
    accents_dict = json.load(fin)
    
def sound_distance(word1, word2):
    """Фонетическое растояние на основе расстояния Левенштейна по окончаниям
    (число несовпадающих символов на соответствующих позициях)"""
    # эта и некоторые другие функции про фонетику взяты из https://github.com/sberbank-ai/classic-ai/tree/master/examples/phonetic-baseline
    suffix_len = 3
    suffix1 = (' ' * suffix_len + word1)[-suffix_len:]
    suffix2 = (' ' * suffix_len + word2)[-suffix_len:]

    distance = sum((ch1 != ch2) for ch1, ch2 in zip(suffix1, suffix2))
    return distance

def accent_syllable(word):
    """Номер ударного слога в слове"""
    default_accent = (syllables_count(word) + 1) // 2
    return accents_dict.get(word, default_accent)

def syllables_count(word):
    """Количество гласных букв (слогов) в слове"""
    return sum((ch in 'уеыаоэёяию') for ch in word)

def get_most_similar(word_topic, word_to_replace):
    """Подбор из похожих слов более подходящего на замену"""    

    result = word_topic

    try:    
        similar = vectors.most_similar(word_topic)
        similar.append( (word_topic, 1) )

        ms = pd.DataFrame()

        for s in similar:
            same_pos = 0
            origmorph = morph.parse(word_to_replace)[0]
            newmorph = morph.parse(s[0])[0]
            if origmorph.tag.POS == newmorph.tag.POS:
                same_pos = 1

            item = {}
            item['word'] = s[0]
            item['score'] = int(1 - s[1] + same_pos * 3 + (sound_distance(s[0],keyword) * 4) + abs(syllables_count(s[0])-syllables_count(keyword)) + abs(accent_syllable(s[0]) - accent_syllable(keyword)))
            
            ms = ms.append(item, ignore_index=True)

        result = ms.sort_values('score').iloc[0]['word'].lower()
    except:
        pass

    origmorph = morph.parse(word_to_replace)[0]

    inflection = set()
    if origmorph.tag.case != None:
        inflection.add(origmorph.tag.case)
    if origmorph.tag.number != None:
        inflection.add(origmorph.tag.number)
    if origmorph.tag.gender != None:
        inflection.add(origmorph.tag.gender)
    if origmorph.tag.voice != None:
        inflection.add(origmorph.tag.voice)
    if origmorph.tag.person != None:
        inflection.add(origmorph.tag.person)
    if origmorph.tag.tense != None:
        inflection.add(origmorph.tag.tense)

    try:
        return morph.parse(result)[0].inflect(inflection).word
    except:
        return result

get_most_similar('машинное', 'обучение') # прогрев первого запуска, чтобы не мерзнуть пол минуты на первом запросе

poems = pd.read_json('classic_poems.json')
poets = np.unique(poems['poet_id'])

app = Flask(__name__)

@app.route('/ready')
def ready():
    return 'OK'


@app.route('/generate/<poet_id>', methods=['POST'])
def generate(poet_id):
    request_data = request.get_json()
    seed = request_data['seed'].lower()

    poet = poet_id

    ###

    def cosine_similarity(a, b):
     try:
        vec_a = vectors.get_vector(a)
        vec_b = vectors.get_vector(b)
        cos_sim = np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
        return cos_sim
     except:
        return vectors.wmdistance(a,b)

    def get_poem(poet, seed):
        """генерирует стих"""
        reg = re.compile('[^а-яА-ЯёЁ \n]')

        poem = ''

        while len(poem.strip().split('\n')) < 6:
            if poet in poets:
                poem = poems[poems['poet_id']==poet].sample()['content'].values[0]
            else:
                poem = poems.sample()['content'].values[0]

        poem = reg.sub('', poem).strip().lower()

        poem = '\n'.join(poem.split('\n')[:np.random.choice([4,6])])

        injections = pd.DataFrame()

        for ins in seed.split():

            if len(ins) < 3:
                continue

            sim = pd.DataFrame()

            for s in poem.split('\n'):
                for w in s.split():
                    if len(w) > 3:
                        w = w.replace(',','')
                        item = {}
                        item['word'] = w
                        item['similarity'] = cosine_similarity(ins, w)
                        sim = sim.append(pd.DataFrame(item, index=[0]))

            replacement = {}
            try:
                replacement['from'] = sim.sort_values('similarity', ascending=False).iloc[0:]['word'].values[0]
                replacement['to'] =  get_most_similar(ins, replacement['from'])
                injections = injections.append(pd.DataFrame(replacement, index=[0]))
            except:
                pass

        txt = '\n'.join(poem.split('\n'))

        for index, row in injections.iterrows():
            txt = txt.replace(row['from'], row['to']) 
            
        txt_list = txt.split('\n')
        txt_new = ''
        for line in txt_list:
            txt_new += line[:117].capitalize() + '\n' 
        txt = txt_new.strip()

        return txt
    
    
    def valudate_poem(poem):
        """
        проверяет соответствие поэмы требованиям
        
        размер стиха — от 3 до 8 строк
        каждая строка содержит не более 120 символов
        строки разделяются символом \n
        пустые строки игнорируются
        """

        poem_list = poem.split('\n')

        lines_count = 0
        lines_maxlen = 0

        for line in poem_list:
            if len(line.strip()) > 1:
                lines_count += 1
            lines_maxlen = max(lines_maxlen, len(line))

        if lines_maxlen > 120:
            return False
        if lines_count < 3:
            return False
        if lines_count > 8:
            return False

        return True
    
    # генерируем несколько стихов и отбираем самое близкое к заданной теме
    # изначально планировался elasticsearch, но его не удалось запустить на конкурсной системе

    poems_df = pd.DataFrame()

    for _ in range(2):   
        poem = get_poem(poet, seed)
        poem_string = ''.join(poem.split('\n'))
        item = {}
        item["score"] = np.float(valudate_poem(poem)) * cosine_similarity(seed, poem_string)
        item["poem"] = poem

        poems_df = poems_df.append(pd.DataFrame(item, index=[0]))

    txt = poems_df.sort_values('score', ascending=False).iloc[0:]['poem'].values[0]
    
    ###

    return jsonify({'poem': txt})


if __name__ == '__main__':

    app.run(host='0.0.0.0', port=8000)



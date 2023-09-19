import requests
import json
import pandas as pd
import streamlit as st
from app_funcs import get_game_data
from app_funcs import predict_play

st.set_page_config(page_title="Predicting the next NFL play")
st.title("Predicting the next NFL play")
st.write('Will the next play be a run or  pass? A question as old as time itself. \
         And now, there is an AI to predict it. We have finally answered humanity\'s biggest question.')
st.write('This app pulls live NFL game data and uses a machine learning model to predict whether \
         the next play will be a run or a pass.')
st.code('Is it accurate?', language=None)
st.write('Sort of but not really. 70\% of the time, it works every time.')
st.code('Wouldn\'t a good model actually predict the outcome of the play?', language=None)
st.write('No. What does this look like, an AI model? Don\'t answer that.')

st.write('')
st.markdown('<h4>The ~Model~</h4>', unsafe_allow_html=True)
def get_games():
    url = 'http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
    r = requests.get(url)
    d = json.loads(r.text)

    # live events
    # get game that are either in progress (2) or completed 3
    games = [x['shortName'] for x in d['events'] if (x['status']['type']['id'].startswith('2')) or (x['status']['type']['id']=='3')]
    game_ids = [x['id'] for x in d['events'] if (x['status']['type']['id'].startswith('2')) or (x['status']['type']['id']=='3')]
    home_away_tms = [(x.split('@ ')[1], x.split(' @')[0]) for x in games]
    week = d['week']['number']

    return games, game_ids, home_away_tms, week

games, game_ids, home_away_tms, week = get_games()

st.write('')
st.write('Select a live game or one from last week and then select a play number.')
selected_game = st.selectbox(label='Select game', options=games)
selected_game_index = games.index(selected_game)
selected_gameid = game_ids[selected_game_index]
selected_tms = home_away_tms[selected_game_index]

if selected_game:
    url = f'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{selected_gameid}3/competitions/{selected_gameid}/plays?limit=300'
    r = requests.get(url)
    d = json.loads(r.text)
    num_of_plays = len(d['items'])
    st.session_state['num_plays'] = num_of_plays

play_options = ['last play'] + [x+1 for x in list(range(0, num_of_plays))]
selected_play = st.selectbox(label='Select play', options=play_options)
if selected_play == 'last play':
    play_index = -1
else:
    play_index = selected_play-1
st.session_state['play_index'] = play_index

if 'game_series' not in st.session_state:
    st.session_state['game_series'] = []

update_button = st.button('Update game data')
if update_button:
    st.session_state['update_button'] = 1
    get_game_data(week, selected_gameid, selected_tms)
    posteam = st.session_state['posteam']
    defteam = st.session_state['defteam']
    game_series = st.session_state['game_series']
    raw_game_data = st.session_state['raw_game_data']
    down_distance_text = st.session_state['down_text']
    home_team = selected_tms[0]
    away_team = selected_tms[1]

    if posteam == home_team:
        home_score = game_series['posteam_score']
        away_score = game_series['defteam_score']
    else:
        home_score = game_series['defteam_score']
        away_score = game_series['posteam_score']

    seconds = st.session_state['seconds']
    sec_remainder = seconds % 60
    min = (seconds / 60) - (sec_remainder/60)
    quarter = st.session_state['quarter']
    game_time = f'{min:.0f}:{int(sec_remainder):02} {quarter:.0f}Q'
    
    st.session_state['score_data'] = f'{away_team} {away_score:.0f}  {home_team} {home_score:.0f}'
    st.session_state['has_the_ball'] =f'{posteam} has the ball'
    st.session_state['game_time'] = game_time

if 'update_button' in st.session_state and st.session_state['update_button'] == 1:
    st.markdown(f"<h3 style='text-align: center;'>{st.session_state['score_data']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center;'>{st.session_state['game_time']}</h4>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center;'>&#127944  <img src=\"{st.session_state['posteam_logo']}\" width=50></h4>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center;'>{st.session_state['down_text']}</h4>", unsafe_allow_html=True)

if len(st.session_state['game_series'])>0:
    predict_button = st.button('Predict next play', on_click=predict_play())
    if predict_button:
        pred = st.session_state['pred']
        st.markdown(f"<h1 style='text-align: center;'>{pred[0].upper()}</h1>", unsafe_allow_html=True)
        actual_play = st.session_state["actual_play"]
        if actual_play.startswith('Pass'):
            outcome = 'pass'
        elif actual_play.startswith('Rush'):
            outcome = 'run'
        elif actual_play.startswith('Field '):
            outcome = 'field goal'
        elif actual_play.startswith('Punt'):
            outcome = 'punt'
        else: 
            outcome = actual_play

        if outcome == 'hasn\'t happened yet!':
            emoji = '&#10067'
        elif pred==outcome:
            emoji = '&#129304'
        else:
            emoji = '&#129335;'
        st.markdown(f'<h5>What actually happened: {outcome} {emoji}<h5>', unsafe_allow_html=True)

st.markdown('<p></p>', unsafe_allow_html=True)
st.markdown('<p></p>', unsafe_allow_html=True)
st.markdown('<p></p>', unsafe_allow_html=True)
st.markdown("<h4 style='text-align: left;'>Background</h4>", unsafe_allow_html=True)
source = 'https://github.com/cooperdff/nfl_data_py'
st.write('The underlying model is a random forest classifier with an out of sample accuracy of 70 percent. It was trained on data \
         from the 2022 NFL season via the [nfl_data_py](%s) python library' % source)

li = 'https://www.nls.website/'
st.write('This streamlit app and underlying model were developed \
        by [Nick Liu-Sontag](%s), a data scientist :nerd_face: in Brooklyn, NY' % li)



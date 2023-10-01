import pandas as pd
import streamlit as st
from app_funcs import get_game_data
from app_funcs import predict_play
from app_funcs import get_games
from app_funcs import generate_play_text
from app_funcs import get_ordinal
from datetime import date
st.set_page_config(page_title="Predicting the next NFL play")

### OPENING
st.title("Predicting the next NFL play")
st.write('Will the next play be a run or  pass? A question as old as time itself. \
         And now, there is an AI to predict it. We have finally answered humanity\'s biggest question.')
st.write('This app pulls live NFL game data and uses a machine learning model to predict whether \
         the next play will be a run or a pass.')
st.code('Is it accurate?', language=None)
st.write('Sort of but not really. 70\% of the time, it works every time.')
st.write('')

# get current week to generate list of historical weeks
week_1_end = date(2023, 9, 12) # the Tuesday after week 1
today = date.today()
current_week = int((today - week_1_end).days / 7 + 2)
week_list = ['Live'] + [f'Week {x}' for x in range(1, current_week)]

### Model
st.markdown('<h4>The ~Model~</h4>', unsafe_allow_html=True)

# select live or previous week
source = st.selectbox('Select source', options=week_list)
if source:
    # get list of all games historical or live
    games, game_ids, home_away_tms, week, game_data = get_games(source)

# if games are returned, populate remaining fields
if len(games) > 0:
    st.write('')
    selected_game = st.selectbox(label='Select game', options=games) # select game of interest

    # get home_away tuple and gameid (for API)
    selected_game_index = games.index(selected_game) 
    selected_tms = home_away_tms[selected_game_index]
    selected_gameid = game_ids[selected_game_index]
    if source!='Live':
        game_data = game_data[game_data['game_id']==selected_gameid].copy()

    # select the game and, if not live, the play #
    if selected_game:
        if source != 'Live':
            play_df = game_data[['qtr', 'posteam', 'down', 'ydstogo', 'play_id']].dropna()
            # create list of plays
            play_df['play_text'] = play_df["qtr"].astype(int).astype(str)  \
                                    + 'Q ' \
                                    + play_df["posteam"] \
                                    + ' - ' \
                                    + play_df["down"].apply(lambda x: get_ordinal(x)).astype(str) \
                                    + ' & ' \
                                    + play_df["ydstogo"].astype(int).astype(str) \
                                    
            play_index = st.selectbox(label='Select play', 
                                         options=play_df['play_id'], 
                                         format_func=lambda x: play_df.loc[play_df['play_id']==x, 'play_text'].values[0],
                                         key='play_index')
        else:
            # if the game is live, always go to the latest play
            play_index = -1 
            st.session_state['play_index'] = play_index

    # initalize game series in session state
    if 'game_series' not in st.session_state:
        st.session_state['game_series'] = []

    ### UPDATE GAME DATA
    update_button = st.button('Update game data')
    if update_button:
        st.session_state['update_button'] = 1
        get_game_data(source, week, selected_gameid, selected_tms, game_data)
        generate_play_text(selected_tms)

    # display game text
    if 'update_button' in st.session_state and st.session_state['update_button'] == 1:
        st.markdown(f"<h3 style='text-align: center;'>{st.session_state['score_data']}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: center;'>{st.session_state['game_time']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: center;'>&#127944  <img src=\"{st.session_state['posteam_logo']}\" width=50></h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: center;'>{st.session_state['down_text']}</h4>", unsafe_allow_html=True)

    ### PREDICT
    if len(st.session_state['game_series'])>0:
        predict_button = st.button('Predict play', on_click=predict_play())

        # get prediction
        if predict_button:
            pred = st.session_state['pred']
            st.markdown(f"<h1 style='text-align: center;'>PREDICTION: {pred[0].upper()}</h1>", unsafe_allow_html=True)
            actual_play = st.session_state["actual_play"]

            # API uses different play_type language
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

            # return eval against actual play
            if outcome == 'hasn\'t happened yet!':
                emoji = '&#10067'
            elif pred==outcome:
                emoji = '&#129304'
            else:
                emoji = '&#129335;'
            st.markdown('<p></p>', unsafe_allow_html=True)
            if source != 'Live':
                st.markdown(f'<h5>What actually happened: {outcome} {emoji}<h5>', unsafe_allow_html=True)
else:
    st.write('No live games! Try selecting a previous week')

### FOOTER
st.markdown('<p></p>', unsafe_allow_html=True)
st.markdown('<p></p>', unsafe_allow_html=True)
st.markdown('<p></p>', unsafe_allow_html=True)
st.markdown("<h4 style='text-align: left;'>Background</h4>", unsafe_allow_html=True)
source = 'https://github.com/cooperdff/nfl_data_py'
st.write('The underlying model is a random forest classifier with an out of sample accuracy of 70 percent. It was trained on data \
         from the 2022 NFL season via the [nfl_data_py](%s) python library.' % source)

li = 'https://www.nls.website/'
st.write('This streamlit app and underlying model were developed \
        by [Nick Liu-Sontag](%s), a data scientist :nerd_face: in Brooklyn, NY' % li)



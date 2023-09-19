def get_game_data(week, gameid, teams):
    import requests
    import json
    import pandas as pd
    import streamlit as st

    url = 'http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
    r = requests.get(url)
    d = json.loads(r.text)

    url = f'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{gameid}3/competitions/{gameid}/plays?limit=300'
    r = requests.get(url)
    d = json.loads(r.text)

    play_index = st.session_state['play_index']

    # get gameclock data
    raw_game_data = d['items'][play_index]
    seconds = d['items'][play_index]['clock']['value']
    quarter = d['items'][play_index]['period']['number']

    # create padding for seconds left in half and quarter
    if quarter==5: # if game is in OT
        game_seconds_remaining = seconds
        half_seconds_remaining = seconds
    else:
        game_pad = 15*60*(4-quarter) # there are 3x 15 min halves remaining in the game
        game_seconds_remaining = seconds + game_pad

        if quarter < 3:
            half_pad = 15*60*(2-quarter) # there is one 15 min quarter remaining in the half
            half_seconds_remaining = seconds+half_pad
        if quarter > 2:
            half_seconds_remaining = game_seconds_remaining

    down = d['items'][play_index]['end']['down']
    ydstogo = d['items'][play_index]['end']['distance']
    yardline = d['items'][play_index]['end']['yardsToEndzone']
    if ydstogo >= yardline:
        goal_to_go = 1.
    else:
        goal_to_go = 0.

    if down == -1:
        st.write('Invalid play, try the next one!')
        return pd.Series(), '', ''
    
    else: 
        down_distance_text = d['items'][play_index]['end']['downDistanceText']

        home_score = d['items'][play_index]['homeScore']
        away_score = d['items'][play_index]['awayScore']

        if play_index != -1:
            actual_play = d['items'][play_index+1]['type']['text']
        else:
            actual_play = 'hasn\'t happened yet!'

        url = d['items'][play_index]['team']['$ref']
        r = requests.get(url)
        d = json.loads(r.text)

        pos_team = d['abbreviation']
        def_team = teams[teams.index(pos_team) - 1]
        if pos_team == teams[0]:
            pos_score = home_score
            def_score = away_score
            is_pos_home = 1
        else:
            pos_score = away_score
            def_score = home_score
            is_pos_home = 0

        index = ['week',
                'yardline_100',
                'half_seconds_remaining',
                'game_seconds_remaining',
                'down',
                'goal_to_go',
                'ydstogo',
                'posteam_score',
                'defteam_score',
                'is_pos_home',]
        
        data = [week,
                yardline,
                half_seconds_remaining,
                game_seconds_remaining,
                down,
                goal_to_go,
                ydstogo,
                pos_score,
                def_score,
                is_pos_home]
        
        series = pd.Series(data, index=index)

        states = {'posteam':pos_team, 
                  'defteam':def_team, 
                  'game_series':series,
                  'raw_game_data':raw_game_data,
                  'down_text':down_distance_text,
                  'quarter':quarter,
                  'seconds':seconds,
                  'posteam_logo':d['logos'][-1]['href'],
                  'actual_play':actual_play}
        
        for s, v in states.items():
            st.session_state[s] = v
    
def predict_play():
    import pandas as pd
    import pickle
    import streamlit as st
    import numpy as np
    import pickle

    game_series = st.session_state['game_series']
    posteam = st.session_state['posteam']
    defteam = st.session_state['defteam']

    with open('data/feature_cols.pkl', 'rb') as f:
        input_cols = pickle.load(f)
    
    missing_cols = list(set(input_cols) - set(game_series.index))

    for c in missing_cols:
        game_series[c] = 0

    pos_team_col = f'posteam_{posteam}'
    def_team_col = f'defteam_{defteam}'
    game_series[pos_team_col] = 1
    game_series[def_team_col] = 1

    input_data = game_series.to_numpy().reshape(1, -1)

    # import model
    with open('model/rf_v1.pkl', 'rb') as f:
        model = pickle.load(f)
    
    pred = model.predict(input_data)

    st.session_state['pred'] = pred


    



def get_ordinal(number):
    '''
    Takes a number and returns the ordinal as a string
    '''
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    return f"{number:.0f}{suffix}"

def get_games(source):
    '''
    Takes in the source as Live or Week #
    Retrieves a list of games either from API or historical data
    Returns 
        list of games
        list of game ids
        list of tuples with (home_team, away_team)
        week #
        raw game data (to reduce re-querying)
    '''

    import requests
    import json

    if source == 'Live':
        url = 'http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
        r = requests.get(url)
        d = json.loads(r.text)

        # get game that are in progress (status.startswith 2)
        games = [x['shortName'] for x in d['events'] if (x['status']['type']['id'].startswith('2'))]
        game_ids = [x['id'] for x in d['events'] if (x['status']['type']['id'].startswith('2'))]
        home_away_tms = [(x.split('@ ')[1], x.split(' @')[0]) for x in games]
        week = d['week']['number']

        return games, game_ids, home_away_tms, week, d
    
    # if historical game
    else:
        import nfl_data_py as nfl
        week = int(source[-1]) # get week num
        data = nfl.import_pbp_data([2023], 
                           downcast=True, 
                           cache=False, 
                           alt_path=None, 
                           columns=[
                                    'play_id',
                                    'qtr',
                                    'home_team', 
                                    'away_team', 
                                    'week', 
                                    'posteam', 
                                    'defteam', 
                                    'yardline_100', 
                                    'half_seconds_remaining',
                                    'game_seconds_remaining', 
                                    'down',
                                    'goal_to_go',
                                    'ydstogo',
                                    'posteam_score',
                                    'defteam_score',
                                    'play_type',
                                    'game_id'
                                    ])
        
        # filter to selected week
        data = data[data['week']==week].copy()

        # sort plays into correct order
        data = data.sort_values(by=['game_seconds_remaining'], ascending=False)

        # get unique list of games
        game_df = data[['home_team', 'away_team', 'game_id']].drop_duplicates()

        home_away_tms = tuple(zip(game_df['home_team'], game_df['away_team']))
        games = list(game_df["away_team"].astype(str) + ' @ ' + game_df["home_team"].astype(str))
        game_ids = game_df['game_id'].to_list()

        return games, game_ids, home_away_tms, week, data

def get_game_data(source, week, gameid, teams, game_data):
    '''
    Produce play data based on the source, week and game
    Intakes game_data to prevent requerying for historical data
    Writes play information and game_series to session state 
    for display and input to prediction
    '''
    import pandas as pd
    import streamlit as st

    # get selected play
    play_index = st.session_state['play_index']

    if source == 'Live':
        import requests
        import json

        # query API for specific game
        url = f'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{gameid}3/competitions/{gameid}/plays?limit=300'
        r = requests.get(url)
        d = json.loads(r.text)

        # get gameclock data
        raw_game_data = d['items'][play_index]
        seconds = d['items'][play_index]['clock']['value']
        quarter = d['items'][play_index]['period']['number']

        # create padding for seconds left in half and quarter
        if quarter==5: # if game is in OT
            game_seconds_remaining = seconds
            half_seconds_remaining = seconds
        else:
            game_pad = 15*60*(4-quarter) 
            game_seconds_remaining = seconds + game_pad

            if quarter < 3:
                half_pad = 15*60*(2-quarter) 
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

            actual_play = d['items'][play_index+1]['type']['text']

            # API does not have a field for posessing team
            # it only provides the url for the team
            url = d['items'][play_index]['team']['$ref']
            r = requests.get(url)
            d = json.loads(r.text)
            pos_team = d['abbreviation']
            def_team = teams[teams.index(pos_team) - 1]

            # assign scores by home or away
            if pos_team == teams[0]:
                pos_score = home_score
                def_score = away_score
                is_pos_home = 1
            else:
                pos_score = away_score
                def_score = home_score
                is_pos_home = 0

            # create index for series that will be predicted from
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

            # organize data for series
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


    else:
        from app_funcs import get_ordinal
        game_data = game_data[[
                            'play_id',
                            'qtr',
                            'week',
                            'yardline_100',
                            'posteam',
                            'defteam',
                            'half_seconds_remaining',
                            'game_seconds_remaining',
                            'down',
                            'goal_to_go',
                            'ydstogo',
                            'posteam_score',
                            'defteam_score',
                            'play_type'
                            ]]
        
        # located selected play as series
        play_data = game_data[game_data['play_id']==play_index].iloc[0]

        # create is_pos_home col
        home_team = teams[0]
        play_data['is_pos_home'] = 0
        if play_data['posteam']==home_team:
            play_data['is_pos_home'] == 1

        # create down distance text
        down_text = get_ordinal(play_data['down'])
        down_distance_text = f'{down_text} & {play_data["ydstogo"]:.0f}'

        # assign vars for writing to session_state
        pos_team = play_data['posteam']
        def_team = play_data['defteam']
        raw_game_data = play_data
        quarter = play_data['qtr']
        quarters_left = 4-quarter
        seconds = play_data['game_seconds_remaining'] - (15*60*quarters_left)
        actual_play = play_data['play_type']

        # create series for prediction
        series = play_data[['week',
                            'yardline_100',
                            'half_seconds_remaining',
                            'game_seconds_remaining',
                            'down',
                            'goal_to_go',
                            'ydstogo',
                            'posteam_score',
                            'defteam_score',
                            'is_pos_home',]]
        
    logo = f'https://a.espncdn.com/i/teamlogos/nfl/500-dark/scoreboard/{pos_team}.png'

    # identify states to write to session_state
    states = {'posteam':pos_team, 
            'defteam':def_team, 
            'game_series':series,
            'raw_game_data':raw_game_data,
            'down_text':down_distance_text,
            'quarter':quarter,
            'seconds':seconds,
            'posteam_logo':logo,
            'actual_play':actual_play}
    
    for s, v in states.items():
        st.session_state[s] = v

def generate_play_text(selected_tms):
    '''
    Reads from session state and generates display text for play information
    Writes play text to session_state
    '''

    import streamlit as st

    # retrieve data from session state
    posteam = st.session_state['posteam']
    defteam = st.session_state['defteam']
    game_series = st.session_state['game_series']
    raw_game_data = st.session_state['raw_game_data']
    down_distance_text = st.session_state['down_text']
    home_team = selected_tms[0]
    away_team = selected_tms[1]

    # 
    if posteam == home_team:
        home_score = game_series['posteam_score']
        away_score = game_series['defteam_score']
    else:
        home_score = game_series['defteam_score']
        away_score = game_series['posteam_score']

    # game clock
    seconds = st.session_state['seconds']
    sec_remainder = seconds % 60
    min = (seconds / 60) - (sec_remainder/60)
    quarter = st.session_state['quarter']
    game_time = f'{min:.0f}:{int(sec_remainder):02} {quarter:.0f}Q'
    
    st.session_state['score_data'] = f'{away_team} {away_score:.0f} - {home_team} {home_score:.0f}'
    st.session_state['has_the_ball'] = f'{posteam} has the ball'
    st.session_state['game_time'] = game_time
    
def predict_play():
    '''
    Reads games series from session_state
    Loads RF model
    Predicts play_type
    '''

    import pandas as pd
    import pickle
    import streamlit as st
    import numpy as np
    import pickle

    # read in data
    game_series = st.session_state['game_series']
    posteam = st.session_state['posteam']
    defteam = st.session_state['defteam']

    # import feature cols used for training
    with open('data/feature_cols.pkl', 'rb') as f:
        input_cols = pickle.load(f)
    
    # get list of all cols and create if missing
    missing_cols = list(set(input_cols) - set(game_series.index))
    for c in missing_cols:
        game_series[c] = 0

    # find proper dummy cols and fill with 1 (e.g. posteam_CIN if CIN posseses the ball)
    pos_team_col = f'posteam_{posteam}'
    def_team_col = f'defteam_{defteam}'
    game_series[pos_team_col] = 1
    game_series[def_team_col] = 1

    input_data = game_series.to_numpy().reshape(1, -1)

    # import model
    with open('model/rf_v1.pkl', 'rb') as f:
        model = pickle.load(f)
    
    pred = model.predict(input_data)

    # write to session state
    st.session_state['pred'] = pred


    



import pandas as pd

def build_transition_matrix(group):
    group = group.sort_values('start_time')
    group['next_state'] = group['state_name'].shift(-1)
    group = group.dropna(subset=['next_state'])

    return pd.crosstab(
        group['state_name'],
        group['next_state'],
        normalize='index'
    )

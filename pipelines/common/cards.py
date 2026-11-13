from pathlib import Path

import pandas as pd

UNKNOWN_CARD_ALIAS = 'unknown_card'

def load_cards(path: str | Path) -> pd.DataFrame:

    # Strip spaces around names and values, so 'card_ref or alias' do not create a different alias
    cards = pd.read_csv(path, dtype=str).rename(columns=str.strip)
    cards = cards.apply(lambda col: col.str.strip())

    if not {'card_ref', 'alias'} <= set(cards.columns):
        raise ValueError('cards.csv needs columns card_ref and alias')

    if cards['card_ref'].duplicated().any() or cards['alias'].duplicated().any():
        raise ValueError('cards.csv: card_ref and alias must be unique')

    return cards
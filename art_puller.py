import os
import time
import sqlite3
import requests

DB_PATH = 'mtg_card_art.db'
ART_TAGS = ['woman', 'female', 'mom']
API_URL = 'https://api.scryfall.com/cards/search'


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            art_url TEXT NOT NULL,
            elo REAL DEFAULT 1200,
            games_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()


def save_card(card_id, name, art_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        INSERT OR IGNORE INTO cards (id, name, art_url)
        VALUES (?, ?, ?)
    ''', (card_id, name, art_url))

    conn.commit()
    conn.close()


def download_unique_card_art():
    query = ' OR '.join([f'art:{tag}' for tag in ART_TAGS])
    params = {'q': query, 'unique': 'art'}

    next_page_url = API_URL

    while next_page_url:
        time.sleep(0.05)
        response = requests.get(next_page_url, params=params)
        response.raise_for_status()
        data = response.json()

        for card in data['data']:
            if 'image_uris' in card:
                art_url = card['image_uris']['art_crop']
                print(f'Saving record for {card["name"]} ({card["id"]})')
                save_card(card['id'], card['name'], art_url)

        if not data.get('has_more', False):
            break

        next_page_url = data.get('next_page', None)
        params = None


if __name__ == '__main__':
    init_db()
    download_unique_card_art()
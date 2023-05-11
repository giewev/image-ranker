import sqlite3
import requests
import time

DB_PATH = 'mtg_card_art.db'

def update_card_info(card_id, artist, colors, cmc, types, mtg_set):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE cards
        SET artist=?, colors=?, cmc=?, types=?, mtg_set=?
        WHERE id=?
    ''', (artist, colors, cmc, types, mtg_set, card_id))
    conn.commit()
    conn.close()

def get_cards():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM cards')
    cards = [{'id': row[0]} for row in c.fetchall()]
    conn.close()
    return cards

def get_card_info(scryfall_id):
    response = requests.get(f'https://api.scryfall.com/cards/{scryfall_id}')
    card_data = response.json()
    print(card_data)

    artist = card_data.get('artist')
    colors = ','.join(card_data.get('colors', []))
    cmc = card_data.get('cmc')
    types = ','.join(card_data.get('type_line').split(' — '))
    mtg_set = card_data.get('mtg_set')

    return artist, colors, cmc, types, mtg_set

def main():
    cards = get_cards()

    for card in cards:
        artist, colors, cmc, types, mtg_set = get_card_info(card['id'])
        update_card_info(card['id'], artist, colors, cmc, types, mtg_set)
        # Pause for 50 ms between requests to respect Scryfall's rate limits
        time.sleep(0.05)

if __name__ == '__main__':
    main()

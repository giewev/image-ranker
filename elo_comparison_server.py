import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

DB_PATH = 'mtg_card_art.db'

app = Flask(__name__)


def get_random_cards(randomness=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, name, art_url, elo, games_played 
        FROM cards 
        WHERE invalid=0 
        ORDER BY ((RANDOM() / CAST(-9223372036854775808 AS REAL)*?) + (1/(games_played + 0.01))/5 + (elo/1200)) desc
        LIMIT 1'''
        , (randomness,))
    row = c.fetchone() 
    first_card = {'id': row[0], 'name': row[1], 'art_url': row[2], 'elo':row[3], 'games_played':row[4]}

    c.execute('''
        SELECT id, name, art_url, elo, games_played 
        FROM cards 
        WHERE 1=1
            AND invalid=0 
            AND id != ?
        ORDER BY ((RANDOM() / CAST(-9223372036854775808 AS REAL)*?) + (1/(games_played + 0.01))/5 - (abs(elo-?) / elo)) desc
        LIMIT 1'''
    , (first_card['id'], first_card['elo'], randomness))
    row = c.fetchone() 
    second_card = {'id': row[0], 'name': row[1], 'art_url': row[2], 'elo':row[3], 'games_played':row[4]}
    conn.close()
    return [first_card, second_card]

def update_elo(winner_id, loser_id, k=64, report=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if report:
        k *= 2
        winner_id, loser_id = loser_id, winner_id

    c.execute('SELECT elo FROM cards WHERE id=?', (winner_id,))
    winner_elo = c.fetchone()[0]
    c.execute('SELECT elo FROM cards WHERE id=?', (loser_id,))
    loser_elo = c.fetchone()[0]

    expected_outcome_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    expected_outcome_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / 400))

    winner_new_elo = winner_elo + k * (1 - expected_outcome_winner)
    loser_new_elo = loser_elo + k * (0 - expected_outcome_loser)

    if not report:
        c.execute('''
            UPDATE cards
            SET elo=?, games_played=games_played+1, wins=wins+1
            WHERE id=?
        ''', (winner_new_elo, winner_id))

    c.execute('''
        UPDATE cards
        SET elo=?, games_played=games_played+1
        WHERE id=?
    ''', (loser_new_elo, loser_id))

    conn.commit()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        winner_id = request.form['winner_id']
        loser_id = request.form['loser_id']
        report = request.form.get('report') == 'true'
        update_elo(winner_id, loser_id, report=report)
        return redirect(url_for('index'))

    cards = get_random_cards()
    return render_template('./index.html', cards=cards)

@app.route('/low_rank/', methods=['GET'])
@app.route('/low_rank/<int:page>', methods=['GET'])
def low_rank(page=1):
    images_per_page = 12
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM cards')
    total_images = c.fetchone()[0]
    total_pages = (total_images + images_per_page - 1) // images_per_page  # round up division

    c.execute('''
        SELECT id, name, art_url, elo, games_played 
        FROM cards
        WHERE invalid=0 
        ORDER BY elo ASC
        LIMIT ? OFFSET ?
    ''', (images_per_page, (page - 1) * images_per_page))
    cards = [{'id': row[0], 'name': row[1], 'art_url': row[2], 'elo': row[3], 'games_played': row[4]} for row in c.fetchall()]

    conn.close()
    return render_template('low_rank.html', cards=cards, page=page, total_pages=total_pages)

@app.route('/flag/<string:image_id>', methods=['POST'])
def flag(image_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE cards SET invalid=1 WHERE id=?', (image_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/invalid', methods=['GET'])
def invalid():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, art_url, elo, games_played FROM cards WHERE invalid=1')
    cards = [{'id': row[0], 'name': row[1], 'art_url': row[2], 'elo':row[3], 'games_played':row[4]} for row in c.fetchall()]
    conn.close()
    return render_template('./invalid.html', cards=cards)

if __name__ == '__main__':
    app.run(debug=True)

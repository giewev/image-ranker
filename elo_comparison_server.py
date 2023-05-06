import os
import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

DB_PATH = 'mtg_card_art.db'

app = Flask(__name__)


def get_random_cards():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, art_url, elo, games_played FROM cards ORDER BY games_played, RANDOM() LIMIT 2')
    cards = [{'id': row[0], 'name': row[1], 'art_url': row[2], 'elo':row[3], 'games_played':row[4]} for row in c.fetchall()]
    conn.close()
    return cards


def update_elo(winner_id, loser_id, k=32):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT elo FROM cards WHERE id=?', (winner_id,))
    winner_elo = c.fetchone()[0]
    c.execute('SELECT elo FROM cards WHERE id=?', (loser_id,))
    loser_elo = c.fetchone()[0]

    expected_outcome_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    expected_outcome_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / 400))

    winner_new_elo = winner_elo + k * (1 - expected_outcome_winner)
    loser_new_elo = loser_elo + k * (0 - expected_outcome_loser)

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
        update_elo(winner_id, loser_id)
        return redirect(url_for('index'))

    cards = get_random_cards()
    return render_template('./index.html', cards=cards)


if __name__ == '__main__':
    app.run(debug=True)
import random
import psycopg2
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
login = LoginManager(app)
login.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.password_hash = user_data['password_hash']

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

def get_user_by_id(id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('select username, password_hash from users where user_id = %s', (id,))
    row = c.fetchone()
    if row is None:
        return row 
    user_data = {'id':id, 'username':row[0], 'password_hash':row[1]}
    return user_data

@login.user_loader
def load_user(id):
    # Use psycopg2 to get the user by id from your database
    user_data = get_user_by_id(id)  # You need to implement this function
    return User(user_data) if user_data else None

def get_db_connection():
    db_creds = json.load(open('./db_creds.json'))
    return psycopg2.connect(
        host=db_creds['host'],
        dbname=db_creds['name'],
        user=db_creds['user'],
        password=db_creds['pass'],
        port=db_creds['port']
    )

def get_random_cards(randomness=1):
    conn = get_db_connection()
    c = conn.cursor()
    elo_lower_bound = random.choice([0, 1100, 1200])
    c.execute('''
        SELECT id, name, art_url, elo, games_played 
        FROM cards 
        WHERE invalid=0 
        AND elo > %s
        ORDER BY (random()*%s) + (1/(games_played + 0.01))/5 desc
        LIMIT 1'''
        , (elo_lower_bound, randomness,))
    row = c.fetchone() 
    first_card = {'id': row[0], 'name': row[1], 'art_url': row[2], 'elo':round(row[3], 1), 'games_played':row[4]}

    row = None
    max_elo_distance = 25
    while row is None:
        c.execute('''
            SELECT id, name, art_url, elo, games_played 
            FROM cards 
            WHERE 1=1
                AND invalid=0 
                AND id != %s
                AND abs(elo - %s) < %s
            ORDER BY (RANDOM()) desc
            LIMIT 1'''
        , (first_card['id'], first_card['elo'], max_elo_distance))
        row = c.fetchone() 
        max_elo_distance += 50

    second_card = {'id': row[0], 'name': row[1], 'art_url': row[2], 'elo':round(row[3], 1), 'games_played':row[4]}
    conn.close()
    return [first_card, second_card]

def update_elo(winner_id, loser_id, k=64, report=False):
    conn = get_db_connection()
    c = conn.cursor()

    if report:
        k *= 2
        winner_id, loser_id = loser_id, winner_id

    c.execute('SELECT elo FROM cards WHERE id=%s', (winner_id,))
    winner_elo = c.fetchone()[0]
    c.execute('SELECT elo FROM cards WHERE id=%s', (loser_id,))
    loser_elo = c.fetchone()[0]

    expected_outcome_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    expected_outcome_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / 400))

    winner_new_elo = winner_elo + k * (1 - expected_outcome_winner)
    loser_new_elo = loser_elo + k * (0 - expected_outcome_loser)

    if not report:
        c.execute('''
            UPDATE cards
            SET elo=%s, games_played=games_played+1, wins=wins+1
            WHERE id=%s
        ''', (winner_new_elo, winner_id))

        c.execute(
        "INSERT INTO votes (user_id, winner_id, loser_id) VALUES (%s, %s, %s)",
        (None, winner_id, loser_id)
        )

    c.execute('''
        UPDATE cards
        SET elo=%s, games_played=games_played+1
        WHERE id=%s
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if the username already exists
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        if cur.fetchone() is not None:
            flash('Please use a different username')
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)

        # Insert the new user data into the database
        cur.execute('INSERT INTO users (username, password_hash) VALUES (%s, %s)',
                    (username, password_hash))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()

        # Check if the username exists and get their password hash
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user_data = cur.fetchone()

        cur.close()
        conn.close()

        if user_data is None or not check_password_hash(user_data[2], password):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        user = User(user_data)
        login_user(user)

        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/low_rank/', methods=['GET'])
@app.route('/low_rank/<int:page>', methods=['GET'])
def low_rank(page=1):
    images_per_page = 12
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM cards')
    total_images = c.fetchone()[0]
    total_pages = (total_images + images_per_page - 1) // images_per_page  # round up division

    c.execute('''
        SELECT id, name, art_url, elo, games_played 
        FROM cards
        WHERE invalid=0 
        ORDER BY elo ASC, name ASC
        LIMIT %s OFFSET %s
    ''', (images_per_page, (page - 1) * images_per_page))
    cards = [{'id': row[0], 'name': row[1], 'art_url': row[2], 'elo': row[3], 'games_played': row[4]} for row in c.fetchall()]

    conn.close()
    return render_template('low_rank.html', cards=cards, page=page, total_pages=total_pages)

@app.route('/flag/<string:image_id>', methods=['POST'])
def flag(image_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE cards SET invalid=1 WHERE id=%s', (image_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/invalid', methods=['GET'])
def invalid():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, art_url, elo, games_played FROM cards WHERE invalid=1 order by name asc')
    cards = [{'id': row[0], 'name': row[1], 'art_url': row[2], 'elo':row[3], 'games_played':row[4]} for row in c.fetchall()]
    conn.close()
    return render_template('./invalid.html', cards=cards)

@app.route('/top', methods=['GET'])
def top():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, art_url, elo FROM cards WHERE invalid=0 ORDER BY elo DESC LIMIT 12')
    cards = [{'id': row[0], 'name': row[1], 'art_url': row[2], 'elo':row[3]} for row in c.fetchall()]
    conn.close()
    return render_template('./top.html', cards=cards)

@app.route('/stats', methods=['GET'])
def stats():
    conn = get_db_connection()
    c = conn.cursor()

    # Query for games played distribution
    c.execute('SELECT games_played, COUNT(*) FROM cards where invalid = 0 GROUP BY games_played order by 1 asc')
    games_played_data = c.fetchall()
    games_played_labels = [str(row[0]) for row in games_played_data]
    games_played_data = [row[1] for row in games_played_data]

    # Query for elo rating distribution
    c.execute('SELECT ROUND(elo / 50) * 50 AS elo_bucket, COUNT(*) FROM cards where invalid = 0 GROUP BY elo_bucket order by 1 asc')
    elo_data = c.fetchall()
    elo_labels = [str(row[0]) for row in elo_data]
    elo_data = [row[1] for row in elo_data]

    # get the artists with the most valid cards
    c.execute('SELECT artist, COUNT(*) AS num_cards FROM cards WHERE invalid=0 GROUP BY artist ORDER BY num_cards DESC LIMIT 10')
    top_artists_by_cards = c.fetchall()

    # get the artists with the highest average elo for their valid images
    c.execute('SELECT artist, AVG(elo) AS avg_elo FROM cards WHERE invalid=0 GROUP BY artist having count(*) >= 5 ORDER BY avg_elo DESC LIMIT 10')
    top_artists_by_elo = c.fetchall()

    conn.close()

    return render_template('./stats.html', 
                           games_played_labels=games_played_labels, 
                           games_played_data=games_played_data,
                           elo_labels=elo_labels,
                           elo_data=elo_data,
                           top_artists_by_cards=top_artists_by_cards, 
                           top_artists_by_elo=top_artists_by_elo)


if __name__ == '__main__':
    app.run(debug=True)

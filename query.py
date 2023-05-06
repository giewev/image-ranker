import sqlite3

# Connect to the SQLite database file
conn = sqlite3.connect('mtg_card_art.db')

# Create a cursor object
cur = conn.cursor()

# Run a SELECT query
cur.execute("SELECT * FROM cards ORDER BY games_played, RANDOM() LIMIT 2")
# cur.execute("PRAGMA table_info(cards)")

# Fetch the results of the query
results = cur.fetchall()

# Print the results
for row in results:
    print(row)

# Close the cursor and connection
cur.close()
conn.close()

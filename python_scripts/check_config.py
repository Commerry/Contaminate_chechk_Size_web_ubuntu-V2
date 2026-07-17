import sqlite3

conn = sqlite3.connect('system_config.db')
c = conn.cursor()
row = c.execute('SELECT value FROM system_config WHERE key="zoom_level"').fetchone()
print(f'Zoom level: {row[0] if row else "Not set"}')

# Reset zoom to 1.0
c.execute('UPDATE system_config SET value=? WHERE key=?', ('1.0', 'zoom_level'))
conn.commit()
print('Zoom reset to 1.0')

conn.close()

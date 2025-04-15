# import sqlite3

# conn = sqlite3.connect("project_accounting.db")
# cursor = conn.cursor()
# cursor.execute("SELECT * FROM users")
# users = cursor.fetchall()
# print(users)
# conn.close()

import hashlib
print(hashlib.__file__)
#print(hashlib.sha256("5900145".encode()).hexdigest())
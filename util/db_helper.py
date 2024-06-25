import sqlite3
conn = sqlite3.connect('universe_price.db')
cur = conn.cursor()

# cur.execute('''CREATE TABLE balance
#                (code varchar(6) PRIMARY KEY,
#                 bid_price int(20) NOT NULL,
#                 quantity int(20) NOT NULL,
#                 created_at varchar(14) NOT NULL,
#                 will_clear_at varchar(14)
#                )
#           ''')
#
# conn.commit()

# sql = "insert into balance(code, bid_price, quantity, created_at, will_clear_at) values(?, ?, ?, ?, ?)"
# cur.execute(sql, ('007700', 70000, 10, '20201222', 'today'))
# conn.commit()
# print(cur.rowcount)
#
# cur.execute('select * from balance')
# row = cur.fetchone()
# print(row)
#
# cur.execute('select code, created_at from balance')
# row = cur.fetchone()
# print(row)
#
# cur.execute('select * from balance')
# rows = cur.fetchall()
# print(rows)
#
#
# cur.execute('select * from balance')
# rows = cur.fetchall()
# for row in rows:
#     code, bid_price, quantity, created_at, will_clear_at = row
#     print(code, bid_price, quantity, created_at, will_clear_at)
#


sql = "select * from balance where code = :code"
cur.execute(sql, {"code": '007700'})
row = cur.fetchone()
print(row)

conn.close()
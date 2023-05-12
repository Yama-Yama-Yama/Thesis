import sqlite3

connection = sqlite3.connect('database.db')

with open('./schema.sql') as f:
    connection.executescript(f.read())

cur = connection.cursor()

cur.execute("INSERT INTO Patient_Data (birthday, taj, first_name, middle_name, last_name) VALUES(?,?,?,?,?)",('2000-12-19','123456789', 'First', 'Second', 'Middle'))
cur.execute("INSERT INTO Patient_Contact (patient_id, phone, email) VALUES(?,?,?)",('1','+36703118994', 'test@test.com'))
cur.execute("INSERT INTO Patient_Address (patient_id, country, post_code, city, street) VALUES(?,?,?,?,?)",('1','Hungary', '9700', 'Szombathely', 'Sugar'))
cur.execute("INSERT INTO Patient_Diagnosis (patient_id, image_name, result) VALUES(?,?,?)",('1','1.jpg','N0.93'))

connection.commit()
print("Success!")
connection.close()
from datetime import date
from datetime import time
from datetime import datetime
from datetime import timedelta
import psycopg2 as db
import random
import string
from psycopg2.extensions import AsIs


try:
        conn = db.connect(host="hostname",database="database_name", user="database_user", password="database_password")
        #issue commands
        cur = conn.cursor()
        cur.callproc('gen_inv',[5,'newCursor'])

        cur2 = conn.cursor('newCursor')
        total = 0
        for record in cur2:
            print(str(record[0]) + '.........' + str(record[1]))
            total += int(record[1])
            
        print('Total = ' + str(total))
        cur.close()
        cur2.close()
except (Exception, db.DatabaseError) as error:
        print(error)
finally:
    #close connection
    if conn is not None:
        conn.close()
        print('Database connection closed.')
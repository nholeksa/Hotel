from datetime import date
from datetime import time
from datetime import datetime
from datetime import timedelta
import psycopg2 as db
import random
import string
from psycopg2.extensions import AsIs

# This is the hotel's gui written by Nathaniel Holeksa


room_numbers = [100,101,102,103,104,200,201,202,203,204,300]



def main():
    global room_numbers
    #connect to database, check for errors
    conn = None
    try:
        conn = db.connect(host="comp421.cs.mcgill.ca",database="cs421", user="cs421g71", password="FOURWORDSoneword")
        #conn = db.connect(database="hotel", user="postgres", password="safe")
        #issue commands
        cur = conn.cursor()

        #! get the available employees
        delivery = getEmployees('bellhop',cur)
        cleaning = getEmployees('cleaning',cur)
        reception = getEmployees('reception',cur)




        #fetch the next ids for things
        # ! LOOK UP HOW TO RETURN FROM cursor       FETCH
        nextEID = get_next_id('eid','employees',cur)
        nextRID = get_next_id('id','reservation',cur)
        nextOEID = get_next_id('element_id','OrderElement',cur)
        nextSID = get_next_id('service_number','service',cur)
        nextTID = get_next_id('Transaction_Id','Transaction',cur)
        


        #prepare all the statements
        cur.execute("PREPARE addGuest as INSERT INTO guests VALUES($1,$2,$3,$4)")

        cur.execute('''PREPARE totalBill as 
                            SELECT sum(cost) FROM
                                (SELECT cost FROM roomDate
                                WHERE r_id = $1 
                                UNION ALL
                                SELECT cost FROM service
                                WHERE reservation_id = $1) t2''')
        # cur.execute("PREPARE addTransaction as INSERT INTO transaction VALUES($1,$2,$3,$4)")
        # cur.execute("PREPARE addReservation as INSERT INTO reservation VALUES($1,$2,$3,$4,$5)")
        cur.execute("PREPARE addService as INSERT INTO service VALUES($1,$2,$3,$4,$5,$6)")
        cur.execute("PREPARE addCleaning as INSERT INTO cleaning VALUES($1)")
        cur.execute("PREPARE addFoodOrder as INSERT INTO foodOrder VALUES($1)")
        cur.execute("PREPARE addOrderElement as INSERT INTO orderElement VALUES($1,$2,$3)")
        

    

        while(True):
            #prompt user    
            #get input
            option = input('''Please select an option: 
                        1) create guest
                        2) order cleaning
                        3) order food
                        4) total bill
                        5) increase minimum salary
                        6) quit\n''')

            if option == '1':
                name = valid_input(name_input)
                email = valid_input(email_input)
                phone = valid_input(phone_input)
                password = valid_input(password_input)

                #create guest, use prepared statements
                cur.execute("EXECUTE addGuest(%s,%s,%s,%s)", (email,phone,password,name))

                print('Guest added to database.')



            #order cleaning
            elif option == '2':
                #rid?
                rid = valid_input(rid_input)
                #room_number?
                room_number = valid_input(room_input)
                #cost?
                cost = valid_input(cost_input)

                cur.execute("EXECUTE addService(%s,%s,%s,%s,%s,%s)", (nextSID, random.choice(cleaning),datetime.today().date(), room_number, cost, rid))
                cur.execute("EXECUTE addCleaning(%s,%s,%s,%s,%s,%s)", (nextSID,))
                nextSID += 1
                
                print("Cleaning ordered!")


            #order food
            elif option == '3':
                #get rid
                rid = valid_input(rid_input)

                #get room number
                room_number = valid_input(room_input)

                #pull from the menu
                cur.execute('''SELECT name, cost FROM food''')

                items = cur.fetchall()
                length = len(items)
                counter = 1
                for item in items:
                    print(str(counter) + ") " + str(item[0]) + "..." + str(item[1]))
                    counter += 1


                #get the items that will be ordered
                while True:
                    inp = input("Please enter the numbers of food items you would like to order followed by commas: (e.g 1,1,2,4,5) ")

                    order = inp.split(',')
                    parsed_order = []

                    #check that the input is what the database expects
                    cost = 0
                    try:
                        for i in range(len(order)):
                            print(order[i])
                            #cast to int
                            parsed_order.append(int(order[i]))

                            #make sure it is a valid item
                            if parsed_order[i] > length or parsed_order[i] < 1:
                                raise TypeError()

                            cost += items[parsed_order[i]-1][1]

                    except (TypeError, ValueError):
                        print("Invalid input, please try again")
                        continue

                    
                    if len(parsed_order) < 1:
                        print("No food ordered")
                        break

                    cur.execute("EXECUTE addService (%s,%s,%s,%s,%s,%s)", (nextSID, random.choice(delivery),datetime.today().date(), room_number, cost, rid))
                    cur.execute("EXECUTE addFoodOrder (%s)",(nextSID,))
                    

                    for i in range(len(parsed_order)):
                        #create food order and order elements
                        cur.execute("EXECUTE addOrderElement (%s,%s,%s)", (nextOEID, nextSID, parsed_order[i]))
                        nextOEID += 1
                        

                    nextSID += 1
                    print("Food order placed")
                    break


    
            #total bill
            elif option == '4':
                rid = valid_input(rid_input)
                #combine all services + roomDate costs associated with the reservation ID 
                cur.execute('EXECUTE totalBill (%s)', (rid,))

                totalCost = cur.fetchone()

                try:
                    totalCost = totalCost[0]
                    
                    print("The total cost of the stay is " + str(totalCost))
                except (TypeError,ValueError):
                    print("There are no items associated to the rid.") 
                

                

                pass
            #increase minimum wage
            elif option == '5':
                wage = valid_input(salary_input)
                cur.execute('UPDATE employees SET salary = %s WHERE salary < %s', (wage, wage))

                print("Increased minimum salary to " + str(wage) + ".")
                
            #quit
            elif option == '6':
                print("Exiting program.")
                break
            else:
                print("Please select a valid option.")
                continue
            #commit the changes to the database
            conn.commit()

        cur.close()
          
    except (Exception, db.DatabaseError) as error:
        print(error)
    finally:
        #close connection
        if conn is not None:
            conn.close()
            print('Database connection closed.')
    

#check if the given email belongs to a guest in the database
def isGuest(email, cur):
    cur.execute("SELECT count(email) FROM guests WHERE email = %s", (email,))

    count = cur.fetchone()

    try:
        count = count[0]
        if count <= 0:
            return False
        return True
    except (TypeError, ValueError):
        print("Something went wrong with the guest email check.")
        return False


def get_next_id(idName, tableName, cur):
    command = 'SELECT max({}) FROM {}'.format(idName,tableName)
    cur.execute(command)
    nextId = cur.fetchone()

    if nextId is None:
        raise Exception("No records in {}, database is setup incorrectly. Exiting now.".format(tableName)) 
    
    
    return (nextId[0] + 1)


def rid_input():
    rid = input("Please enter the reservation id.\n")
    try:
        val = int(rid)
        if not (val > 0 and val < 68):     #! CHANGE TO NEXT ID
            raise ValueError()
        return True, val
    except ValueError:
        print("That is not a valid room number.")
        return False, None
    
def cost_input():
    cost = input("How much will it cost?\n")

    try: 
        val = float(cost)
        if val < 0:
            raise ValueError()
        return True, val
    except ValueError:
        print("That is not a valid cost.\n Please enter a positive float.")
        return False, None

def room_input():
    room_number = input("Please enter a room number\n")

    try:
        val = float(room_number)
        if val not in room_numbers:
            raise ValueError()
        return True, val
    except ValueError:
        print("That is not a valid room number.")
        return False, None

def salary_input():
    # get input, ensure it is a positive number
    salary = input("Please enter new minimum salary.")

    try:
        val = float(salary)
        print(val)
        if val < 0:
            raise ValueError()
        return True, val
    except ValueError:
        print("That is not a valid salary.")
        return False, None


def password_input():
    inp = input("Please enter a password")

    if len(inp) > 25:
        print("Input too long, please limit to 25 chars")
        return False, None
    return True, inp

def name_input():
    inp = input("Please enter their full name:")
    if len(inp) > 25:
        print("Input too long, please limit to 25 chars")
        return False, None
    return True, inp


def email_input():
    inp = input("Please enter their email:")
    #just checking length since prepared statements protect us from injection attacks
    if len(inp) > 254 or len(inp) < 1:
        return False, None
    return True, inp

def phone_input():
    inp = input("Please enter a valid phone number:")
    #just checking length since prepared statements protect us from injection attacks
    if len(inp) > 15 or len(inp) <= 7:
        return False, None
    return True, inp

def valid_input(input_fnc):
    valid = False
    inp = None
    while(not valid):
        
        valid, inp = input_fnc()

        if not valid:
            print("invalid input, please try again.")
    
    return inp


def getEmployees(position, cur):
   
    cur.execute('SELECT eid FROM employees WHERE position = %s',(position,))

    empl = cur.fetchall()
    eid_list = []
    
    try:
        for e in empl:
            eid_list.append(e[0])
    except (TypeError, ValueError):
        print("INTERNAL PROBLEMS")
        raise Exception()
    
    return eid_list

if __name__ == '__main__':
    main()
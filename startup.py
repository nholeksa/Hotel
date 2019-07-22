
from datetime import date
from datetime import time
from datetime import datetime
from datetime import timedelta
import psycopg2 as db
import random
import string
from psycopg2.extensions import AsIs


#global vars, I know its bad practice but it works
cur            = None
conn           = None
rooms          = []
reservations   = []
kitchenStaff   = []
cleaningStaff  = []
receptionStaff = []
serviceNumber  = 1
orderElementId = 1
reservationId  = 1


#helpful data for generation
roomTypes = [('single',200,300),('double',500,600),('suite',1000,1200)]
foods = [('Caesar Salad',10,1),('Cream of Mushroom Soup',8,2),('Chicken Pesto Fusilli',18,3),('Sirloin Steak',30,4),('Ribs',27,5),('Chicken BLT',15,6),
         ('Salmon Filet',27,7),('Black Angus Burger',24,8),('Chocolate Mousse Cake',11,9), ('Tiramisu',11,10)]
positions = ['manager','bellhop','bellhop','reception','reception','kitchen','kitchen','kitchen','cleaning','cleaning','cleaning']


#used https://github.com/arineng/arincli/blob/master/lib/male-first-names.txt
#and  https://github.com/arineng/arincli/blob/master/lib/last-names.txt
#for generating names

# used https://github.com/zopefoundation/z3c.datagenerator/blob/master/src/z3c/datagenerator/us-street-names.txt
# for street names


#script data structure for tracking DATES
class Guests:
    def __init__(self, email, phone, password, full_name):
        self.email = email
        self.phone = phone
        self.password = password
        self.full_name = full_name
        self.reservations = []


class Employee:
    def __init__(self, eID, name, position, address, phone, salary):
        self.eID = eID
        self.name = name
        self.position = position
        self.address = address
        self.phone = phone
        self.salary = salary
    

class Reservation:
    def __init__(self,guest, duration, rooms):
        global cur, reservationId
        self.Transaction = None
        self.email = guest.email
        self.id = reservationId
        
        
        #increment reservationId
        reservationId += 1

        #pick some dates, find available room(s)
     
        self.booked_rooms = []

        #keep trying dates until something works
        while True:
           
            self.startDate = date(2017,8,1) + timedelta(days=random.randint(0,700))
            self.endDate = self.startDate + timedelta(duration - 1)

            #check if the guests already have a booking during this date range
            if not self.conflict(self.startDate, self.endDate, guest.reservations): 
                #find some rooms book if they work
                
                self.booked_rooms = availableRooms(self, self.startDate, self.endDate, rooms, duration, self.id)

                #if we find rooms to stay in we break
                if len(self.booked_rooms) != 0:
                    break
                else: 
                    continue

        #did a you call to book?
        if random.random() <= 0.3:
            #create an entry in "books"
            bookReservation(self.id)
        
       
        #if it is past the start of reso 
        if self.startDate <=  datetime.now().date() and len(self.booked_rooms) > 0:
           
            #did we order food? (small chance to reduce table size)
            if random.random() <= 0.2:
                room = random.choice(self.booked_rooms)
                roomno = room.room_number
          
                foodOrderCreation(self.id, roomno, self.startDate, duration)
                

            #did we get a room cleaning? small chance
            if random.random() <= 0.2:
                room = random.choice(self.booked_rooms)
                roomno = room.room_number
        
                cleaningCreation(self.id, roomno, self.startDate, duration)




    #check if there is a conflict in reservations
    def conflict(self, startDate, endDate, others):
        for reso in others:
            if max(startDate, reso.startDate) <= min(endDate, reso.endDate):
                return True

        return False


class Transaction:
    def __init__(self,id, transaction_date, email):
        global cur

    
        self.date = transaction_date
        self.id = id
        self.payment = random.choice(["Mastercard","Visa","Amex","Cheque","Paypal","Cash"])
        self.email = email

        #write to the table
        command = "INSERT INTO Transaction VALUES(%s,%s,%s,%s)"
        cur.execute(command, (self.id, self.payment, email, self.date))

#check if there is any available number of rooms for the date range
def availableRooms(reso, startDate, endDate, number, duration, r_id):
    global rooms
    to_book = []
    room_numbers = []
    shuffled = rooms.copy()
    random.shuffle(shuffled)


    for room in shuffled:

        
        if room.isAvailable(startDate,endDate):
            
            to_book.append(room)
        
        if len(to_book) == number:
            #create transaction
            reso.transaction = Transaction(reso.id, reso.endDate, reso.email)
            
            #create reservation in database
            command = "INSERT INTO Reservation VALUES(%s,%s,%s,%s,%s)"
            creationDate = reso.startDate - timedelta(days=random.randint(0,70))
            occupants = number * random.randint(1,3)
    
            cur.execute(command, (reso.id, creationDate, occupants, reso.email, reso.id))
            #for each room we are booking
            for room in to_book:
            
                #book each of the dates
                for i in range(duration):
                    room.book(r_id, startDate + timedelta(days=i))
                room_numbers.append(room.room_number)    
                
            return to_book
    return []
    

#each room keeps track of all booked dates
# if a date isn't listed it is available
# need to check all dates in the range to see if it is a valid room to book    
class Room:
    def __init__(self, room_number, type, lower_price, upper_price):

        self.room_dates = []
        self.room_number = room_number
        self.type = type
        self.lower_price = lower_price
        self.upper_price = upper_price

    
   
    #book a specific room date
    def book(self,r_id,date):
        global cur
        #rooms get more expensive throughout the year 
        #print("Booking room " + str(self.room_number) + ". For date" + str(date.year) + "-" + str(date.month) + "-" + str(date.day))
        
        self.room_dates.append(RoomDate(date, self.lower_price + date.month/12 * (self.upper_price - self.lower_price),r_id))

        #CREATE ENTRY IN TABLE
        command = "INSERT INTO roomDate VALUES(%s,%s,%s,%s)"
        cur.execute(command, (self.room_number, self.room_dates[-1].date, self.room_dates[-1].cost, r_id))


    #return true if the room isn't booked during any of the requested days
    def isAvailable(self, startDate, endDate):
        for room_date in self.room_dates:
            if room_date.date >= startDate and room_date.date <= endDate:
                return False

        return True

#room dates are only listed if they are booked
class RoomDate:
    def __init__(self, date, price, r_id):
        self.date = date
        self.cost = price
        self.r_id = r_id


#database of first/last names create pairs
def createPeople():

    #read from first names file
    fp = open("firstNames.txt","r")
    firstNames = fp.readlines()


    #shuffle names to randomize
    random.shuffle(firstNames)

    fp.close()
    #do same w/ last names
    fp = open("lastNames.txt","r")
    lastNames = fp.readlines()
    


    guests = []
    #add 400 guests  
    for i in range(400):
        fName = firstNames[i].strip()
        lName = lastNames[i].strip()
        guests.append(Guests(email(fName, lName), phoneNumber(), password(), fName + " " + lName))

    print("CREATED GUESTS...")

    employees = []
    streets = address()
    for i in range(400,500):

        streetNum = ""
        for j in range(4):
            streetNum = streetNum + str(random.randint(0,9))

        fName = firstNames[i].strip()
        lName = lastNames[i].strip()
        name = fName + " " + lName
        
   
        employees.append(Employee(i-399, name, random.choice(positions), 
                         streetNum + " " + random.choice(streets), phoneNumber(), random.randint(30000,80000)))


    print("CREATED EMPLOYEES...")

    return guests, employees

#pick from a couple area codes 
def phoneNumber():
    num = ''
    for i in range(8):
        num = num + str(random.randint(0,9))

    return num

#random password generator
def password():
    temp = ""
    for i in range(8):
        temp = temp + random.choice(string.ascii_letters)
    
    return temp

#use first and last name and some random email server
def email(first,last):
    return first + '.' + last + '@gmail.com'


def tableCreation(cur, conn):   

    commands = (
        """DROP TABLE IF EXISTS Books""",
        """DROP TABLE IF EXISTS OrderElement""",
        """DROP TABLE IF EXISTS Cleaning""",
        """DROP TABLE IF EXISTS FoodOrder""",
        """DROP TABLE IF EXISTS Service""",
        """DROP TABLE IF EXISTS RoomDate""",
        """DROP TABLE IF EXISTS room""",
        """DROP TABLE IF EXISTS Reservation CASCADE""",
        """DROP TABLE IF EXISTS Transaction""",
        """DROP TABLE IF EXISTS Employees""",
        """DROP TABLE IF EXISTS Food""",
        """DROP TABLE IF EXISTS Guests""",
       
        """DROP TYPE room_t CASCADE""",
        """CREATE type room_t as enum('single','double','suite','penthouse')""",
        """CREATE TABLE room (
            room_number INTEGER PRIMARY KEY NOT NULL CHECK (room_number > 0),
            roomtype room_t NOT NULL
            )""", 
        """CREATE TABLE Guests(
            Email VARCHAR(254) PRIMARY KEY NOT NULL,
            Phone_Number varchar(15),                                             
            Password VARCHAR(25),
            Full_Name VARCHAR(25)
            )""",     
        """CREATE TABLE Food(
            ID INTEGER NOT NULL PRIMARY KEY,
            Name VARCHAR(32),
            Cost INTEGER CHECK (Cost > 0)
            )""",
        """CREATE TABLE Employees (
            eID INTEGER PRIMARY KEY UNIQUE NOT NULL, 
            Name varchar(60) NOT NULL, 
            Position varchar(100) NOT NULL, 
            Address varchar(70) NOT NULL, 
            Phone_Number varchar(15), 
            Salary float 
            )""", 
        """CREATE TABLE Transaction(
            Transaction_ID INTEGER PRIMARY KEY NOT NULL,
            Payment_type    VARCHAR(32),
            Email VARCHAR(254) REFERENCES Guests(Email), 
            Date Date)""",
        """CREATE TABLE Reservation (
            id INTEGER PRIMARY KEY NOT NULL,
            date Date,
            occupants int CHECK (occupants > 0),                
            email VARCHAR(254) references guests(email),
            transactionID INTEGER references Transaction(Transaction_ID))""",
        """CREATE TABLE RoomDate(
            Room_Number INTEGER NOT NULL References Room(room_number), 
            Date Date NOT NULL, 
            Cost INTEGER NOT NULL CHECK (Cost > 0),
            r_id INTEGER references Reservation(id),
            PRIMARY KEY(ROOM_Number, Date)
            )""",
        """CREATE TABLE Service(
            Service_Number INTEGER PRIMARY KEY NOT NULL, 
            Supervisor INTEGER REFERENCES employees(eid),
            Date DATE,
            Room_Number INTEGER REFERENCES room(room_number),
            Cost INTEGER,
            Reservation_ID INTEGER REFERENCES reservation(id)
            )""", 
        """CREATE TABLE FoodOrder(
            Service_Number INTEGER PRIMARY KEY REFERENCES service(service_number) NOT NULL
            )""", 
        """CREATE TABLE Cleaning( 
            Service_Number INTEGER PRIMARY KEY REFERENCES service(service_number) NOT NULL 
            )""",
        """CREATE TABLE OrderElement(
            element_id INTEGER PRIMARY KEY NOT NULL CHECK (element_id > 0),
            Service_Number INTEGER REFERENCES FoodOrder(Service_Number),
            food_id INTEGER REFERENCES Food(ID)
        )""",
        """CREATE TABLE Books(
            r_id INTEGER PRIMARY KEY REFERENCES Reservation(id),
            e_id INTEGER REFERENCES Employees(eID)
        )""")

    for command in commands:
        print(command)
        cur.execute(command)
    

    conn.commit()


    #output all tables in the server

def address():

    fp = open("streetNames.txt","r")
    streets = fp.readlines()
    return streets


def dataGeneration():
    global cur

    guests, empl = createPeople()
    print("CREATED PEOPLE...")
    streets = address()

   
    for i in guests:
        command = "INSERT INTO Guests VALUES(%s, %s, %s, %s)"
        cur.execute(command, (i.email, i.phone, i.password, i.full_name))
    

    print("EMPLOYEES")
 
    for i in empl:
        command = "INSERT INTO Employees VALUES(%s, %s, %s, %s, %s, %s)"
        cur.execute(command, (i.eID, i.name, i.position, i.address, i.phone, i.salary))
      
    return guests, empl



def menuCreation():
    global foods, cur

    id = 1
    for item in foods:
        command = "INSERT INTO food VALUES(%s,%s,%s)"
        cur.execute(command, (id, item[0], item[1]))
        id += 1



def roomCreation():
    global rooms, cur

    for i in range(1,3):
        for j in range(0,5):
            type = random.choice(roomTypes)
            rooms.append(Room(i * 100 + j, type[0],type[1],type[2]))
            command = "INSERT INTO room VALUES(%s,%s)"
            cur.execute(command, (i * 100 + j, type[0]))

    rooms.append(Room(300,"penthouse",5000,7000))
    cur.execute("INSERT INTO room VALUES(%s,%s)", (300,"penthouse"))

def foodOrderCreation(r_id, room_number, startDate, duration):
    global kitchenStaff, serviceNumber, conn, cur, orderElementId
 
    staff = random.choice(kitchenStaff)
    date = startDate + timedelta(days=random.randint(0,duration))
    items = random.randint(1,5)
    order = []
    cost = 0

    for i in range(items):
        order.append(random.choice(foods))
        cost += order[i][1]


    #create service
    command = "INSERT INTO service VALUES(%s,%s,%s,%s,%s,%s)"
    cur.execute(command, [serviceNumber, staff.eID, date, room_number, cost, r_id])
              

    #create food order
    command = "INSERT INTO foodOrder VALUES(%s)"
    cur.execute(command, (serviceNumber, ))

    #create order elements
    for item in order:
        command = "INSERT INTO OrderElement VALUES(%s,%s,%s)"
        cur.execute(command, (orderElementId, serviceNumber, item[2]))
        orderElementId += 1
    

    serviceNumber += 1


    pass

#map all services that cleaning employees have to here
def cleaningCreation(r_id, room_number, startDate, duration):
    global cleaningStaff, serviceNumber, conn, cur

    staff = random.choice(cleaningStaff)
    date = startDate + timedelta(days=random.randint(0,duration))
    cost = random.randint(10,500)

    #create service
    command = "INSERT INTO service VALUES(%s,%s,%s,%s,%s,%s)"
    cur.execute(command, [serviceNumber, staff.eID, date, room_number, cost, r_id])
    
    #create cleaning
    command = "INSERT INTO Cleaning VALUES(%s)"
    cur.execute(command, (serviceNumber, ))

    serviceNumber += 1


def orderElements(serviceId, foodId):
    global orderElementId

    command = "INSERT INTO orderElements VALUES(%s,%s)"
    cur.execute(command, (orderElementId, serviceId, foodId))

    orderElementId += 1

#take random sample of reservations and assign to employee with position reception
def bookReservation(r_id):
    global receptionStaff, cur
    staff = random.choice(receptionStaff)

    command = "INSERT INTO books VALUES(%s,%s)"
    cur.execute(command, (r_id, staff.eID))


if __name__ == '__main__':

    #connect to server here with try/except/finally

    try:
        #connect to psql server
        conn = db.connect(host="hostname",database="database_name", user="database_user", password="database_password")
        
        #issue commands
        cur = conn.cursor()

        #create the tables for the database
        tableCreation(cur, conn)

        print("TABLE CREATION DONE...")

        #create the guests and employees
        guests, empl = dataGeneration()

        print("PEOPLE CREATION DONE...")

        #get some of the employee subsets
        kitchenStaff   = list(filter(lambda x: x.position == "kitchen", empl))
        cleaningStaff  = list(filter(lambda x: x.position == "cleaning", empl))
        receptionStaff = list(filter(lambda x: x.position == "reception", empl))
        
        #create the menu
        menuCreation()
        roomCreation()

        print("""DONE MENU CREATION...""")


        print("""STARTING TO MAKE RESERVATIONS...""")

        #create reservations from guests
        for i in range(1,31):
        
            booking = 1
            #make 2 reservations
            if i % 5 == 0:
                booking = 2
            #make 3 reservations
            elif i % 7 == 0: 
                booking = 3
            #make 5 reservations
            elif i % 9 == 0:
                booking = 5
            #make 7 reservations
            elif i % 11 == 0:
                booking = 7
            
            for j in range(booking):
                #create a reservation
                reservations.append(Reservation(guests[i-1], random.choice([2,2,2,3,3,3,4,4,5,6,7]), random.choice([1,1,1,1,2,2,3])))
               

        #tableName = ['reservation','room','roomdate','employees','guests','foodorder','orderelement','service','cleaning','transaction','books']    

        cur.close()

        conn.commit()


    except (Exception, db.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')

  
    

    
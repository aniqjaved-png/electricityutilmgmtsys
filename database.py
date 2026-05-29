import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "electricity.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS Customer (
            Cust_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Cust_Name TEXT NOT NULL,
            CNIC TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Customer_Contact (
            Contact_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Cust_Id INTEGER NOT NULL,
            Phone TEXT NOT NULL,
            Email TEXT NOT NULL UNIQUE,
            FOREIGN KEY (Cust_Id) REFERENCES Customer(Cust_Id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS Address (
            Address_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Street TEXT NOT NULL,
            City TEXT NOT NULL,
            Postal_Code TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Customer_Address (
            Cust_Id INTEGER,
            Address_Id INTEGER,
            PRIMARY KEY (Cust_Id, Address_Id),
            FOREIGN KEY (Cust_Id) REFERENCES Customer(Cust_Id) ON DELETE CASCADE,
            FOREIGN KEY (Address_Id) REFERENCES Address(Address_Id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS Meter (
            Meter_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Serial_No TEXT UNIQUE NOT NULL,
            Installation_Date TEXT NOT NULL,
            Meter_Type TEXT NOT NULL CHECK(Meter_Type IN ('Digital','Analog','Smart')),
            Status TEXT NOT NULL CHECK(Status IN ('Active','Inactive'))
        );

        CREATE TABLE IF NOT EXISTS Connection_Type (
            Connection_Type_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Connection_Type_Name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Connection (
            Connection_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Cust_Id INTEGER NOT NULL,
            Meter_Id INTEGER NOT NULL,
            Connection_Type_Id INTEGER NOT NULL,
            Load INTEGER NOT NULL CHECK(Load > 0),
            Status TEXT NOT NULL CHECK(Status IN ('Active','Inactive')),
            FOREIGN KEY (Cust_Id) REFERENCES Customer(Cust_Id),
            FOREIGN KEY (Meter_Id) REFERENCES Meter(Meter_Id),
            FOREIGN KEY (Connection_Type_Id) REFERENCES Connection_Type(Connection_Type_Id)
        );

        CREATE TABLE IF NOT EXISTS Area (
            Area_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Area_Name TEXT NOT NULL,
            City TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Connection_Area (
            Connection_Id INTEGER,
            Area_Id INTEGER,
            PRIMARY KEY (Connection_Id, Area_Id),
            FOREIGN KEY (Connection_Id) REFERENCES Connection(Connection_Id) ON DELETE CASCADE,
            FOREIGN KEY (Area_Id) REFERENCES Area(Area_Id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS Tariff (
            Tariff_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Connection_Type_Id INTEGER NOT NULL,
            Unit_Rate REAL NOT NULL,
            Fixed_Charges REAL NOT NULL,
            Tax_Percentage REAL NOT NULL,
            FOREIGN KEY (Connection_Type_Id) REFERENCES Connection_Type(Connection_Type_Id)
        );

        CREATE TABLE IF NOT EXISTS Billing (
            Bill_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Connection_Id INTEGER NOT NULL,
            Billing_Month TEXT NOT NULL,
            Issue_Date TEXT NOT NULL,
            Due_Date TEXT NOT NULL,
            Units_Consumed INTEGER NOT NULL CHECK(Units_Consumed >= 0),
            Total_Amount REAL NOT NULL CHECK(Total_Amount >= 0),
            FOREIGN KEY (Connection_Id) REFERENCES Connection(Connection_Id)
        );

        CREATE TABLE IF NOT EXISTS Payment_Method (
            Method_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Method_Name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Payment (
            Payment_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Bill_Id INTEGER NOT NULL,
            Method_Id INTEGER NOT NULL,
            Payment_Date TEXT NOT NULL,
            Payment_Status TEXT DEFAULT 'Unpaid' CHECK(Payment_Status IN ('Paid','Unpaid','Pending')),
            Amount_Paid REAL DEFAULT 0 CHECK(Amount_Paid >= 0),
            FOREIGN KEY (Bill_Id) REFERENCES Billing(Bill_Id) ON DELETE CASCADE,
            FOREIGN KEY (Method_Id) REFERENCES Payment_Method(Method_Id)
        );

        CREATE TABLE IF NOT EXISTS Employee (
            Employee_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Role TEXT NOT NULL,
            Department TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Employee_Contact (
            Emp_Contact_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Employee_Id INTEGER NOT NULL,
            Emp_Phone TEXT NOT NULL,
            FOREIGN KEY (Employee_Id) REFERENCES Employee(Employee_Id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS Meter_Reading (
            Reading_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Meter_Id INTEGER NOT NULL,
            Employee_Id INTEGER NOT NULL,
            Reading_Date TEXT NOT NULL,
            Units INTEGER DEFAULT 0 CHECK(Units >= 0),
            FOREIGN KEY (Meter_Id) REFERENCES Meter(Meter_Id),
            FOREIGN KEY (Employee_Id) REFERENCES Employee(Employee_Id)
        );

        CREATE TABLE IF NOT EXISTS Complaint (
            Complaint_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Cust_Id INTEGER NOT NULL,
            Employee_Id INTEGER,
            Description TEXT NOT NULL,
            Status TEXT DEFAULT 'Pending' CHECK(Status IN ('Pending','Resolved')),
            Date_Logged TEXT NOT NULL,
            FOREIGN KEY (Cust_Id) REFERENCES Customer(Cust_Id) ON DELETE CASCADE,
            FOREIGN KEY (Employee_Id) REFERENCES Employee(Employee_Id)
        );

        CREATE TABLE IF NOT EXISTS Power_Outage (
            Outage_Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Area_Id INTEGER NOT NULL,
            Start_Time TEXT NOT NULL,
            End_Time TEXT,
            Reason TEXT NOT NULL,
            Status TEXT NOT NULL CHECK(Status IN ('Active','Resolved')),
            FOREIGN KEY (Area_Id) REFERENCES Area(Area_Id)
        );
    """)

    # Seed only if empty
    count = cur.execute("SELECT COUNT(*) FROM Customer").fetchone()[0]
    if count == 0:
        _seed(cur)

    conn.commit()
    conn.close()


def _seed(cur):
    cur.executemany("INSERT INTO Customer VALUES (?,?,?)", [
        (1,'Ali Raza','35201-1111111-1'),(2,'Ahmed Khan','35201-2222222-2'),
        (3,'Sara Malik','35201-3333333-3'),(4,'Usman Tariq','35201-4444444-4'),
        (5,'Ayesha Noor','35201-5555555-5'),(6,'Bilal Ahmed','35201-6666666-6'),
        (7,'Hina Shah','35201-7777777-7'),(8,'Zain Ali','35201-8888888-8'),
        (9,'Fatima Zahra','35201-9999999-9'),(10,'Hamza Saeed','35201-1010101-0'),
        (11,'Imran Khalid','35201-1111222-1'),(12,'Nida Aslam','35201-1212121-2'),
        (13,'Tariq Mehmood','35201-1313131-3'),(14,'Sana Iqbal','35201-1414141-4'),
        (15,'Rizwan Akram','35201-1515151-5'),(16,'Farhan Javed','35201-1616161-6'),
        (17,'Mariam Khan','35201-1717171-7'),(18,'Adnan Sheikh','35201-1818181-8'),
        (19,'Kiran Ali','35201-1919191-9'),(20,'Asad Rauf','35201-2020202-0'),
        (21,'Waqas Ahmad','35201-2121212-1'),(22,'Saad Hassan','35201-2222333-2'),
        (23,'Mehwish Fatima','35201-2323232-3'),(24,'Yasir Ali','35201-2424242-4'),
        (25,'Iqra Khan','35201-2525252-5'),
    ])

    cur.executemany("INSERT INTO Meter VALUES (?,?,?,?,?)", [
        (1,'MTR1001','2023-01-01','Digital','Active'),(2,'MTR1002','2023-01-02','Analog','Active'),
        (3,'MTR1003','2023-01-03','Smart','Active'),(4,'MTR1004','2023-01-04','Digital','Active'),
        (5,'MTR1005','2023-01-05','Analog','Inactive'),(6,'MTR1006','2023-01-06','Smart','Active'),
        (7,'MTR1007','2023-01-07','Digital','Active'),(8,'MTR1008','2023-01-08','Analog','Active'),
        (9,'MTR1009','2023-01-09','Smart','Active'),(10,'MTR1010','2023-01-10','Digital','Active'),
        (11,'MTR1011','2023-01-11','Smart','Active'),(12,'MTR1012','2023-01-12','Digital','Active'),
        (13,'MTR1013','2023-01-13','Analog','Active'),(14,'MTR1014','2023-01-14','Smart','Active'),
        (15,'MTR1015','2023-01-15','Digital','Active'),(16,'MTR1016','2023-01-16','Analog','Active'),
        (17,'MTR1017','2023-01-17','Smart','Active'),(18,'MTR1018','2023-01-18','Digital','Active'),
        (19,'MTR1019','2023-01-19','Analog','Active'),(20,'MTR1020','2023-01-20','Smart','Active'),
    ])

    cur.executemany("INSERT INTO Connection_Type VALUES (?,?)", [
        (1,'Residential'),(2,'Commercial'),(3,'Industrial'),(4,'Agricultural'),
    ])

    cur.executemany("INSERT INTO Area VALUES (?,?,?)", [
        (1,'Model Town','Lahore'),(2,'Gulberg','Lahore'),(3,'Johar Town','Lahore'),
        (4,'DHA','Lahore'),(5,'Bahria Town','Lahore'),(6,'F-10','Islamabad'),
        (7,'G-11','Islamabad'),(8,'Satellite Town','Rawalpindi'),
        (9,'North Nazimabad','Karachi'),(10,'Clifton','Karachi'),
    ])

    cur.executemany("INSERT INTO Payment_Method VALUES (?,?)", [
        (1,'Cash'),(2,'Credit Card'),(3,'Bank Transfer'),(4,'JazzCash'),(5,'EasyPaisa'),
    ])

    cur.executemany("INSERT INTO Employee VALUES (?,?,?,?)", [
        (1,'Ali Hassan','Technician','Operations'),(2,'Usman Ali','Manager','Billing'),
        (3,'Zara Khan','Clerk','Customer Service'),(4,'Imran Shah','Technician','Maintenance'),
        (5,'Hassan Raza','Supervisor','Operations'),
    ])

    cur.executemany("INSERT INTO Customer_Contact VALUES (?,?,?,?)", [
        (i, i, f'0300000000{i}', f'c{i}@gmail.com') for i in range(1, 26)
    ])

    cur.executemany("INSERT INTO Address VALUES (?,?,?,?)", [
        (1,'Street 1','Lahore','54000'),(2,'Street 2','Lahore','54001'),
        (3,'Street 3','Lahore','54002'),(4,'Street 4','Islamabad','44000'),
        (5,'Street 5','Karachi','75000'),(6,'Street 6','Lahore','54003'),
        (7,'Street 7','Islamabad','44001'),(8,'Street 8','Karachi','75001'),
        (9,'Street 9','Lahore','54004'),(10,'Street 10','Karachi','75002'),
    ])

    cur.executemany("INSERT INTO Customer_Address VALUES (?,?)", [
        (1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8),(9,9),(10,10),
        (11,1),(12,2),(13,3),(14,4),(15,5),(16,6),(17,7),(18,8),(19,9),(20,10),
        (21,1),(22,2),(23,3),(24,4),(25,5),
    ])

    cur.executemany("INSERT INTO Connection VALUES (?,?,?,?,?,?)", [
        (1,1,1,1,5,'Active'),(2,2,2,2,8,'Active'),(3,3,3,1,6,'Active'),
        (4,4,4,3,12,'Active'),(5,5,5,1,7,'Inactive'),(6,6,6,2,9,'Active'),
        (7,7,7,1,5,'Active'),(8,8,8,4,11,'Active'),(9,9,9,1,6,'Active'),
        (10,10,10,2,10,'Active'),(11,11,11,1,5,'Active'),(12,12,12,2,8,'Active'),
        (13,13,13,1,6,'Active'),(14,14,14,3,12,'Active'),(15,15,15,1,7,'Active'),
        (16,16,16,2,9,'Active'),(17,17,17,1,5,'Active'),(18,18,18,4,11,'Active'),
        (19,19,19,1,6,'Active'),(20,20,20,2,10,'Active'),
    ])

    cur.executemany("INSERT INTO Connection_Area VALUES (?,?)", [
        (1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8),(9,9),(10,10),
        (11,1),(12,2),(13,3),(14,4),(15,5),(16,6),(17,7),(18,8),(19,9),(20,10),
    ])

    cur.executemany("INSERT INTO Tariff VALUES (?,?,?,?,?)", [
        (1,1,20.5,150,5),(2,2,25.0,200,10),(3,3,30.0,500,15),(4,4,15.0,100,2),
    ])

    cur.executemany("INSERT INTO Billing VALUES (?,?,?,?,?,?,?)", [
        (1,1,'2025-01-01','2025-01-05','2025-01-20',200,5000),
        (2,2,'2025-01-01','2025-01-05','2025-01-20',300,7500),
        (3,3,'2025-01-01','2025-01-05','2025-01-20',150,3200),
        (4,4,'2025-01-01','2025-01-05','2025-01-20',400,12000),
        (5,5,'2025-01-01','2025-01-05','2025-01-20',180,4000),
        (6,6,'2025-02-01','2025-02-05','2025-02-20',250,6000),
        (7,7,'2025-02-01','2025-02-05','2025-02-20',180,4200),
        (8,8,'2025-02-01','2025-02-05','2025-02-20',320,9000),
        (9,9,'2025-02-01','2025-02-05','2025-02-20',210,5500),
        (10,10,'2025-02-01','2025-02-05','2025-02-20',275,7000),
        (11,11,'2025-03-01','2025-03-05','2025-03-20',190,4800),
        (12,12,'2025-03-01','2025-03-05','2025-03-20',310,8000),
        (13,13,'2025-03-01','2025-03-05','2025-03-20',160,3500),
        (14,14,'2025-03-01','2025-03-05','2025-03-20',420,12500),
        (15,15,'2025-03-01','2025-03-05','2025-03-20',200,5000),
        (16,16,'2025-03-01','2025-03-05','2025-03-20',260,6500),
        (17,17,'2025-03-01','2025-03-05','2025-03-20',175,4100),
        (18,18,'2025-03-01','2025-03-05','2025-03-20',330,9200),
        (19,19,'2025-03-01','2025-03-05','2025-03-20',220,5600),
        (20,20,'2025-03-01','2025-03-05','2025-03-20',290,7200),
    ])

    cur.executemany("INSERT INTO Payment VALUES (?,?,?,?,?,?)", [
        (1,1,1,'2025-01-10','Paid',5000),(2,2,2,'2025-01-12','Paid',7500),
        (3,3,3,'2025-01-15','Pending',0),(4,4,4,'2025-01-18','Paid',12000),
        (5,5,5,'2025-01-19','Unpaid',0),(6,6,1,'2025-02-10','Paid',6000),
        (7,7,2,'2025-02-11','Paid',4200),(8,8,3,'2025-02-12','Pending',0),
        (9,9,4,'2025-02-13','Paid',5500),(10,10,5,'2025-02-14','Unpaid',0),
        (11,11,1,'2025-03-10','Paid',4800),(12,12,2,'2025-03-11','Paid',8000),
        (13,13,3,'2025-03-12','Pending',0),(14,14,4,'2025-03-13','Paid',12500),
        (15,15,5,'2025-03-14','Unpaid',0),(16,16,1,'2025-03-15','Paid',6500),
        (17,17,2,'2025-03-16','Paid',4100),(18,18,3,'2025-03-17','Pending',0),
        (19,19,4,'2025-03-18','Paid',5600),(20,20,5,'2025-03-19','Unpaid',0),
    ])

    cur.executemany("INSERT INTO Meter_Reading VALUES (?,?,?,?,?)", [
        (1,1,1,'2025-01-01',200),(2,2,1,'2025-01-01',300),(3,3,2,'2025-01-01',150),
        (4,4,3,'2025-01-01',400),(5,5,4,'2025-01-01',180),(6,6,1,'2025-02-01',250),
        (7,7,2,'2025-02-01',180),(8,8,3,'2025-02-01',320),(9,9,4,'2025-02-01',210),
        (10,10,5,'2025-02-01',275),(11,11,1,'2025-03-01',190),(12,12,2,'2025-03-01',310),
        (13,13,3,'2025-03-01',160),(14,14,4,'2025-03-01',420),(15,15,5,'2025-03-01',200),
        (16,16,1,'2025-03-01',260),(17,17,2,'2025-03-01',175),(18,18,3,'2025-03-01',330),
        (19,19,4,'2025-03-01',220),(20,20,5,'2025-03-01',290),
    ])

    cur.executemany("INSERT INTO Complaint VALUES (?,?,?,?,?,?)", [
        (1,1,3,'No electricity','Pending','2025-01-02'),
        (2,2,2,'High bill issue','Resolved','2025-01-03'),
        (3,3,1,'Meter fault','Pending','2025-01-04'),
        (4,4,2,'Voltage fluctuation','Pending','2025-02-02'),
        (5,5,3,'Billing error','Resolved','2025-02-03'),
        (6,6,1,'Frequent outage','Pending','2025-02-04'),
        (7,7,2,'Meter issue','Resolved','2025-02-05'),
        (8,8,3,'Low voltage','Pending','2025-02-06'),
        (9,9,1,'Overbilling','Resolved','2025-02-07'),
        (10,10,2,'Connection fault','Pending','2025-02-08'),
    ])

    cur.executemany("INSERT INTO Power_Outage VALUES (?,?,?,?,?,?)", [
        (1,1,'2025-01-01 08:00','2025-01-01 10:00','Maintenance','Resolved'),
        (2,2,'2025-01-02 09:00','2025-01-02 11:30','Fault','Resolved'),
        (3,3,'2025-02-01 07:00','2025-02-01 09:00','Load shedding','Resolved'),
        (4,4,'2025-02-05 06:00','2025-02-05 08:00','Transformer issue','Resolved'),
        (5,5,'2025-02-10 05:00','2025-02-10 07:00','Emergency repair','Resolved'),
    ])

    cur.executemany("INSERT INTO Employee_Contact VALUES (?,?,?)", [
        (1,1,'03100000001'),(2,2,'03100000002'),(3,3,'03100000003'),
        (4,4,'03100000004'),(5,5,'03100000005'),
    ])

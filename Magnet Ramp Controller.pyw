import os
from tkinter import *
from tkinter import filedialog
import mysql.connector
from mysql.connector import Error
from mysql.connector import connection
import pandas as pd
import platform
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import time
import webbrowser
import serial
import re


global port
global stage1Temp
global stage2Temp
global magnetATemp
global magnetBTemp
global switchTemp
global sql
global state
global interlock
global status
global ser
global process
global switch

global initialTime
global time_array
global current_array

global rate1
global rate2
global rate3
global rate4
global set1
global set2
global set3

global t1
t1 = None

status = None
process = None
time_array = []
current_array = []
interlock = False
switch = False
ser = None


#Defines location of the Desktop as well as font and text size for use in the software
desktop = os.path.expanduser("~\Desktop")
font1 = ('Helvetica', 18)
font2 = ('Helvetica', 16)
font3 = ('Helvetica', 14)
font4 = ('Helvetica', 12)
textSize = 20




#Loads the variables com and R from the variables file, and creates the file if none exists
try:
    f = open('variables', 'r')
    variables = f.readlines()
    port = str(variables[0].split('=')[1]).strip()
    sql = str(variables[1].split('=')[1]).strip()
    rate1 = float(variables[2].split(',')[0].split('=')[1])
    set1 = float(variables[2].split(',')[1].split('=')[1])
    rate2 = float(variables[3].split(',')[0].split('=')[1])
    set2 = float(variables[3].split(',')[1].split('=')[1])
    rate3 = float(variables[4].split(',')[0].split('=')[1])
    set3 = float(variables[4].split(',')[1].split('=')[1])
    rate4 = float(variables[5].split('=')[1])

except:
    port = 'COM6'
    sql = 'data'
    rate1 = 0.292
    set1 = 36
    rate2 = 0.219
    set2 = 72
    rate3 = 0.123
    set3 = 90
    rate4 = 0.052
    f = open("variables",'w')
    f.write(f'port={port}\nsql={sql}\nrate1={rate1},set1={set1}\nrate2={rate2},set2={set2}\
        \nrate3={rate3},set3={set3}\nrate4={rate4}')
    f.close()

#Establishes a connection to the SQL database file
def create_db_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection

#Executes commands on the SQL database file
def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query successful")
    except Error as err:
        print(f"Error: '{err}'")

#Reads data from the SQL database file
def read_query(connection, query):
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        connection.commit()
        return result
    except Error as err:
        print(f"Error: '{err}'")

def start_ramp(dir):
    global state
    global initialTime
    global time_array
    global current_array
    global interlock
    global status
    global ser
    global process
    
    if not interlock:
        interlock = True
        time_array = []
        current_array = []
        state = 'start'
        if ser is None:
            try:
                ser = serial.Serial(port, 9600, timeout=3)
            except:
                interlock = False
                helpMessage ='Could not connect to magnet controller. Check connection and try again' 
                messageVar = Message(root, text = helpMessage, font = font2, width = 600) 
                messageVar.config(bg='firebrick1')
                messageVar.place(relx = 0, rely = 1, anchor = SW)
                root.after(5000, messageVar.destroy)
                return
        initialTime = time.time()

        if dir == 'up':
            process = 'energize'
            status.destroy()
            #Creates Status Box
            status = Frame(root, width = 275, height = 300,background = 'white', highlightbackground = 'black', highlightthickness = 1)
            status.place(relx = 0.87, rely = 0.4, anchor = CENTER)
            #Changes Status Label
            statusLabel = Label(status, text = 'Status: Energizing B', font = font1, bg = 'white', fg = 'blue')
            statusLabel.place(relx=0.5, rely=0.15, anchor = CENTER)


            #Stage 1 Process
            stage1 = Label(status, text = 'Stage 1: ', font = font3, bg = 'yellow')
            process1= Label(status, text = 'Heating Switch', font = font3, bg = 'yellow')
            stage1.place(relx=0.35, rely=0.3, anchor = E)
            process1.place(relx=0.35, rely=0.3, anchor = W)

            #Stage 2 Process
            stage2 = Label(status, text = 'Stage 2: ', font = font3, bg = 'white')
            process2 = Label(status, text = 'Ramping Up', font = font3, bg = 'white')
            process2b = Label(status, text = 'R = 0.000 A/s', font = font4, bg = 'white')
            stage2.place(relx=0.35, rely=0.45, anchor = E)
            process2.place(relx=0.35, rely=0.45, anchor = W)
            process2b.place(relx=0.35, rely=0.55, anchor=W)

            #Stage 3 Process
            stage3 = Label(status, text = 'Stage 3: ', font = font3, bg = 'white')
            process3 = Label(status, text = 'Cooling Switch', font = font3, bg = 'white')
            stage3.place(relx=0.35, rely=0.65, anchor = E)
            process3.place(relx=0.35, rely=0.65, anchor = W)

            #Stage 4 Process
            stage4 = Label(status, text = 'Stage 4: ', font = font3, bg = 'white')
            process4 = Label(status, text = 'Ramping Down', font = font3, bg = 'white')
            process4b = Label(status, text = 'R = 0.5 A/s', font = font4, bg = 'white')
            stage4.place(relx=0.35, rely=0.8, anchor = E)
            process4.place(relx=0.35, rely=0.8, anchor = W)
            process4b.place(relx=0.35, rely=0.9, anchor=W)

            ramp_up()

        elif dir == 'down':
            process = 'de-energize'
            status.destroy()
            #Creates Status Box
            status = Frame(root, width = 275, height = 300,background = 'white', highlightbackground = 'black', highlightthickness = 1)
            status.place(relx = 0.87, rely = 0.4, anchor = CENTER)
            #Changes Status Label
            statusLabel = Label(status, text = 'Status: De-energizing B', font = font1, bg = 'white', fg = 'blue')
            statusLabel.place(relx=0.5, rely=0.15, anchor = CENTER)


            #Stage 1 Process
            stage1 = Label(status, text = 'Stage 1: ', font = font3, bg = 'yellow')
            process1 = Label(status, text = 'Ramping Up', font = font3, bg = 'yellow')
            process1b = Label(status, text = 'R = 0.5 A/s', font = font4, bg = 'yellow')
            stage1.place(relx=0.35, rely=0.3, anchor = E)
            process1.place(relx=0.35, rely=0.3, anchor = W)
            process1b.place(relx=0.35, rely=0.4, anchor = W)

            #Stage 2 Process
            stage2 = Label(status, text = 'Stage 2: ', font = font3, bg = 'white')
            process2 = Label(status, text = 'Heating Switch', font = font3, bg = 'white')
            stage2.place(relx=0.35, rely=0.5, anchor = E)
            process2.place(relx=0.35, rely=0.5, anchor = W)

            #Stage 3 Process
            stage3 = Label(status, text = 'Stage 3: ', font = font3, bg = 'white')
            process3 = Label(status, text = 'Ramping Down', font = font3, bg = 'white')
            process3b = Label(status, text = 'R = -0.1 A/s', font = font4, bg = 'white')
            stage3.place(relx=0.35, rely=0.65, anchor = E)
            process3.place(relx=0.35, rely=0.65, anchor = W)
            process3b.place(relx=0.35, rely=0.75, anchor=W)

            #Stage 4 Process
            stage4 = Label(status, text = 'Stage 4: ', font = font3, bg = 'white')
            process4 = Label(status, text = 'Cooling Switch', font = font3, bg = 'white')
            stage4.place(relx=0.35, rely=0.85, anchor = E)
            process4.place(relx=0.35, rely=0.85, anchor = W)

            ramp_down()
    else:
        helpMessage ='Cannot start another process while the magnet is being ramped' 
        messageVar = Message(root, text = helpMessage, font = font2, width = 600) 
        messageVar.config(bg='firebrick1')
        messageVar.place(relx = 0, rely = 1, anchor = SW)
        root.after(5000, messageVar.destroy)

def ramp_up():
    global state
    global initialTime
    global interlock
    global status
    global ser
    global rate1
    global set1
    global rate2
    global set2
    global rate3
    global set3
    global rate4
    global switch

    if state == 'abort':
        return
    
    if state == 'start':
        #Turns the heater on to warm up the switch
        ser.write(str.encode('H1?\n'))
        reading = ser.readline().decode()
        if re.search('HEATER STATUS: ON', reading) == None:
            print(reading)
            print('Error: Heater did not turn on')
            return
        state = 'warm_up'
        switch = True
    
    elif state == 'warm_up':
        check_temperature('up')
    
    elif state == 'start_ramp':
        #Starts the current ramping upward
        ser.write(str.encode(f'SR{rate1}?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-rate1) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        ser.write(str.encode('R!\n'))
        state = 'ramp_1'

        #Stage 1 Process
        stage1 = Label(status, text = 'Stage 1: ', font = font3, bg = 'white')
        process1= Label(status, text = 'Heating Switch', font = font3, bg = 'white')
        stage1.place(relx=0.35, rely=0.3, anchor = E)
        process1.place(relx=0.35, rely=0.3, anchor = W)

        #Stage 2 Process
        stage2 = Label(status, text = 'Stage 2: ', font = font3, bg = 'yellow')
        process2 = Label(status, text = 'Ramping Up', font = font3, bg = 'yellow')
        process2b = Label(status, text = f'R = {rate1} A/s', font = font4, bg = 'yellow')
        stage2.place(relx=0.35, rely=0.45, anchor = E)
        process2.place(relx=0.35, rely=0.45, anchor = W)
        process2b.place(relx=0.35, rely=0.55, anchor=W)
    
    elif state == 'ramp_1':
        check_current(set1, 'up')

    elif state == 'set_rate_2':
        #Lowers the ramp rate to 0.219 A/sec when I=36 A
        ser.write(str.encode(f'SR{rate2}?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-rate2) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        state = 'ramp_2'

        process2b = Label(status, text = f'R = {rate2} A/s', font = font4, bg = 'yellow')
        process2b.place(relx=0.35, rely=0.55, anchor=W)
    
    elif state == 'ramp_2':
        check_current(set2, 'up')

    elif state == 'set_rate_3':
        #Lowers the ramp rate to 0.123 A/sec when I=72 A
        ser.write(str.encode(f'SR{rate3}?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-rate3) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        state = 'ramp_3'

        process2b = Label(status, text = f'R = {rate3} A/s', font = font4, bg = 'yellow')
        process2b.place(relx=0.35, rely=0.55, anchor=W)

    elif state == 'ramp_3':
        check_current(set3, 'up')

    elif state == 'set_rate_4':
        #Lowers the ramp rate to 0.052 A/sec when I=90 A
        ser.write(str.encode(f'SR{rate4}?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-rate4) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        state = 'ramp_4'

        process2b = Label(status, text = f'R = {rate4} A/s', font = font4, bg = 'yellow')
        process2b.place(relx=0.35, rely=0.55, anchor=W)

    elif state == 'ramp_4':
        check_current(108.1, 'up', sleeps=True)

    elif state == 'heat_off':
        #Turns the Heater off
        ser.write(str.encode('H0?\n'))
        reading = ser.readline().decode()
        if re.search('HEATER STATUS: SWITCHED OFF', reading) == None:
            print(reading)
            print('Error: Heater did not turn off')
            ser.write(str.encode('H1?\n'))
        state = 'cool_down'

        #Stage 2 Process
        stage2 = Label(status, text = 'Stage 2: ', font = font3, bg = 'white')
        process2 = Label(status, text = 'Ramping Up', font = font3, bg = 'white')
        process2b = Label(status, text = 'R = 0.000 A/s', font = font4, bg = 'white')
        stage2.place(relx=0.35, rely=0.45, anchor = E)
        process2.place(relx=0.35, rely=0.45, anchor = W)
        process2b.place(relx=0.35, rely=0.55, anchor=W)

        #Stage 3 Process
        stage3 = Label(status, text = 'Stage 3: ', font = font3, bg = 'yellow')
        process3 = Label(status, text = 'Cooling Switch', font = font3, bg = 'yellow')
        stage3.place(relx=0.35, rely=0.65, anchor = E)
        process3.place(relx=0.35, rely=0.65, anchor = W)
    
    elif state == 'cool_down':
        check_temperature('down')
    
    elif state == 'finished':
        switch = False
        #Sets the ramp rate
        ser.write(str.encode('SR0.5\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-0.5) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
        ser.write(str.encode('R0\n'))
        state = 'supply_down'

        #Stage 3 Process
        stage3 = Label(status, text = 'Stage 3: ', font = font3, bg = 'white')
        process3 = Label(status, text = 'Cooling Switch', font = font3, bg = 'white')
        stage3.place(relx=0.35, rely=0.65, anchor = E)
        process3.place(relx=0.35, rely=0.65, anchor = W)


        #Stage 4 Process
        stage4 = Label(status, text = 'Stage 4: ', font = font3, bg = 'yellow')
        process4 = Label(status, text = 'Ramping Down', font = font3, bg = 'yellow')
        process4b = Label(status, text = 'R = -0.5 A/s', font = font4, bg = 'yellow')
        stage4.place(relx=0.35, rely=0.8, anchor = E)
        process4.place(relx=0.35, rely=0.8, anchor = W)
        process4b.place(relx=0.35, rely=0.9, anchor=W)
    
    elif state == 'supply_down':
        check_current(0, 'down')

    elif state == 'done':
        create_blank_status()

        interlock = False
        return
    
    root.after(500, lambda: ramp_up())


def ramp_down():
    global initialTime
    global state
    global interlock
    global status
    global ser
    global switch
    global rate1
    global set1
    global rate2
    global set2
    global rate3
    global set3
    global rate4

    if state == 'abort':
        return

    if state == 'start':
        #Starts the current ramping upward
        ser.write(str.encode('SR0.5?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-0.5) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        ser.write(str.encode('R!\n'))
        state = 'ramp_up'

    elif state == 'ramp_up':
        check_current(108.1, 'up', sleeps=True)
    
    elif state == 'heat_on':
        #Turns the heater on to warm up the switch
        ser.write(str.encode('H1?\n'))
        reading = ser.readline().decode()
        print(reading)
        if re.search('HEATER STATUS: ON', reading) == None:
            print(reading)
            print('Error: Heater did not turn on')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        state = 'warm_up'
        switch = True

        #Stage 1 Process
        stage1 = Label(status, text = 'Stage 1: ', font = font3, bg = 'white')
        process1 = Label(status, text = 'Ramping Up', font = font3, bg = 'white')
        process1b = Label(status, text = 'R = 0.0 A/s', font = font4, bg = 'white')
        stage1.place(relx=0.35, rely=0.3, anchor = E)
        process1.place(relx=0.35, rely=0.3, anchor = W)
        process1b.place(relx=0.35, rely=0.4, anchor = W)

        #Stage 2 Process
        stage2 = Label(status, text = 'Stage 2: ', font = font3, bg = 'yellow')
        process2 = Label(status, text = 'Heating Switch', font = font3, bg = 'yellow')
        stage2.place(relx=0.35, rely=0.5, anchor = E)
        process2.place(relx=0.35, rely=0.5, anchor = W)

    elif state == 'warm_up':
        check_temperature('up')

    elif state == 'start_ramp':
        #Sets the ramp rate for the downward ramp cycle to rate4
        ser.write(str.encode(f'SR{rate4}?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-rate4) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
        state = 'ramp_1'
        #Ramps the magnet current down
        ser.write(str.encode('R0\n'))

        #Stage 2 Process
        stage2 = Label(status, text = 'Stage 2: ', font = font3, bg = 'white')
        process2 = Label(status, text = 'Heating Switch', font = font3, bg = 'white')
        stage2.place(relx=0.35, rely=0.5, anchor = E)
        process2.place(relx=0.35, rely=0.5, anchor = W)

        #Stage 3 Process
        stage3 = Label(status, text = 'Stage 3: ', font = font3, bg = 'yellow')
        process3 = Label(status, text = 'Ramping Down', font = font3, bg = 'yellow')
        process3b = Label(status, text = f'R = -{rate4} A/s', font = font4, bg = 'yellow')
        stage3.place(relx=0.35, rely=0.65, anchor = E)
        process3.place(relx=0.35, rely=0.65, anchor = W)
        process3b.place(relx=0.35, rely=0.75, anchor=W)
    
    elif state == 'ramp_1':
        check_current(set3, 'down')

    elif state == 'set_rate_2':
        #Raises the ramp rate to rate3 when I=set3
        ser.write(str.encode(f'SR{rate3}?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-rate3) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        state = 'ramp_2'

        process3b = Label(status, text = f'R = -{rate3} A/s', font = font4, bg = 'yellow')
        process3b.place(relx=0.35, rely=0.75, anchor=W)

    elif state == 'ramp_2':
        check_current(set2, 'down')

    elif state == 'set_rate_3':
        #Raises the ramp rate to rate2 when I=set2
        ser.write(str.encode(f'SR{rate2}?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-rate2) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        state = 'ramp_3'

        process3b = Label(status, text = f'R = -{rate2} A/s', font = font4, bg = 'yellow')
        process3b.place(relx=0.35, rely=0.75, anchor=W)

    elif state == 'ramp_3':
        check_current(set1, 'down')

    elif state == 'set_rate_4':
        #Raises the ramp rate to rate1 when I=set1
        ser.write(str.encode(f'SR{rate1}?\n'))
        reading = ser.readline().decode()
        start = re.search('RAMP RATE: ', reading).span()[1] + 1
        end = re.search(' A/SEC', reading).span()[0] - 1
        rate = float(reading[start:end])
        if abs(rate-rate1) >= 0.05:
            print(reading)
            print('Error: Rate not set correctly')
            ser.write(str.encode('R0?\n'))
            check_current(0, 'down')
            return
        state = 'ramp_down'

        process3b = Label(status, text = f'R = -{rate1} A/s', font = font4, bg = 'yellow')
        process3b.place(relx=0.35, rely=0.75, anchor=W)
    
    elif state == 'ramp_down':
        check_current(0, 'down', sleeps=True)

    elif state == 'heat_off':
        #Turns the Heater off
        ser.write(str.encode('H0?\n'))
        reading = ser.readline().decode()
        if re.search('HEATER STATUS: OFF', reading) == None:
            print(reading)
            print('Error: Heater did not turn off')
        state = 'cool_down'
        switch = False

        #Stage 3 Process
        stage3 = Label(status, text = 'Stage 3: ', font = font3, bg = 'white')
        process3 = Label(status, text = 'Ramping Down', font = font3, bg = 'white')
        process3b = Label(status, text = 'R = -0.0 A/s', font = font4, bg = 'white')
        stage3.place(relx=0.35, rely=0.65, anchor = E)
        process3.place(relx=0.35, rely=0.65, anchor = W)
        process3b.place(relx=0.35, rely=0.75, anchor=W)

        #Stage 4 Process
        stage4 = Label(status, text = 'Stage 4: ', font = font3, bg = 'yellow')
        process4 = Label(status, text = 'Cooling Switch', font = font3, bg = 'yellow')
        stage4.place(relx=0.35, rely=0.85, anchor = E)
        process4.place(relx=0.35, rely=0.85, anchor = W)

    elif state == 'cool_down':
        check_temperature('down')

    elif state == 'finished':
        create_blank_status()

        interlock = False
        return

    root.after(500, lambda: ramp_down())


#Checks the current to see if it has reached the setpoint yet
def check_current(setpoint, dir):
    global time_array
    global current_array
    global state
    global ser

    if setpoint == 108.1 or setpoint == 0:
        set.write(str.encode('RS?\n'))
        reading = ser.readline().decode()
        start = re.search('OUTPUT:', reading).span()[1] + 1
        end = re.search('AMPS', reading).span()[0] - 1
        current = float(reading[start:end].strip())

        if re.search('RAMP STATUS: HOLDING ON', reading) != None:
            if dir == 'up':
                if state == 'ramp_up':
                    state = 'heat_on'
                elif state == 'ramp_4':
                    state = 'heat_off'
            elif dir == 'down':
                if state == 'ramp_down':
                    state = 'heat_off'
        else:
            return
            

    else:
        ser.write(str.encode('GO?\n'))
        reading = ser.readline().decode()
        start = re.search('OUTPUT:', reading).span()[1] + 1
        end = re.search('AMPS', reading).span()[0] - 1
        current = float(reading[start:end].strip())
        # print(reading)
        # print(current)

        time_array.append(time.time()-initialTime)
        current_array.append(current)

        if dir == 'up':
            if current <= setpoint:
                return
            elif state == 'ramp_1':
                state = 'set_rate_2'
            elif state == 'ramp_2':
                state = 'set_rate_3'
            elif state == 'ramp_3':
                state = 'set_rate_4'

        if dir == 'down':
            if current > setpoint:
                return

            elif state == 'ramp_1':
                state = 'set_rate_2'
            elif state == 'ramp_2':
                state = 'set_rate_3'
            elif state == 'ramp_3':
                state = 'set_rate_4'
            elif state == 'supply_down':
                state = 'done'
            elif state == 'abort':
                state = 'done'


#Checks the switch temperature to ensure it is warmed up
def check_temperature(dir):
    global switchTemp
    global state

    if dir == 'up':
        if switchTemp < 6:
            return
        if state == 'warm_up':
            state = 'start_ramp'
            
    if dir == 'down':
        if switchTemp > 4.5:
            return
        if state == 'heat_switch':
            state = 'set_rate'
        elif state == 'cool_down':
            state = 'finished'
        

def update_data(connection):
    global stage1Temp
    global stage2Temp
    global magnetATemp
    global magnetBTemp
    global switchTemp

    query_format = f'''
    SELECT * FROM kryo_temps;
    '''
    table = read_query(connection, query_format)
    stage1Temp = table[0][4]
    stage2Temp = table[1][4]
    magnetATemp = table[2][4]
    magnetBTemp = table[3][4]
    switchTemp = table[4][4]

    stage1b.config(text = f'{stage1Temp:.2f} K')
    stage2b.config(text = f'{stage2Temp:.2f} K')
    magnetAb.config(text = f'{magnetATemp:.2f} K')
    magnetBb.config(text = f'{magnetBTemp:.2f} K')
    switchb.config(text = f'{switchTemp:.2f} K')

    temps.after(1000, lambda: update_data(connection))


#Opens Settings Window, which allows the user to change the persistent global variables V and R
def Settings():
    global port
    global sql
    global rate1
    global set1
    global rate2
    global set2
    global rate3
    global set3
    global rate4

    settings = Toplevel(root)
    settings.geometry('400x300')
    settings.wm_title("Settings")
    if platform.system() == 'Windows':
        settings.iconbitmap("icons/settings.ico")
    settings.configure(bg='grey95')
    L1 = Label(settings, text = 'COM Port:', font = font2, bg='grey95')
    L1.place(relx=0.3, rely=0.2, anchor = E)
    E1 = Entry(settings, font = font2, width = 6)
    E1.insert(0,str(port))
    E1.place(relx=0.3, rely=0.2, anchor = W)

    L2 = Label(settings, text = 'SQL File:', font = font2, bg='grey95')
    L2.place(relx=0.8, rely=0.2, anchor = E)
    E2 = Entry(settings, font = font2, width = 5)
    E2.insert(0,str(sql))
    E2.place(relx=0.8, rely=0.2, anchor = W)
    
    L3 = Label(settings, text = 'Rate 1:', font = font2, bg='grey95')
    L3.place(relx=0.25, rely=0.4, anchor = E)
    E3 = Entry(settings, font = font2, width = 5)
    E3.insert(0,str(rate1))
    E3.place(relx=0.25, rely=0.4, anchor = W)
    L3units = Label(settings, text = 'A/s', font = font2, bg = 'grey95')
    L3units.place(relx=0.4, rely=0.4, anchor = W)

    L4 = Label(settings, text = 'Set 1:', font = font2, bg='grey95')
    L4.place(relx=0.75, rely=0.4, anchor = E)
    E4 = Entry(settings, font = font2, width = 5)
    E4.insert(0,str(set1))
    E4.place(relx=0.75, rely=0.4, anchor = W)
    L4units = Label(settings, text = 'A', font = font2, bg='grey95')
    L4units.place(relx=0.9, rely=0.4, anchor = W)

    L5 = Label(settings, text = 'Rate 2:', font = font2, bg='grey95')
    L5.place(relx=0.25, rely=0.5, anchor = E)
    E5 = Entry(settings, font = font2, width = 5)
    E5.insert(0,str(rate2))
    E5.place(relx=0.25, rely=0.5, anchor = W)
    L5units = Label(settings, text = 'A/s', font = font2, bg = 'grey95')
    L5units.place(relx=0.4, rely=0.5, anchor = W)

    L6 = Label(settings, text = 'Set 2:', font = font2, bg='grey95')
    L6.place(relx=0.75, rely=0.5, anchor = E)
    E6 = Entry(settings, font = font2, width = 5)
    E6.insert(0,str(set2))
    E6.place(relx=0.75, rely=0.5, anchor = W)
    L6units = Label(settings, text = 'A', font = font2, bg='grey95')
    L6units.place(relx=0.9, rely=0.5, anchor = W)

    L7 = Label(settings, text = 'Rate 3:', font = font2, bg='grey95')
    L7.place(relx=0.25, rely=0.6, anchor = E)
    E7 = Entry(settings, font = font2, width = 5)
    E7.insert(0,str(rate3))
    E7.place(relx=0.25, rely=0.6, anchor = W)
    L7units = Label(settings, text = 'A/s', font = font2, bg = 'grey95')
    L7units.place(relx=0.4, rely=0.6, anchor = W)

    L8 = Label(settings, text = 'Set 3:', font = font2, bg='grey95')
    L8.place(relx=0.75, rely=0.6, anchor = E)
    E8 = Entry(settings, font = font2, width = 5)
    E8.insert(0,str(set3))
    E8.place(relx=0.75, rely=0.6, anchor = W)
    L8units = Label(settings, text = 'A', font = font2, bg='grey95')
    L8units.place(relx=0.9, rely=0.6, anchor = W)

    L9 = Label(settings, text = 'Rate 4:', font = font2, bg='grey95')
    L9.place(relx=0.25, rely=0.7, anchor = E)
    E9 = Entry(settings, font = font2, width = 5)
    E9.insert(0,str(rate4))
    E9.place(relx=0.25, rely=0.7, anchor = W)
    L9units = Label(settings, text = 'A/s', font = font2, bg = 'grey95')
    L9units.place(relx=0.4, rely=0.7, anchor = W)

    L10 = Label(settings, text = 'Set 4:', font = font2, bg='grey95')
    L10.place(relx=0.75, rely=0.7, anchor = E)
    L10 = Label(settings, text = '108.1 A', font = font2, bg='grey95')
    L10.place(relx=0.75, rely=0.7, anchor = W)

    b1 = Button(settings, text = 'Update', relief = 'raised', background='lightblue', activebackground='blue', font = font1, width = 10, height = 1,\
                command = lambda: [updateSettings(str(E1.get()),str(E2.get()),float(E3.get()),float(E4.get()),float(E5.get()),float(E6.get()),float(E7.get()),float(E8.get()),float(E9.get())),settings.destroy()])
    b1.place(relx=0.75, rely=0.9, anchor = CENTER)

    b2 = Button(settings, text = 'Reset', relief = 'raised', background='pink', activebackground='red', font = font1, width = 10, height = 1, command = lambda: [updateSettings('COM6','data',0.292,36,0.219,72,0.123,90,0.052),settings.destroy()])
    b2.place(relx=0.25, rely=0.9, anchor = CENTER)

#Updates the persistent global variables port and sql, as well as store the ramp rates and set points
def updateSettings(E1, E2, E3, E4, E5, E6, E7, E8, E9):
    global interlock
    global port
    global sql
    global rate1
    global set1
    global rate2
    global set2
    global rate3
    global set3
    global rate4

    if not interlock:
        port = E1
        sql = E2
        rate1 = E3
        set1 = E4
        rate2 = E5
        set2 = E6
        rate3 = E7
        set3 = E8
        rate4 = E9
        f = open("variables",'w')
        f.write(f'port={port}\nsql={sql}\nrate1={rate1},set1={set1}\nrate2={rate2},set2={set2}\
            \nrate3={rate3},set3={set3}\nrate4={rate4}')
        f.close()
    else:
        helpMessage ='Cannot change settings while ramping the magnet' 
        messageVar = Message(root, text = helpMessage, font = font2, width = 600) 
        messageVar.config(bg='firebrick1')
        messageVar.place(relx = 0, rely = 1, anchor = SW)
        root.after(5000, messageVar.destroy)


def manualControl():
    manual = Toplevel(root)
    manual.geometry('400x300')
    manual.wm_title("Manual Serial Control")
    if platform.system() == 'Windows':
        manual.iconbitmap("icons/serial.ico")
    manual.configure(bg='white')
    v = Scrollbar(manual, orient = 'vertical')
    t = Text(manual, font = font4, bg='white', width = 20, height = 100, wrap = NONE, yscrollcommand = v.set)
    t.insert(END, "*********************************************************************************************************************\n")
    t.insert(END, "Program: RGA Spectrum Analyzer\n")
    t.insert(END, "Author: Richard Mattish\n")
    t.insert(END, "Last Updated: 10/27/2021\n\n")
    t.insert(END, "Function:  This program provides a graphical user interface for quickly importing\n")
    t.insert(END, "\tRGA binary data files and identifying the presence/partial pressure of several of the most\n")
    t.insert(END, "\tcommon elements and gases.\n")
    t.insert(END, "*********************************************************************************************************************\n\n\n\n")
    t.insert(END, "User Instructions\n-------------------------\n")
    t.pack(side=TOP, fill=X)
    v.config(command=t.yview)


#Opens a url in a new tab in the default webbrowser
def callback(url):
    webbrowser.open_new_tab(url)


#Opens About Window with software information
def About():
    name = "Magnet Ramp Controller"
    version = 'Version: 1.0.0'
    date = 'Date: 11/02/2021'
    support = 'Support: '
    url = 'https://github.com/rhmatti/RGA-Spectrum-Analyzer'
    copyrightMessage ='Copyright © 2021 Richard Mattish All Rights Reserved.'
    t = Toplevel(root)
    t.wm_title("About")
    t.geometry("400x300")
    t.resizable(False, False)
    t.configure(background='white')
    if platform.system() == 'Windows':
        t.iconbitmap("icons/magnet.ico")
    l1 = Label(t, text = name, bg='white', fg='blue', font=font2)
    l1.place(relx = 0.15, rely = 0.14, anchor = W)
    l2 = Label(t, text = version, bg='white', font=font4)
    l2.place(relx = 0.15, rely = 0.25, anchor = W)
    l3 = Label(t, text = date, bg='white', font=font4)
    l3.place(relx = 0.15, rely = 0.35, anchor = W)
    l4 = Label(t, text = support, bg = 'white', font=font4)
    l4.place(relx = 0.15, rely = 0.45, anchor = W)
    l5 = Label(t, text = 'https://github.com/rhmatti/\nRGA-Spectrum-Analyzer', bg = 'white', fg = 'blue', font=font4)
    l5.place(relx = 0.31, rely=0.48, anchor = W)
    l5.bind("<Button-1>", lambda e:
    callback(url))
    messageVar = Message(t, text = copyrightMessage, bg='white', font = font4, width = 600)
    messageVar.place(relx = 0.5, rely = 1, anchor = S)

def Instructions():
    instructions = Toplevel(root)
    instructions.geometry('1280x720')
    instructions.wm_title("User Instructions")
    instructions.configure(bg='white')
    if platform.system() == 'Windows':
        instructions.iconbitmap("icons/magnet.ico")
    v = Scrollbar(instructions, orient = 'vertical')
    t = Text(instructions, font = font4, bg='white', width = 100, height = 100, wrap = NONE, yscrollcommand = v.set)
    t.insert(END, "*********************************************************************************************************************\n")
    t.insert(END, "Program: RGA Spectrum Analyzer\n")
    t.insert(END, "Author: Richard Mattish\n")
    t.insert(END, "Last Updated: 10/27/2021\n\n")
    t.insert(END, "Function:  This program provides a graphical user interface for quickly importing\n")
    t.insert(END, "\tRGA binary data files and identifying the presence/partial pressure of several of the most\n")
    t.insert(END, "\tcommon elements and gases.\n")
    t.insert(END, "*********************************************************************************************************************\n\n\n\n")
    t.insert(END, "User Instructions\n-------------------------\n")
    t.insert(END, "1. Open the file \"RGA Spectrum Analyzer.pyw\"\n\n")
    t.insert(END, "2. Select the \"Import\" option from the File menu (File>Import) or use the shortcut <Ctrl+I>\n\n")
    t.insert(END, "3. Using the navigation window, navigate to an output file generated from the SRS RGA software (ending in .ana) and import it\n\n")
    t.insert(END, "4. Automatic Analysis:\n")
    t.insert(END, "\ta) Select \"Auto-Anayze\" from the Analysis menu (Analysis>Auto-Analylze) or use the shortcut <Ctrl+R>\n")
    t.insert(END, "\tb) A separate window will open with the results of the analysis\n")
    t.insert(END, "\tc) The results will show the name of the gas, along with the partial pressure in Torr and % composition\n")
    t.insert(END, "\td) To save these results, click anywhere within the results window and use the <Ctrl+S> command\n")
    t.insert(END, "\te) The \"Auto-Anayze\" function searches for peak matches within a certain range of the expected mass (Δm)\n")
    t.insert(END, "\tand above a certain pressure threshold (P_min) which can be adjusted in the \"Settings\" (File>Settings)\n\n")
    t.insert(END, "5. Select a desired plot type from the \"Plot\" menu:\n")
    t.insert(END, "\ta) Single RGA Scan:\n")
    t.insert(END, "\t\t-Plots one RGA scan at a single instance in time from the binary data file\n")
    t.insert(END, "\t\t-Use the navigation controls to change which scan is plotted\n")
    t.insert(END, "\tb) All RGA Scans:\n")
    t.insert(END, "\t\t-Plots all of the RGA scans from the binary data file\n")
    t.insert(END, "\tc) Total Pressure Change:\n")
    t.insert(END, "\t\t-Plots the total pressure (sum of all partial pressures) as a function of time\n")
    t.insert(END, "\td) Partial Pressure Change:\n")
    t.insert(END, "\t\t-Plots the partial pressure of a specific gas that the user selects from the submenu\n")
    t.insert(END, "\t\t-The gases available for selection include: Methane, H2O, Ne, N2, NO, O2, Ar, and CO2\n\n")
    t.insert(END, "6. To save the graph on screen, use the save icon in the toolbar at the bottom of the screen,\n")
    t.insert(END, "\tselect \"Save\" from the drop-down File menu (File>Save), or use the shortcut <Ctrl+S>\n\n")


    t.pack(side=TOP, fill=X)
    v.config(command=t.yview)

def save_data():
    fileName = str(filedialog.asksaveasfile(initialdir = desktop,title = "Save",filetypes = (("Text Document","*.txt*"),("Text Document","*.txt*"))))
    fileName = fileName.split("'")
    fileName = fileName[1]
    outputFile = open(fileName + '.txt', "w")
    outputFile.write('Time (s)\tCurrent (°C)\n\n')

    for i in range(0,len(time_array)-1):
        outputFile.write(str(time_array[i]) + '\t' + str(current_array[i]) + '\n')

    outputFile.close()
    webbrowser.open(fileName + '.txt')

def abort():
    global ser
    global interlock
    global state
    global status
    global process
    global switch

    if interlock:
        state = 'abort'

        if not switch:
            #Ramps the magnet current down
            ser.write(str.encode('R0\n'))

            #Sets the ramp speed to 0.5 A/s
            ser.write(str.encode('SR0.5?\n'))
            reading = ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-0.5) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')

        elif switch:
            if process == 'energize':
                #Ramps the magnet current down
                ser.write(str.encode('R0\n'))

                if state == 'start_ramp' or state == 'ramp_1' or state == 'ramp_2' or state == 'set_rate_2':
                    #Sets the ramp speed to 0.2 A/s
                    ser.write(str.encode('SR0.2?\n'))
                    reading = ser.readline().decode()
                    start = re.search('RAMP RATE: ', reading).span()[1] + 1
                    end = re.search(' A/SEC', reading).span()[0] - 1
                    rate = float(reading[start:end])
                    if abs(rate-0.2) >= 0.05:
                        print(reading)
                        print('Error: Rate not set correctly')
                else:
                    #Sets the ramp speed to 0.1 A/s
                    ser.write(str.encode('SR0.1?\n'))
                    reading = ser.readline().decode()
                    start = re.search('RAMP RATE: ', reading).span()[1] + 1
                    end = re.search(' A/SEC', reading).span()[0] - 1
                    rate = float(reading[start:end])
                    if abs(rate-0.1) >= 0.05:
                        print(reading)
                        print('Error: Rate not set correctly')
            elif process == 'de-energize':
                if state == 'warm_up' or state == 'start_ramp' or state == 'ramp_1':
                    #Sets the ramp speed to 0.1 A/s
                    ser.write(str.encode('SR0.1?\n'))
                    reading = ser.readline().decode()
                    start = re.search('RAMP RATE: ', reading).span()[1] + 1
                    end = re.search(' A/SEC', reading).span()[0] - 1
                    rate = float(reading[start:end])
                    if abs(rate-0.1) >= 0.05:
                        print(reading)
                        print('Error: Rate not set correctly')
                else:
                    #Sets the ramp speed to 0.2 A/s
                    ser.write(str.encode('SR0.2?\n'))
                    reading = ser.readline().decode()
                    start = re.search('RAMP RATE: ', reading).span()[1] + 1
                    end = re.search(' A/SEC', reading).span()[0] - 1
                    rate = float(reading[start:end])
                    if abs(rate-0.2) >= 0.05:
                        print(reading)
                        print('Error: Rate not set correctly')



        print('Process Aborted')

        status.destroy()
        #Creates Status Box
        status = Frame(root, width = 275, height = 300,background = 'white', highlightbackground = 'black', highlightthickness = 1)
        status.place(relx = 0.87, rely = 0.4, anchor = CENTER)
        #Changes Status Label
        statusLabel = Label(status, text = 'Status: Aborting', font = font1, bg = 'white', fg = 'red')
        statusLabel.place(relx=0.5, rely=0.15, anchor = CENTER)


        #Abortion Process
        abortionMessage = f'Process has been aborted.\nPower supply is ramping\n down at {rate} A/s'
        abortionLabel = Label(status, text = abortionMessage, font = font3, bg = 'white', fg = 'red')
        abortionLabel.place(relx=0.5, rely=0.5, anchor = CENTER)

        monitor_abortion()



def monitor_abortion():
    global state
    global interlock

    check_current(0, 'down')
    if state == 'done':
        interlock = False
        create_blank_status()
        return
    root.after(500, lambda: monitor_abortion())

def quitProgram():
    print('Quit Program')
    abort()
    root.quit()
    root.destroy()


def animate(i):
    global ax
    global time_array
    global current_array
    ax.clear()
    xdata = time_array
    ydata = current_array
    ax.plot(xdata,ydata)
    ax.set_title('Magnet Current')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Current (A)')

def create_blank_status():
    global status
    global process

    process = None

    if status is not None:
        status.destroy()
    #Creates Status Box
    status = Frame(root, width = 275, height = 300,background = 'grey92', highlightbackground = 'black', highlightthickness = 1)
    status.place(relx = 0.87, rely = 0.4, anchor = CENTER)
    statusLabel = Label(status, text = 'Status: Off', font = font1, bg = 'grey92', fg = 'blue')
    statusLabel.place(relx=0.5, rely=0.15, anchor = CENTER)

    #Stage 1 Process
    stage1 = Label(status, text = 'Stage 1: ', font = font3, bg = 'grey92')
    process1= Label(status, text = 'N/A', font = font3, bg = 'grey92')
    stage1.place(relx=0.35, rely=0.3, anchor = E)
    process1.place(relx=0.35, rely=0.3, anchor = W)


    #Stage 2 Process
    stage2 = Label(status, text = 'Stage 2: ', font = font3, bg = 'grey92')
    process2 = Label(status, text = 'N/A', font = font3, bg = 'grey92')
    stage2.place(relx=0.35, rely=0.45, anchor = E)
    process2.place(relx=0.35, rely=0.45, anchor = W)


    #Stage 3 Process
    stage3 = Label(status, text = 'Stage 3: ', font = font3, bg = 'grey92')
    process3 = Label(status, text = 'N/A', font = font3, bg = 'grey92')
    stage3.place(relx=0.35, rely=0.6, anchor = E)
    process3.place(relx=0.35, rely=0.6, anchor = W)


    #Stage 4 Process
    stage4 = Label(status, text = 'Stage 4: ', font = font3, bg = 'grey92')
    process4 = Label(status, text = 'N/A', font = font3, bg = 'grey92')
    stage4.place(relx=0.35, rely=0.75, anchor = E)
    process4.place(relx=0.35, rely=0.75, anchor = W)

    #Message
    messageLabel = Label(status, text = 'Progress will be shown here\nwhen a process is started', font = font3, bg = 'grey92')
    messageLabel.place(relx=0.5, rely=0.9, anchor = CENTER)

stage1Temp = 40
stage2Temp = 4
magnetATemp = 4
magnetBTemp = 4
switchTemp = 4

#connection = create_db_connection("localhost", "root", "cuebit", sql)

#This is the GUI for the software
root = Tk()
menu = Menu(root)
root.config(menu=menu)

root.title("Magnet Ramp Controller")
root.geometry("1200x768")
root.configure(bg='white')
root.protocol("WM_DELETE_WINDOW", quitProgram)
if platform.system() == 'Windows':
    root.iconbitmap("icons/magnet.ico")


#Creates File menu
filemenu = Menu(menu, tearoff=0)
menu.add_cascade(label="File", menu=filemenu)
filemenu.add_command(label="Save", command=lambda: save_data(), accelerator="Ctrl+S")
filemenu.add_command(label='Settings', command=lambda: Settings())
filemenu.add_command(label='Manual Control', command=lambda: manualControl())
filemenu.add_separator()
filemenu.add_command(label='Exit', command=lambda: quitProgram())


#Creates Help menu
helpmenu = Menu(menu, tearoff=0)
menu.add_cascade(label='Help', menu=helpmenu)
helpmenu.add_command(label='Instructions', command= lambda: Instructions())
helpmenu.add_command(label='About', command= lambda: About())

#Creates Temperature Readouts
temps = Frame(root, width = 225, height = 300,background = 'white', highlightbackground = 'black', highlightthickness = 1)
temps.place(relx = 0.12, rely = 0.4, anchor = CENTER)
tempLabel = Label(temps, text = 'Temperatures', font = font1, bg = 'white', fg = 'blue')
tempLabel.place(relx=0.5, rely=0.15, anchor = CENTER)

#Stage 1 Temperature
stage1a = Label(temps, text = 'Stage 1: ', font = font3, bg = 'white')
stage1b= Label(temps, text = str(stage1Temp) + ' K', font = font3, bg = 'white')
stage1a.place(relx=0.5, rely=0.3, anchor = E)
stage1b.place(relx=0.5, rely=0.3, anchor = W)

#Stage 2 Temperature
stage2a = Label(temps, text = 'Stage 2: ', font = font3, bg = 'white')
stage2b = Label(temps, text = str(stage2Temp) + ' K', font = font3, bg = 'white')
stage2a.place(relx=0.5, rely=0.45, anchor = E)
stage2b.place(relx=0.5, rely=0.45, anchor = W)

#Magnet A Temperature
magnetAa = Label(temps, text = 'Magnet A: ', font = font3, bg = 'white')
magnetAb = Label(temps, text = str(magnetATemp) + ' K', font = font3, bg = 'white')
magnetAa.place(relx=0.5, rely=0.6, anchor = E)
magnetAb.place(relx=0.5, rely=0.6, anchor = W)

#Magnet B Temperature
magnetBa = Label(temps, text = 'Magnet B: ', font = font3, bg = 'white')
magnetBb = Label(temps, text = str(magnetBTemp) + ' K', font = font3, bg = 'white')
magnetBa.place(relx=0.5, rely=0.75, anchor = E)
magnetBb.place(relx=0.5, rely=0.75, anchor = W)

#Switch Temperature
switcha = Label(temps, text = 'Switch: ', font = font3, bg = 'white')
switchb = Label(temps, text = str(switchTemp) + ' K', font = font3, bg = 'white')
switcha.place(relx=0.5, rely=0.9, anchor = E)
switchb.place(relx=0.5, rely=0.9, anchor = W)


#Creates a "Ramp Up" Button
global b1
b1 = Button(text = 'Ramp Up', font = font2, relief = 'raised',background='deep sky blue', activebackground='lightblue', width = 13, height = 2,\
            command = lambda: start_ramp('up'))
b1.place(relx = 0.35, rely = 0.85, anchor = CENTER)

global b2
b2 = Button(text = 'Ramp Down', font = font2, relief = 'raised',background = 'orange red', activebackground = 'tomato', width = 13, height = 2,\
            command = lambda: start_ramp('down'))
b2.place(relx = 0.65, rely = 0.85, anchor = CENTER)


global b3
b3 = Button(text = 'Abort Process', font = font2, relief = 'raised',background = 'red', activebackground = 'pink', width = 13, height = 2,\
            command = lambda: abort())
b3.place(relx = 0.87, rely = 0.7, anchor = CENTER)

#update_data(connection)

#Creates a Plot of the Magnet Power Supply Current
graph = Frame(root, padx=10, pady=10, bg='white')
graph.place(relx=0.5, rely = 0.4, anchor = CENTER)

fig = Figure(figsize=(6,4))
ax = fig.add_subplot(111)
freqPlot = FigureCanvasTkAgg(fig, graph)
freqPlot.get_tk_widget().grid(row=0, column=0, columnspan=5, sticky='esnw')
ani = animation.FuncAnimation(fig, animate, interval = 500)

create_blank_status()

root.mainloop()

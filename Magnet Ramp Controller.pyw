#Author: Richard Mattish
#Last Updated: 02/27/2023

import os
from tkinter import *
from tkinter import filedialog
import platform
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.animation as animation
import time
import webbrowser
import serial
import re
import datetime


#Defines location of the Desktop as well as font and text size for use in the software
desktop = os.path.expanduser("~\Desktop")
font1 = ('Helvetica', 18)
font2 = ('Helvetica', 16)
font3 = ('Helvetica', 14)
font4 = ('Helvetica', 12)
textSize = 20

today = datetime.date.today().strftime("%m-%d-%y")
now = datetime.datetime.now().strftime("%H%M")
logPath = 'C:/Users/CUEBIT/Documents/status_logs/magnet_ramp_logs/'
logName = f'Log {today} {now}.txt'

now = datetime.datetime.now().strftime("%H:%M:%S")
log = open(logPath+logName,'w')
log.write(f'Date: {today}\n')
log.write(f'Log started at {now}\n\n')
log.close()

def startProgram(root=None):
    instance = rampController()
    instance.startGui(root)

class rampController:
    def __init__(self):      
        self.port = None
        self.stage1Temp = None
        self.stage2Temp = None
        self.magnetATemp = None
        self.magnetBTemp = None
        self.switchTemp = None
        self.sqlFile = None
        self.state = None
        self.interlock = False
        self.status = None
        self.ser = None
        self.process = None
        self.switch = False

        self.initialTime = None
        self.time_array = []
        self.current_array = []

        self.rate1 = None
        self.rate2 = None
        self.rate3 = None
        self.rate4 = None
        self.set1 = None
        self.set2 = None
        self.set3 = None
        self.set4 = None

        self.t1 = None


        #Loads the variables com and R from the variables file, and creates the file if none exists
        try:
            f = open('variables', 'r')
            variables = f.readlines()
            self.port = str(variables[0].split('=')[1]).strip()
            self.sqlFile = str(variables[1].split('=')[1]).strip()
            self.rate1 = float(variables[2].split(',')[0].split('=')[1])
            self.set1 = float(variables[2].split(',')[1].split('=')[1])
            self.rate2 = float(variables[3].split(',')[0].split('=')[1])
            self.set2 = float(variables[3].split(',')[1].split('=')[1])
            self.rate3 = float(variables[4].split(',')[0].split('=')[1])
            self.set3 = float(variables[4].split(',')[1].split('=')[1])
            self.rate4 = float(variables[5].split(',')[0].split('=')[1])
            self.set4 = float(variables[5].split(',')[1].split('=')[1])

            if self.set4 > 108.1:
                self.log_entry(f"Error with max current {self.set4}, reducing to 108.1!")
                self.set4 = 108.1

            self.log_entry('Getting variables from variables file')
        

        except:
            self.port = 'COM6'
            self.sqlFile = 'data'
            self.rate1 = 0.292
            self.set1 = 36
            self.rate2 = 0.219
            self.set2 = 72
            self.rate3 = 0.123
            self.set3 = 90
            self.rate4 = 0.052
            self.set4 = 108.1
            f = open("variables",'w')
            f.write(f'port={self.port}\nsqlFile={self.sqlFile}\nrate1={self.rate1},set1={self.set1}\nrate2={self.rate2},set2={self.set2}\
                \nrate3={self.rate3},set3={self.set3}\nrate4={self.rate4},set4={self.set4}')
            f.close()

            self.log_entry('Unsuccessful: Writing new variables file and resetting all variables to default values')

    def get_settings(self):
        # Return an array or collection of settings here
        # Module can have more than 1 set of settings.
        return []

    def get_menus(self):

        # This returns what menus (except for settings) should be made for this
        # module. This example adds a "Misc" dropdown, with 3 values, and 1 separator
        

        _file_menu = module.Menu()
        # Define what the button does
        _file_menu._options["ramp_controller"] = self.startGui
        # Defines order in list (only 1 here though)
        _file_menu._opts_order.append("ramp_controller")
        # Describes what it does
        _file_menu._helps["ramp_controller"] = 'Says I Ran a Thing'
        # What you see in the list to click on
        _file_menu._labels["ramp_controller"] = "Ramp controller"
        # What menu to add this to
        _file_menu._label = "File"

        # Returns an array of menus (only 1 in this case)
        return [_file_menu]

    def log_entry(self, text):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        log = open(logPath+logName, 'a')
        log.write(f'{now}\t{text}\n\n')
        log.close()


    def start_ramp(self, dir):      
        if not self.interlock:
            self.interlock = True
            self.time_array = []
            self.current_array = []
            self.state = 'start'

            self.log_entry(f'state={self.state}')

            if self.ser is None:
                try:
                    self.ser = serial.Serial(self.port, 9600, timeout=3)
                except Exception as err:
                    print(err)
                    self.interlock = False
                    helpMessage ='Could not connect to magnet controller. Check connection and try again'

                    self.log_entry(helpMessage)

                    messageVar = Message(self.root, text = helpMessage, font = font2, width = 600) 
                    messageVar.config(bg='firebrick1')
                    messageVar.place(relx = 0, rely = 1, anchor = SW)
                    self.root.after(5000, messageVar.destroy)
                    return
            self.initialTime = time.time()

            if dir == 'up':
                self.log_entry('Ramp Up Process Started')

                self.process = 'energize'
                self.status.destroy()
                #Creates Status Box
                self.status = Frame(self.root, width = 275, height = 300,background = 'white', highlightbackground = 'black', highlightthickness = 1)
                self.status.place(relx = 0.87, rely = 0.4, anchor = CENTER)
                #Changes Status Label
                statusLabel = Label(self.status, text = 'Status: Energizing B', font = font1, bg = 'white', fg = 'blue')
                statusLabel.place(relx=0.5, rely=0.15, anchor = CENTER)


                #Stage 1 Process
                stage1 = Label(self.status, text = 'Stage 1: ', font = font3, bg = 'yellow')
                process1= Label(self.status, text = 'Heating Switch', font = font3, bg = 'yellow')
                stage1.place(relx=0.35, rely=0.3, anchor = E)
                process1.place(relx=0.35, rely=0.3, anchor = W)

                #Stage 2 Process
                stage2 = Label(self.status, text = 'Stage 2: ', font = font3, bg = 'white')
                process2 = Label(self.status, text = 'Ramping Up', font = font3, bg = 'white')
                process2b = Label(self.status, text = 'R = 0.000 A/s', font = font4, bg = 'white')
                stage2.place(relx=0.35, rely=0.45, anchor = E)
                process2.place(relx=0.35, rely=0.45, anchor = W)
                process2b.place(relx=0.35, rely=0.55, anchor=W)

                #Stage 3 Process
                stage3 = Label(self.status, text = 'Stage 3: ', font = font3, bg = 'white')
                process3 = Label(self.status, text = 'Cooling Switch', font = font3, bg = 'white')
                stage3.place(relx=0.35, rely=0.65, anchor = E)
                process3.place(relx=0.35, rely=0.65, anchor = W)

                #Stage 4 Process
                stage4 = Label(self.status, text = 'Stage 4: ', font = font3, bg = 'white')
                process4 = Label(self.status, text = 'Ramping Down', font = font3, bg = 'white')
                process4b = Label(self.status, text = 'R = 0.5 A/s', font = font4, bg = 'white')
                stage4.place(relx=0.35, rely=0.8, anchor = E)
                process4.place(relx=0.35, rely=0.8, anchor = W)
                process4b.place(relx=0.35, rely=0.9, anchor=W)

                self.ramp_up()

            elif dir == 'down':
                self.log_entry('Ramp Down Process Started')
                self.process = 'de-energize'
                self.status.destroy()
                #Creates Status Box
                self.status = Frame(self.root, width = 275, height = 300,background = 'white', highlightbackground = 'black', highlightthickness = 1)
                self.status.place(relx = 0.87, rely = 0.4, anchor = CENTER)
                #Changes Status Label
                statusLabel = Label(self.status, text = 'Status: De-energizing B', font = font1, bg = 'white', fg = 'blue')
                statusLabel.place(relx=0.5, rely=0.15, anchor = CENTER)


                #Stage 1 Process
                stage1 = Label(self.status, text = 'Stage 1: ', font = font3, bg = 'yellow')
                process1 = Label(self.status, text = 'Ramping Up', font = font3, bg = 'yellow')
                process1b = Label(self.status, text = 'R = 0.5 A/s', font = font4, bg = 'yellow')
                stage1.place(relx=0.35, rely=0.3, anchor = E)
                process1.place(relx=0.35, rely=0.3, anchor = W)
                process1b.place(relx=0.35, rely=0.4, anchor = W)

                #Stage 2 Process
                stage2 = Label(self.status, text = 'Stage 2: ', font = font3, bg = 'white')
                process2 = Label(self.status, text = 'Heating Switch', font = font3, bg = 'white')
                stage2.place(relx=0.35, rely=0.5, anchor = E)
                process2.place(relx=0.35, rely=0.5, anchor = W)

                #Stage 3 Process
                stage3 = Label(self.status, text = 'Stage 3: ', font = font3, bg = 'white')
                process3 = Label(self.status, text = 'Ramping Down', font = font3, bg = 'white')
                process3b = Label(self.status, text = 'R = -0.1 A/s', font = font4, bg = 'white')
                stage3.place(relx=0.35, rely=0.65, anchor = E)
                process3.place(relx=0.35, rely=0.65, anchor = W)
                process3b.place(relx=0.35, rely=0.75, anchor=W)

                #Stage 4 Process
                stage4 = Label(self.status, text = 'Stage 4: ', font = font3, bg = 'white')
                process4 = Label(self.status, text = 'Cooling Switch', font = font3, bg = 'white')
                stage4.place(relx=0.35, rely=0.85, anchor = E)
                process4.place(relx=0.35, rely=0.85, anchor = W)

                self.ramp_down()
        else:
            helpMessage ='Cannot start another process while the magnet is being ramped' 
            messageVar = Message(self.root, text = helpMessage, font = font2, width = 600) 
            messageVar.config(bg='firebrick1')
            messageVar.place(relx = 0, rely = 1, anchor = SW)
            self.root.after(5000, messageVar.destroy)

    def ramp_up(self):
        if self.state == 'abort':
            return
        
        if self.state == 'start':

            # Set the ramp target to set4.
            self.ser.write(str.encode(f'SET MID {self.set4/2:.1f}\n'))
            reading = self.ser.readline().decode()
            self.ser.write(str.encode(f'SET MAX {self.set4:.1f}\n'))
            reading = self.ser.readline().decode()

            #Turns the heater on to warm up the switch
            self.ser.write(str.encode('H1?\n'))
            reading = self.ser.readline().decode()
            if re.search('HEATER STATUS: ON', reading) == None:
                print(reading)
                print('Error: Heater did not turn on')
                self.log_entry(f'Error: Heater did not turn on\n{reading}')
                return
            self.state = 'warm_up'
            self.log_entry(f'state={self.state}')
            self.switch = True
        
        elif self.state == 'warm_up':
            self.check_temperature('up')
        
        elif self.state == 'start_ramp':
            #Starts the current ramping upward
            self.ser.write(str.encode(f'SR{self.rate1}?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-self.rate1) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.ser.write(str.encode('R!\n'))
            self.state = 'ramp_1'
            self.log_entry(f'state={self.state}')

            #Stage 1 Process
            stage1 = Label(self.status, text = 'Stage 1: ', font = font3, bg = 'white')
            process1= Label(self.status, text = 'Heating Switch', font = font3, bg = 'white')
            stage1.place(relx=0.35, rely=0.3, anchor = E)
            process1.place(relx=0.35, rely=0.3, anchor = W)

            #Stage 2 Process
            stage2 = Label(self.status, text = 'Stage 2: ', font = font3, bg = 'yellow')
            process2 = Label(self.status, text = 'Ramping Up', font = font3, bg = 'yellow')
            process2b = Label(self.status, text = f'R = {self.rate1} A/s', font = font4, bg = 'yellow')
            stage2.place(relx=0.35, rely=0.45, anchor = E)
            process2.place(relx=0.35, rely=0.45, anchor = W)
            process2b.place(relx=0.35, rely=0.55, anchor=W)
        
        elif self.state == 'ramp_1':
            self.check_current(self.set1, 'up')

        elif self.state == 'set_rate_2':
            #Lowers the ramp rate to 0.219 A/sec when I=36 A
            self.ser.write(str.encode(f'SR{self.rate2}?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-self.rate2) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.state = 'ramp_2'
            self.log_entry(f'state={self.state}')

            process2b = Label(self.status, text = f'R = {self.rate2} A/s', font = font4, bg = 'yellow')
            process2b.place(relx=0.35, rely=0.55, anchor=W)
        
        elif self.state == 'ramp_2':
            self.check_current(self.set2, 'up')

        elif self.state == 'set_rate_3':
            #Lowers the ramp rate to 0.123 A/sec when I=72 A
            self.ser.write(str.encode(f'SR{self.rate3}?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-self.rate3) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.state = 'ramp_3'
            self.log_entry(f'state={self.state}')

            process2b = Label(self.status, text = f'R = {self.rate3} A/s', font = font4, bg = 'yellow')
            process2b.place(relx=0.35, rely=0.55, anchor=W)

        elif self.state == 'ramp_3':
            self.check_current(self.set3, 'up')

        elif self.state == 'set_rate_4':
            #Lowers the ramp rate to 0.052 A/sec when I=90 A
            self.ser.write(str.encode(f'SR{self.rate4}?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-self.rate4) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.state = 'ramp_4'
            self.log_entry(f'state={self.state}')

            process2b = Label(self.status, text = f'R = {self.rate4} A/s', font = font4, bg = 'yellow')
            process2b.place(relx=0.35, rely=0.55, anchor=W)

        elif self.state == 'ramp_4':
            self.check_current(self.set4, 'up')

        elif self.state == 'heat_off':
            #Turns the Heater off
            self.ser.write(str.encode('H0?\n'))
            reading = self.ser.readline().decode()
            if re.search('HEATER STATUS: SWITCHED OFF', reading) == None:
                print(reading)
                print('Error: Heater did not turn off')
                self.log_entry(f'Error: Heater did not turn off\n{reading}')
                self.ser.write(str.encode('H1?\n'))
            self.state = 'cool_down'
            self.log_entry(f'state={self.state}')

            #Stage 2 Process
            stage2 = Label(self.status, text = 'Stage 2: ', font = font3, bg = 'white')
            process2 = Label(self.status, text = 'Ramping Up', font = font3, bg = 'white')
            process2b = Label(self.status, text = 'R = 0.000 A/s', font = font4, bg = 'white')
            stage2.place(relx=0.35, rely=0.45, anchor = E)
            process2.place(relx=0.35, rely=0.45, anchor = W)
            process2b.place(relx=0.35, rely=0.55, anchor=W)

            #Stage 3 Process
            stage3 = Label(self.status, text = 'Stage 3: ', font = font3, bg = 'yellow')
            process3 = Label(self.status, text = 'Cooling Switch', font = font3, bg = 'yellow')
            stage3.place(relx=0.35, rely=0.65, anchor = E)
            process3.place(relx=0.35, rely=0.65, anchor = W)
        
        elif self.state == 'cool_down':
            self.check_temperature('down')
        
        elif self.state == 'finished':
            self.switch = False
            #Sets the ramp rate
            self.ser.write(str.encode('SR0.5?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-0.5) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
            self.ser.write(str.encode('R0\n'))
            self.state = 'supply_down'
            self.log_entry(f'state={self.state}')

            #Stage 3 Process
            stage3 = Label(self.status, text = 'Stage 3: ', font = font3, bg = 'white')
            process3 = Label(self.status, text = 'Cooling Switch', font = font3, bg = 'white')
            stage3.place(relx=0.35, rely=0.65, anchor = E)
            process3.place(relx=0.35, rely=0.65, anchor = W)


            #Stage 4 Process
            stage4 = Label(self.status, text = 'Stage 4: ', font = font3, bg = 'yellow')
            process4 = Label(self.status, text = 'Ramping Down', font = font3, bg = 'yellow')
            process4b = Label(self.status, text = 'R = -0.5 A/s', font = font4, bg = 'yellow')
            stage4.place(relx=0.35, rely=0.8, anchor = E)
            process4.place(relx=0.35, rely=0.8, anchor = W)
            process4b.place(relx=0.35, rely=0.9, anchor=W)
        
        elif self.state == 'supply_down':
            self.check_current(0, 'down')

        elif self.state == 'done':
            self.create_blank_status()

            self.interlock = False
            return
        
        self.root.after(500, lambda: self.ramp_up())


    def ramp_down(self):
        if self.state == 'abort':
            return

        if self.state == 'start':
            #Starts the current ramping upward
            self.ser.write(str.encode('SR0.5?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-0.5) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.ser.write(str.encode('R!\n'))
            self.state = 'ramp_up'
            self.log_entry(f'state={self.state}')

        elif self.state == 'ramp_up':
            self.check_current(self.set4, 'up')
        
        elif self.state == 'heat_on':
            #Turns the heater on to warm up the switch
            self.ser.write(str.encode('H1?\n'))
            reading = self.ser.readline().decode()
            print(reading)
            if re.search('HEATER STATUS: ON', reading) == None:
                print(reading)
                print('Error: Heater did not turn on')
                self.log_entry(f'Error: Heater did not turn on\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.state = 'warm_up'
            self.log_entry(f'state={self.state}')
            self.switch = True

            #Stage 1 Process
            stage1 = Label(self.status, text = 'Stage 1: ', font = font3, bg = 'white')
            process1 = Label(self.status, text = 'Ramping Up', font = font3, bg = 'white')
            process1b = Label(self.status, text = 'R = 0.0 A/s', font = font4, bg = 'white')
            stage1.place(relx=0.35, rely=0.3, anchor = E)
            process1.place(relx=0.35, rely=0.3, anchor = W)
            process1b.place(relx=0.35, rely=0.4, anchor = W)

            #Stage 2 Process
            stage2 = Label(self.status, text = 'Stage 2: ', font = font3, bg = 'yellow')
            process2 = Label(self.status, text = 'Heating Switch', font = font3, bg = 'yellow')
            stage2.place(relx=0.35, rely=0.5, anchor = E)
            process2.place(relx=0.35, rely=0.5, anchor = W)

        elif self.state == 'warm_up':
            self.check_temperature('up')

        elif self.state == 'start_ramp':
            #Sets the ramp rate for the downward ramp cycle to rate4
            self.ser.write(str.encode(f'SR{self.rate4}?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-self.rate4) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
            self.state = 'ramp_1'
            self.log_entry(f'state={self.state}')
            #Ramps the magnet current down
            self.ser.write(str.encode('R0\n'))

            #Stage 2 Process
            stage2 = Label(self.status, text = 'Stage 2: ', font = font3, bg = 'white')
            process2 = Label(self.status, text = 'Heating Switch', font = font3, bg = 'white')
            stage2.place(relx=0.35, rely=0.5, anchor = E)
            process2.place(relx=0.35, rely=0.5, anchor = W)

            #Stage 3 Process
            stage3 = Label(self.status, text = 'Stage 3: ', font = font3, bg = 'yellow')
            process3 = Label(self.status, text = 'Ramping Down', font = font3, bg = 'yellow')
            process3b = Label(self.status, text = f'R = -{self.rate4} A/s', font = font4, bg = 'yellow')
            stage3.place(relx=0.35, rely=0.65, anchor = E)
            process3.place(relx=0.35, rely=0.65, anchor = W)
            process3b.place(relx=0.35, rely=0.75, anchor=W)
        
        elif self.state == 'ramp_1':
            self.check_current(self.set3, 'down')

        elif self.state == 'set_rate_2':
            #Raises the ramp rate to rate3 when I=set3
            self.ser.write(str.encode(f'SR{self.rate3}?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-self.rate3) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.state = 'ramp_2'
            self.log_entry(f'state={self.state}')

            process3b = Label(self.status, text = f'R = -{self.rate3} A/s', font = font4, bg = 'yellow')
            process3b.place(relx=0.35, rely=0.75, anchor=W)

        elif self.state == 'ramp_2':
            self.check_current(self.set2, 'down')

        elif self.state == 'set_rate_3':
            #Raises the ramp rate to rate2 when I=set2
            self.ser.write(str.encode(f'SR{self.rate2}?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-self.rate2) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.state = 'ramp_3'
            self.log_entry(f'state={self.state}')

            process3b = Label(self.status, text = f'R = -{self.rate2} A/s', font = font4, bg = 'yellow')
            process3b.place(relx=0.35, rely=0.75, anchor=W)

        elif self.state == 'ramp_3':
            self.check_current(self.set1, 'down')

        elif self.state == 'set_rate_4':
            #Raises the ramp rate to rate1 when I=set1
            self.ser.write(str.encode(f'SR{self.rate1}?\n'))
            reading = self.ser.readline().decode()
            start = re.search('RAMP RATE: ', reading).span()[1] + 1
            end = re.search(' A/SEC', reading).span()[0] - 1
            rate = float(reading[start:end])
            if abs(rate-self.rate1) >= 0.05:
                print(reading)
                print('Error: Rate not set correctly')
                self.log_entry(f'Error: Rate not set correctly\n{reading}')
                self.ser.write(str.encode('R0?\n'))
                self.check_current(0, 'down')
                return
            self.state = 'ramp_down'
            self.log_entry(f'state={self.state}')

            process3b = Label(self.status, text = f'R = -{self.rate1} A/s', font = font4, bg = 'yellow')
            process3b.place(relx=0.35, rely=0.75, anchor=W)
        
        elif self.state == 'ramp_down':
            self.check_current(0, 'down')

        elif self.state == 'heat_off':
            #Turns the Heater off
            self.ser.write(str.encode('H0?\n'))
            reading = self.ser.readline().decode()
            if re.search('HEATER STATUS: OFF', reading) == None:
                print(reading)
                print('Error: Heater did not turn off')
                self.log_entry(f'Error: Heater did not turn off\n{reading}')
            self.state = 'cool_down'
            self.log_entry(f'state={self.state}')
            self.switch = False

            #Stage 3 Process
            stage3 = Label(self.status, text = 'Stage 3: ', font = font3, bg = 'white')
            process3 = Label(self.status, text = 'Ramping Down', font = font3, bg = 'white')
            process3b = Label(self.status, text = 'R = -0.000 A/s', font = font4, bg = 'white')
            stage3.place(relx=0.35, rely=0.65, anchor = E)
            process3.place(relx=0.35, rely=0.65, anchor = W)
            process3b.place(relx=0.35, rely=0.75, anchor=W)

            #Stage 4 Process
            stage4 = Label(self.status, text = 'Stage 4: ', font = font3, bg = 'yellow')
            process4 = Label(self.status, text = 'Cooling Switch', font = font3, bg = 'yellow')
            stage4.place(relx=0.35, rely=0.85, anchor = E)
            process4.place(relx=0.35, rely=0.85, anchor = W)

        elif self.state == 'cool_down':
            self.check_temperature('down')

        elif self.state == 'finished':
            self.create_blank_status()

            self.interlock = False
            return

        self.root.after(500, lambda: self.ramp_down())

    # Gets the current produced by the supply, and updates the times and current arrays
    def get_current(self):
        self.ser.write(str.encode('GO?\n'))
        reading = self.ser.readline().decode()
        start = re.search('OUTPUT:', reading).span()[1] + 1
        end = re.search('AMPS', reading).span()[0] - 1
        current = float(reading[start:end].strip())

        self.time_array.append(time.time()-self.initialTime)
        self.current_array.append(current)
        return current

    #Checks the current to see if it has reached the setpoint yet
    def check_current(self, setpoint, dir):
        if setpoint == self.set4 or setpoint == 0:
            self.ser.write(str.encode('RS?\n'))
            reading = self.ser.readline().decode()
            self.log_entry(reading)

            if re.search('RAMP STATUS: HOLDING ON', reading) != None:
                if dir == 'up':
                    if self.state == 'ramp_up':
                        self.state = 'heat_on'
                        self.log_entry(f'state={self.state}')
                    elif self.state == 'ramp_4':
                        self.state = 'heat_off'
                        self.log_entry(f'state={self.state}')
                elif dir == 'down':
                    if self.state == 'ramp_down':
                        self.state = 'heat_off'
                        self.log_entry(f'state={self.state}')
                    elif self.state == 'supply_down':
                        self.state = 'done'
                        self.log_entry(f'state={self.state}')
                    elif self.state == 'abort':
                        self.state = 'done'
                        self.log_entry(f'state={self.state}')

            else:
                self.get_current()
                return
                
        else:
            current = self.get_current()

            if dir == 'up':
                if current <= setpoint:
                    return
                elif self.state == 'ramp_1':
                    self.state = 'set_rate_2'
                    self.log_entry(f'state={self.state}')
                elif self.state == 'ramp_2':
                    self.state = 'set_rate_3'
                    self.log_entry(f'state={self.state}')
                elif self.state == 'ramp_3':
                    self.state = 'set_rate_4'
                    self.log_entry(f'state={self.state}')

            if dir == 'down':
                if current > setpoint:
                    return

                elif self.state == 'ramp_1':
                    self.state = 'set_rate_2'
                    self.log_entry(f'state={self.state}')
                elif self.state == 'ramp_2':
                    self.state = 'set_rate_3'
                    self.log_entry(f'state={self.state}')
                elif self.state == 'ramp_3':
                    self.state = 'set_rate_4'
                    self.log_entry(f'state={self.state}')
                
                #This statement likely does nothing but I left it for flow of thought (should be called in previous if statement)
                elif self.state == 'supply_down':
                    self.state = 'done'
                    self.log_entry(f'state={self.state}')


    #Checks the switch temperature to ensure it is warmed up
    def check_temperature(self, dir):
        if dir == 'up':
            if self.switchTemp < 6:
                return
            if self.state == 'warm_up':
                self.state = 'start_ramp'
                self.log_entry(f'state={self.state}')
                
        if dir == 'down':
            self.log_entry(f'switchTemp = {self.switchTemp} K')
            if self.switchTemp > 4.5:
                return
            if self.state == 'heat_switch':
                self.state = 'set_rate'
                self.log_entry(f'state={self.state}')
            elif self.state == 'cool_down' and self.switchTemp < 4.5:
                self.state = 'finished'
                self.log_entry(f'state={self.state}')
            

    def update_data(self, connection):
        self.stage1Temp = connection.get_float("Temperature_Cryo_S1")[1]
        self.stage2Temp = connection.get_float("Temperature_Cryo_S2")[1]
        self.magnetATemp = connection.get_float("Temperature_Cryo_MA")[1]
        self.magnetBTemp = connection.get_float("Temperature_Cryo_MB")[1]
        self.switchTemp = connection.get_float("Temperature_Cryo_Sw")[1]

        self.stage1b.config(text = f'{self.stage1Temp:.2f} K')
        self.stage2b.config(text = f'{self.stage2Temp:.2f} K')
        self.magnetAb.config(text = f'{self.magnetATemp:.2f} K')
        self.magnetBb.config(text = f'{self.magnetBTemp:.2f} K')
        self.switchb.config(text = f'{self.switchTemp:.2f} K')

        self.temps.after(1000, lambda: self.update_data(connection))


    #Opens Settings Window, which allows the user to change the persistent global variables V and R
    def Settings(self):
        settings = Toplevel(self.root)
        settings.geometry('400x300')
        settings.wm_title("Settings")
        if platform.system() == 'Windows':
            settings.iconbitmap("icons/settings.ico")
        settings.configure(bg='grey95')
        L1 = Label(settings, text = 'COM Port:', font = font2, bg='grey95')
        L1.place(relx=0.3, rely=0.2, anchor = E)
        E1 = Entry(settings, font = font2, width = 6)
        E1.insert(0,str(self.port))
        E1.place(relx=0.3, rely=0.2, anchor = W)

        L2 = Label(settings, text = 'SQL File:', font = font2, bg='grey95')
        L2.place(relx=0.8, rely=0.2, anchor = E)
        E2 = Entry(settings, font = font2, width = 5)
        E2.insert(0,str(self.sqlFile))
        E2.place(relx=0.8, rely=0.2, anchor = W)
        
        L3 = Label(settings, text = 'Rate 1:', font = font2, bg='grey95')
        L3.place(relx=0.25, rely=0.4, anchor = E)
        E3 = Entry(settings, font = font2, width = 5)
        E3.insert(0,str(self.rate1))
        E3.place(relx=0.25, rely=0.4, anchor = W)
        L3units = Label(settings, text = 'A/s', font = font2, bg = 'grey95')
        L3units.place(relx=0.4, rely=0.4, anchor = W)

        L4 = Label(settings, text = 'Set 1:', font = font2, bg='grey95')
        L4.place(relx=0.75, rely=0.4, anchor = E)
        E4 = Entry(settings, font = font2, width = 5)
        E4.insert(0,str(self.set1))
        E4.place(relx=0.75, rely=0.4, anchor = W)
        L4units = Label(settings, text = 'A', font = font2, bg='grey95')
        L4units.place(relx=0.9, rely=0.4, anchor = W)

        L5 = Label(settings, text = 'Rate 2:', font = font2, bg='grey95')
        L5.place(relx=0.25, rely=0.5, anchor = E)
        E5 = Entry(settings, font = font2, width = 5)
        E5.insert(0,str(self.rate2))
        E5.place(relx=0.25, rely=0.5, anchor = W)
        L5units = Label(settings, text = 'A/s', font = font2, bg = 'grey95')
        L5units.place(relx=0.4, rely=0.5, anchor = W)

        L6 = Label(settings, text = 'Set 2:', font = font2, bg='grey95')
        L6.place(relx=0.75, rely=0.5, anchor = E)
        E6 = Entry(settings, font = font2, width = 5)
        E6.insert(0,str(self.set2))
        E6.place(relx=0.75, rely=0.5, anchor = W)
        L6units = Label(settings, text = 'A', font = font2, bg='grey95')
        L6units.place(relx=0.9, rely=0.5, anchor = W)

        L7 = Label(settings, text = 'Rate 3:', font = font2, bg='grey95')
        L7.place(relx=0.25, rely=0.6, anchor = E)
        E7 = Entry(settings, font = font2, width = 5)
        E7.insert(0,str(self.rate3))
        E7.place(relx=0.25, rely=0.6, anchor = W)
        L7units = Label(settings, text = 'A/s', font = font2, bg = 'grey95')
        L7units.place(relx=0.4, rely=0.6, anchor = W)

        L8 = Label(settings, text = 'Set 3:', font = font2, bg='grey95')
        L8.place(relx=0.75, rely=0.6, anchor = E)
        E8 = Entry(settings, font = font2, width = 5)
        E8.insert(0,str(self.set3))
        E8.place(relx=0.75, rely=0.6, anchor = W)
        L8units = Label(settings, text = 'A', font = font2, bg='grey95')
        L8units.place(relx=0.9, rely=0.6, anchor = W)

        L9 = Label(settings, text = 'Rate 4:', font = font2, bg='grey95')
        L9.place(relx=0.25, rely=0.7, anchor = E)
        E9 = Entry(settings, font = font2, width = 5)
        E9.insert(0,str(self.rate4))
        E9.place(relx=0.25, rely=0.7, anchor = W)
        L9units = Label(settings, text = 'A/s', font = font2, bg = 'grey95')
        L9units.place(relx=0.4, rely=0.7, anchor = W)

        L10 = Label(settings, text = 'Set 4:', font = font2, bg='grey95')
        L10.place(relx=0.75, rely=0.7, anchor = E)
        E10 = Entry(settings, font = font2, width = 5)
        E10.insert(0,str(self.set4))
        E10.place(relx=0.75, rely=0.7, anchor = W)
        L10units = Label(settings, text = 'A', font = font2, bg='grey95')
        L10units.place(relx=0.9, rely=0.7, anchor = W)

        b1 = Button(settings, text = 'Update', relief = 'raised', background='lightblue', activebackground='blue', font = font1, width = 10, height = 1,\
                    command = lambda: [self.updateSettings(str(E1.get()),str(E2.get()),float(E3.get()),float(E4.get()),float(E5.get()),float(E6.get()),float(E7.get()),float(E8.get()),float(E9.get()), float(E10.get())),settings.destroy()])
        b1.place(relx=0.75, rely=0.9, anchor = CENTER)

        b2 = Button(settings, text = 'Reset', relief = 'raised', background='pink', activebackground='red', font = font1, width = 10, height = 1, command = lambda: [self.updateSettings('COM6','data',0.292,36,0.219,72,0.123,90,0.052,108.1),settings.destroy()])
        b2.place(relx=0.25, rely=0.9, anchor = CENTER)

    #Updates the persistent global variables port and sql, as well as store the ramp rates and set points
    def updateSettings(self, E1, E2, E3, E4, E5, E6, E7, E8, E9, E10):
        if not self.interlock:
            self.port = E1
            self.sqlFile = E2
            self.rate1 = E3
            self.set1 = E4
            self.rate2 = E5
            self.set2 = E6
            self.rate3 = E7
            self.set3 = E8
            self.rate4 = E9
            self.set4 = E10
            f = open("variables",'w')
            f.write(f'port={self.port}\nsqlFile={self.sqlFile}\nrate1={self.rate1},set1={self.set1}\nrate2={self.rate2},set2={self.set2}\
                \nrate3={self.rate3},set3={self.set3}\nrate4={self.rate4},set4={self.set4}')
            f.close()
        else:
            helpMessage ='Cannot change settings while ramping the magnet' 
            messageVar = Message(self.root, text = helpMessage, font = font2, width = 600) 
            messageVar.config(bg='firebrick1')
            messageVar.place(relx = 0, rely = 1, anchor = SW)
            self.root.after(5000, messageVar.destroy)


    def manualControl(self):
        manual = Toplevel(self.root)
        manual.geometry('440x330')
        manual.wm_title("Manual Serial Control")
        if platform.system() == 'Windows':
            manual.iconbitmap("icons/serial.ico")
        manual.resizable(False, False)
        #manual.configure(bg='white')
        manual.configure(bg='grey95')
        v = Scrollbar(manual, orient = 'vertical')
        t = Text(manual, font = font4, bg='white', width = 10, height = 15, wrap = NONE, yscrollcommand = v.set)
        t.insert(END, "*********************************************************************************************************************\n")
        t.insert(END, "\t\tBasic Commands\n\n")
        t.insert(END, "\tSet Ramp Rate: SR{rate}?\n")
        t.insert(END, "\tRamp Up: R!\n")
        t.insert(END, "\tRamp Down: R0?\n")
        t.insert(END, "\tRamp Status: RS?\n")
        t.insert(END, "\tHeater Off: H0?\n")
        t.insert(END, "\tHeater On: H1?\n")
        t.insert(END, "\tGet Output: GO?\n")
        t.insert(END, "*********************************************************************************************************************\n\n\n\n")
        t.pack(side=TOP, fill=X)
        v.config(command=t.yview)

        
        L1 = Label(manual, text = 'Serial Command:', font = font2, bg='grey95')
        L1.place(relx=0.45, rely=0.91, anchor = E)
        E1 = Entry(manual, font = font2, width = 7)
        E1.place(relx=0.45, rely=0.91, anchor = W)

        b1 = Button(manual, text = 'Send', relief = 'raised', background='lightblue', activebackground='blue', font = font1, width = 5, height = 1,\
                    command = lambda: self.updateText(E1.get(), t))
        b1.place(relx=0.85, rely=0.91, anchor = CENTER)

        if self.ser is None:
            try:
                self.ser = serial.Serial(self.port, 9600, timeout=3)
            except:
                self.interlock = False
                helpMessage ='Could not connect to magnet controller. Check connection and try again'

                self.log_entry(helpMessage)

                messageVar = Message(self.root, text = helpMessage, font = font2, width = 600) 
                messageVar.config(bg='firebrick1')
                messageVar.place(relx = 0, rely = 1, anchor = SW)
                self.root.after(5000, messageVar.destroy)
                manual.destroy()
                return

    def updateText(self, text, t):
        t.insert(END, f'{text}\n')
        self.ser.write(str.encode(f'{text}\n'))
        if "?" in text:
            reading = self.ser.readline().decode()
            t.insert(END, f'{reading}\n')

        


    #Opens a url in a new tab in the default webbrowser
    def callback(url):
        webbrowser.open_new_tab(url)


    #Opens About Window with software information
    def About(self):
        name = "Magnet Ramp Controller"
        version = 'Version: 2.0.0'
        date = 'Date: 02/27/2022'
        support = 'Support: '
        url = 'https://github.com/rhmatti/Magnet-Ramp-Controller'
        copyrightMessage ='Copyright © 2023 Richard Mattish All Rights Reserved.'
        t = Toplevel(self.root)
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
        l5 = Label(t, text = 'https://github.com/rhmatti/\nMagnet-Ramp-Controller', bg = 'white', fg = 'blue', font=font4)
        l5.place(relx = 0.31, rely=0.48, anchor = W)
        l5.bind("<Button-1>", lambda e:
        rampController.callback(url))
        messageVar = Message(t, text = copyrightMessage, bg='white', font = font4, width = 600)
        messageVar.place(relx = 0.5, rely = 1, anchor = S)

    def Instructions(self):
        instructions = Toplevel(self.root)
        instructions.geometry('1280x720')
        instructions.wm_title("User Instructions")
        instructions.configure(bg='white')
        if platform.system() == 'Windows':
            instructions.iconbitmap("icons/magnet.ico")
        v = Scrollbar(instructions, orient = 'vertical')
        t = Text(instructions, font = font4, bg='white', width = 100, height = 100, wrap = NONE, yscrollcommand = v.set)
        t.insert(END, "*********************************************************************************************************************\n")
        t.insert(END, "Program: Magnet Ramp Controller\n")
        t.insert(END, "Author: Richard Mattish\n")
        t.insert(END, "Last Updated: 02/27/2023\n\n")
        t.insert(END, "Function:  This program provides a graphical user interface for controlling\n")
        t.insert(END, "\tthe superconducting magnet in the CUEBIT source.\n")
        t.insert(END, "*********************************************************************************************************************\n\n\n\n")

        t.pack(side=TOP, fill=X)
        v.config(command=t.yview)

    def save_data(self):
        fileName = str(filedialog.asksaveasfile(initialdir = desktop,title = "Save",filetypes = (("Text Document","*.txt*"),("Text Document","*.txt*"))))
        fileName = fileName.split("'")
        fileName = fileName[1]
        outputFile = open(fileName + '.txt', "w")
        outputFile.write('Time (s)\tCurrent (°C)\n\n')

        for i in range(0,len(self.time_array)-1):
            outputFile.write(str(self.time_array[i]) + '\t' + str(self.current_array[i]) + '\n')

        outputFile.close()
        webbrowser.open(fileName + '.txt')

    def abort(self):
        if self.interlock:

            if not self.switch:
                #Ramps the magnet current down
                self.ser.write(str.encode('R0\n'))

                #Sets the ramp speed to 0.5 A/s
                self.ser.write(str.encode('SR0.5?\n'))
                reading = self.ser.readline().decode()
                start = re.search('RAMP RATE: ', reading).span()[1] + 1
                end = re.search(' A/SEC', reading).span()[0] - 1
                rate = float(reading[start:end])
                if abs(rate-0.5) >= 0.05:
                    print(reading)
                    print('Error: Rate not set correctly')
                    self.log_entry(f'Error: Rate not set correctly\n{reading}')

            elif self.switch:
                if self.process == 'energize':
                    #Ramps the magnet current down
                    self.ser.write(str.encode('R0\n'))

                    if self.state == 'start_ramp' or self.state == 'ramp_1' or self.state == 'ramp_2' or self.state == 'set_rate_2':
                        #Sets the ramp speed to 0.2 A/s
                        self.ser.write(str.encode('SR0.2?\n'))
                        reading = self.ser.readline().decode()
                        start = re.search('RAMP RATE: ', reading).span()[1] + 1
                        end = re.search(' A/SEC', reading).span()[0] - 1
                        rate = float(reading[start:end])
                        if abs(rate-0.2) >= 0.05:
                            print(reading)
                            print('Error: Rate not set correctly')
                            self.log_entry(f'Error: Rate not set correctly\n{reading}')
                    else:
                        #Sets the ramp speed to 0.1 A/s
                        self.ser.write(str.encode('SR0.1?\n'))
                        reading = self.ser.readline().decode()
                        start = re.search('RAMP RATE: ', reading).span()[1] + 1
                        end = re.search(' A/SEC', reading).span()[0] - 1
                        rate = float(reading[start:end])
                        if abs(rate-0.1) >= 0.05:
                            print(reading)
                            print('Error: Rate not set correctly')
                            self.log_entry(f'Error: Rate not set correctly\n{reading}')
                elif self.process == 'de-energize':
                    if self.state == 'warm_up' or self.state == 'start_ramp' or self.state == 'ramp_1':
                        #Sets the ramp speed to 0.1 A/s
                        self.ser.write(str.encode('SR0.1?\n'))
                        reading = self.ser.readline().decode()
                        start = re.search('RAMP RATE: ', reading).span()[1] + 1
                        end = re.search(' A/SEC', reading).span()[0] - 1
                        rate = float(reading[start:end])
                        if abs(rate-0.1) >= 0.05:
                            print(reading)
                            print('Error: Rate not set correctly')
                            self.log_entry(f'Error: Rate not set correctly\n{reading}')
                    else:
                        #Sets the ramp speed to 0.2 A/s
                        self.ser.write(str.encode('SR0.2?\n'))
                        reading = self.ser.readline().decode()
                        start = re.search('RAMP RATE: ', reading).span()[1] + 1
                        end = re.search(' A/SEC', reading).span()[0] - 1
                        rate = float(reading[start:end])
                        if abs(rate-0.2) >= 0.05:
                            print(reading)
                            print('Error: Rate not set correctly')
                            self.log_entry(f'Error: Rate not set correctly\n{reading}')



            print('Process Aborted')
            self.log_entry('Process Aborted')

            self.state = 'abort'
            self.log_entry(f'state={self.state}')

            self.status.destroy()
            #Creates Status Box
            self.status = Frame(self.root, width = 275, height = 300,background = 'white', highlightbackground = 'black', highlightthickness = 1)
            self.status.place(relx = 0.87, rely = 0.4, anchor = CENTER)
            #Changes Status Label
            statusLabel = Label(self.status, text = 'Status: Aborting', font = font1, bg = 'white', fg = 'red')
            statusLabel.place(relx=0.5, rely=0.15, anchor = CENTER)


            #Abortion Process
            abortionMessage = f'Process has been aborted.\nPower supply is ramping\n down at {rate} A/s'
            abortionLabel = Label(self.status, text = abortionMessage, font = font3, bg = 'white', fg = 'red')
            abortionLabel.place(relx=0.5, rely=0.5, anchor = CENTER)

            self.monitor_abortion()



    def monitor_abortion(self):
        self.check_current(0, 'down')
        if self.state == 'done':
            self.interlock = False
            self.create_blank_status()
            if self.ser != None:
                try:
                    self.ser.close()
                    self.ser = None
                except:
                    pass
            return
        self.root.after(500, lambda: self.monitor_abortion())

    def on_stop(self):
        # This is called when the program is exited
        self.abort()

    def quitProgram(self):
        print('Quit Program')
        self.abort()
        self.root.destroy()

    def animate(self, i):
        self.ax.clear()
        xdata = self.time_array
        ydata = self.current_array
        if len(self.current_array) > 0:
            current = self.current_array[len(self.current_array)-1]
            self.ax.set_title(f'Magnet Current - {round(current,1)} A')
        else:
            self.ax.set_title('Magnet Current')
        self.ax.plot(xdata,ydata)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Current (A)')

    def create_blank_status(self):
        self.process = None

        if self.status is not None:
            self.status.destroy()
        #Creates Status Box
        self.status = Frame(self.root, width = 275, height = 300,background = 'grey92', highlightbackground = 'black', highlightthickness = 1)
        self.status.place(relx = 0.87, rely = 0.4, anchor = CENTER)
        statusLabel = Label(self.status, text = 'Status: Off', font = font1, bg = 'grey92', fg = 'blue')
        statusLabel.place(relx=0.5, rely=0.15, anchor = CENTER)

        #Stage 1 Process
        stage1 = Label(self.status, text = 'Stage 1: ', font = font3, bg = 'grey92')
        process1= Label(self.status, text = 'N/A', font = font3, bg = 'grey92')
        stage1.place(relx=0.35, rely=0.3, anchor = E)
        process1.place(relx=0.35, rely=0.3, anchor = W)


        #Stage 2 Process
        stage2 = Label(self.status, text = 'Stage 2: ', font = font3, bg = 'grey92')
        process2 = Label(self.status, text = 'N/A', font = font3, bg = 'grey92')
        stage2.place(relx=0.35, rely=0.45, anchor = E)
        process2.place(relx=0.35, rely=0.45, anchor = W)


        #Stage 3 Process
        stage3 = Label(self.status, text = 'Stage 3: ', font = font3, bg = 'grey92')
        process3 = Label(self.status, text = 'N/A', font = font3, bg = 'grey92')
        stage3.place(relx=0.35, rely=0.6, anchor = E)
        process3.place(relx=0.35, rely=0.6, anchor = W)


        #Stage 4 Process
        stage4 = Label(self.status, text = 'Stage 4: ', font = font3, bg = 'grey92')
        process4 = Label(self.status, text = 'N/A', font = font3, bg = 'grey92')
        stage4.place(relx=0.35, rely=0.75, anchor = E)
        process4.place(relx=0.35, rely=0.75, anchor = W)

        #Message
        messageLabel = Label(self.status, text = 'Progress will be shown here\nwhen a process is started', font = font3, bg = 'grey92')
        messageLabel.place(relx=0.5, rely=0.9, anchor = CENTER)

    def startGui(self, root=None):
        self.stage1Temp = 40
        self.stage2Temp = 4
        self.magnetATemp = 4
        self.magnetBTemp = 4
        self.switchTemp = 4

        from data_client import BaseDataClient
        connection = BaseDataClient()

        #This is the GUI for the software
        if root == None:
            self.root = Tk()
        else:
            self.root = root
        menu = Menu(self.root)
        self.root.config(menu=menu)

        self.root.title("Magnet Ramp Controller")
        self.root.geometry("1280x768")
        self.root.configure(bg='white')
        self.root.protocol("WM_DELETE_WINDOW", self.quitProgram)
        if platform.system() == 'Windows':
            self.root.iconbitmap("icons/magnet.ico")


        #Creates File menu
        filemenu = Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu = filemenu)
        filemenu.add_command(label="Save", command = self.save_data, accelerator="Ctrl+S")
        filemenu.add_command(label='Settings', command = self.Settings)
        filemenu.add_command(label='Manual Control', command = self.manualControl)
        filemenu.add_separator()
        filemenu.add_command(label='Exit', command= self.quitProgram)


        #Creates Help menu
        helpmenu = Menu(menu, tearoff=0)
        menu.add_cascade(label='Help', menu=helpmenu)
        helpmenu.add_command(label='Instructions', command = self.Instructions)
        helpmenu.add_command(label='About', command = self.About)

        #Creates Temperature Readouts
        self.temps = Frame(self.root, width = 225, height = 300,background = 'white', highlightbackground = 'black', highlightthickness = 1)
        self.temps.place(relx = 0.12, rely = 0.4, anchor = CENTER)
        self.tempLabel = Label(self.temps, text = 'Temperatures', font = font1, bg = 'white', fg = 'blue')
        self.tempLabel.place(relx=0.5, rely=0.15, anchor = CENTER)

        #Stage 1 Temperature
        self.stage1a = Label(self.temps, text = 'Stage 1: ', font = font3, bg = 'white')
        self.stage1b= Label(self.temps, text = str(self.stage1Temp) + ' K', font = font3, bg = 'white')
        self.stage1a.place(relx=0.5, rely=0.3, anchor = E)
        self.stage1b.place(relx=0.5, rely=0.3, anchor = W)

        #Stage 2 Temperature
        self.stage2a = Label(self.temps, text = 'Stage 2: ', font = font3, bg = 'white')
        self.stage2b = Label(self.temps, text = str(self.stage2Temp) + ' K', font = font3, bg = 'white')
        self.stage2a.place(relx=0.5, rely=0.45, anchor = E)
        self.stage2b.place(relx=0.5, rely=0.45, anchor = W)

        #Magnet A Temperature
        self.magnetAa = Label(self.temps, text = 'Magnet A: ', font = font3, bg = 'white')
        self.magnetAb = Label(self.temps, text = str(self.magnetATemp) + ' K', font = font3, bg = 'white')
        self.magnetAa.place(relx=0.5, rely=0.6, anchor = E)
        self.magnetAb.place(relx=0.5, rely=0.6, anchor = W)

        #Magnet B Temperature
        self.magnetBa = Label(self.temps, text = 'Magnet B: ', font = font3, bg = 'white')
        self.magnetBb = Label(self.temps, text = str(self.magnetBTemp) + ' K', font = font3, bg = 'white')
        self.magnetBa.place(relx=0.5, rely=0.75, anchor = E)
        self.magnetBb.place(relx=0.5, rely=0.75, anchor = W)

        #Switch Temperature
        self.switcha = Label(self.temps, text = 'Switch: ', font = font3, bg = 'white')
        self.switchb = Label(self.temps, text = str(self.switchTemp) + ' K', font = font3, bg = 'white')
        self.switcha.place(relx=0.5, rely=0.9, anchor = E)
        self.switchb.place(relx=0.5, rely=0.9, anchor = W)


        #Creates a "Ramp Up" Button
        b1 = Button(self.root, text = 'Ramp Up', font = font2, relief = 'raised',background='deep sky blue', activebackground='lightblue', width = 13, height = 2,\
                    command = lambda: self.start_ramp('up'))
        b1.place(relx = 0.35, rely = 0.85, anchor = CENTER)

        b2 = Button(self.root, text = 'Ramp Down', font = font2, relief = 'raised',background = 'orange red', activebackground = 'tomato', width = 13, height = 2,\
                    command = lambda: self.start_ramp('down'))
        b2.place(relx = 0.65, rely = 0.85, anchor = CENTER)


        b3 = Button(self.root, text = 'Abort Process', font = font2, relief = 'raised',background = 'red', activebackground = 'pink', width = 13, height = 2,\
                    command = self.abort)
        b3.place(relx = 0.87, rely = 0.7, anchor = CENTER)

        self.update_data(connection)

        #Creates a Plot of the Magnet Power Supply Current
        graph = Frame(self.root, padx=10, pady=10, bg='white')
        graph.place(relx=0.5, rely = 0.4, anchor = CENTER)

        fig = Figure(figsize=(6,4))
        self.ax = fig.add_subplot(111)
        freqPlot = FigureCanvasTkAgg(fig, graph)
        freqPlot.get_tk_widget().grid(row=0, column=0, columnspan=5, sticky='esnw')
        self.ani = animation.FuncAnimation(fig, self.animate, interval = 500)

        self.create_blank_status()

        self.root.mainloop()

startProgram()
#!/usr/bin/python3
## import sys
import os
import pyudev
import psutil
import sys

from PIL import Image  # image manipulation for Overlay
import time  # timing
import picamera  # camera driver
import shutil  # file io access like copy
from datetime import datetime  # datetime routine
import RPi.GPIO as GPIO  # gpio access
import subprocess  # call external scripts
from transitions import Machine  # state machine
import configparser  # parsing config file
import logging  # logging functions
import cups  # connection to cups printer driver
import usb  # check if printer is connected and turned on
from io import BytesIO
from wand.image import Image as image  # image manipulation lib

# get the real path of the script
REAL_PATH = os.path.dirname(os.path.realpath(__file__))

class Photobooth:
    # define state machine for taking photos
    FSMstates = ['PowerOn', 'Start', 'CountdownPhoto', 'TakePhoto', 'ShowPhoto', 'PrintPhoto', 'RefillPaper', 'RefillInk']

    def __init__(self):
        self.initStateMachine()

        logging.debug("Read Config File")
        self.readConfiguration()

        logging.debug("Config GPIO")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin_button_right, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.pin_button_left, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.pin_button_right, GPIO.FALLING, callback=self.Button2pressed, bouncetime=500)
        GPIO.add_event_detect(self.pin_button_left, GPIO.FALLING, callback=self.Button1pressed, bouncetime=500)

        logging.debug("Set TimeStamp for Buttons")
        self.time_stamp_button = time.time()

        self.button_active = False

        logging.debug("Setup Camera")
        # Setup Camera
        try:
            self.camera = picamera.PiCamera()
        except:
            logging.CRITICAL("error initializing the camera - exiting")
            raise SystemExit

        self.camera.resolution = (self.photo_w, self.photo_h)
        self.camera.hflip = self.flip_screen_h
        self.camera.vflip = self.flip_screen_v
        self.camera.framerate = self.framerate
        self.camera.rotation = self.rotation

        # load the Logo of the Photobooth and display it
        #self.overlayscreen_logo = self.overlay_image(self.screen_logo, True, 0, 5)

        # find the USB Drive, if connected
        mountPoint = self.GetMountpoint()
        self.PhotoCopyPath = mountPoint

        # path for saving photos on usb drive
        if self.PhotoCopyPath is not None:
            self.PhotoCopyPath = self.PhotoCopyPath + "/Photos"
            logging.debug("Photocopypath = " + self.PhotoCopyPath)
            if not os.path.exists(self.PhotoCopyPath):
                logging.debug("os.mkdir(self.PhotoCopyPath)")
                os.mkdir(self.PhotoCopyPath)
        else:
            logging.debug("self.PhotoCopyPath not Set -> No USB Drive Found")

        self.overlay_photo = -1
        self.overlay_frame = -1
        self.layout = 1

        # Start the Application
        self.on_enter_PowerOn()

    # Init the State machine controlling the Photobooth
    def initStateMachine(self):
        logging.debug("Init State Machine")
        self.machine = Machine(model=self, states=self.FSMstates, initial='PowerOn', ignore_invalid_triggers=True)
        # power on self test - check if printer is conected
        self.machine.add_transition(source='PowerOn', dest='PowerOn', trigger='Button1')  
        # printer is on -> goto start
        self.machine.add_transition(source='PowerOn', dest='Start', trigger='PrinterFound')  
        self.machine.add_transition(source='Start', dest='CountdownPhoto', trigger='Button1')
        self.machine.add_transition(source='Start', dest='CountdownPhoto', trigger='Button2')
        self.machine.add_transition(source='CountdownPhoto', dest='TakePhoto', trigger='CountdownPhotoTimeout')
        self.machine.add_transition(source='TakePhoto', dest='ShowPhoto', trigger='None')
        self.machine.add_transition(source='ShowPhoto', dest='PrintPhoto', trigger='Button1')  # print
        self.machine.add_transition(source='ShowPhoto', dest='Start', trigger='Button2')  # do not print
        self.machine.add_transition(source='PrintPhoto', dest='Start', trigger='PrintDone')  # print done
        # Refill Paper on printer
        self.machine.add_transition(source='PrintPhoto', dest='RefillPaper', trigger='PaperEmpty')  
        self.machine.add_transition(source='RefillPaper', dest='PrintPhoto', trigger='Button1')  
        self.machine.add_transition(source='RefillPaper', dest='PrintPhoto', trigger='Button2')
        # Refill Ink on printer
        self.machine.add_transition(source='PrintPhoto', dest='RefillInk', trigger='InkEmpty')  
        self.machine.add_transition(source='RefillInk', dest='PrintPhoto', trigger='Button1')  
        self.machine.add_transition(source='RefillInk', dest='PrintPhoto', trigger='Button2')

    # read the global configuration, folders, resolution....
    def readConfiguration(self):
        logging.debug("Read Config File")
        self.config = configparser.ConfigParser()
        self.config.sections()
        self.config.read(os.path.join(REAL_PATH, 'config.ini'))

        if self.config.getboolean("Debug", "debug", fallback=True) == True:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)

        self.printPicsEnable = self.config.getboolean("Debug", "print", fallback=True)

        if self.printPicsEnable == False:
            logging.debug("Printing pics disabled")

        self.photo_abs_file_path = os.path.join(REAL_PATH, self.config.get("Paths", "photo_path", fallback="Photos/"))
        self.screens_abs_file_path = os.path.join(REAL_PATH,
                                                  self.config.get("Paths", "screen_path", fallback="Screens/"))
        self.pin_button_left = int(self.config.get("InOut", "pin_button_left", fallback="23"))
        self.pin_button_right = int(self.config.get("InOut", "pin_button_right", fallback="24"))
        
        self.photo_w = int(self.config.get("Resolution", "photo_w", fallback="3280"))
        self.photo_h = int(self.config.get("Resolution", "photo_h", fallback="2464"))
        self.screen_w = int(self.config.get("Resolution", "screen_w", fallback="1280"))
        self.screen_h = int(self.config.get("Resolution", "screen_h", fallback="1024"))
        self.flip_screen_h = self.config.getboolean("Resolution", "flip_screen_h", fallback=False)
        self.flip_screen_v = self.config.getboolean("Resolution", "flip_screen_v", fallback=False)
        self.framerate = int(self.config.get("Resolution", "framerate", fallback="25"))
        self.rotation = int(self.config.get("Resolution", "rotation", fallback="0"))

        self.screen_turnOnPrinter = os.path.join(self.screens_abs_file_path,
                                                 self.config.get("Screens", "screen_turn_on_printer",
                                                                 fallback="ScreenTurnOnPrinter.png"))
        self.screen_logo = os.path.join(self.screens_abs_file_path,
                                        self.config.get("Screens", "screen_logo", fallback="ScreenLogo.png"))
        self.screen_choose_layout = os.path.join(self.screens_abs_file_path,
                                                 self.config.get("Screens", "screen_Choose_Layout",
                                                                 fallback="ScreenChooseLayout.png"))
        self.screen_countdown_0 = os.path.join(self.screens_abs_file_path,
                                               self.config.get("Screens", "screen_countdown_0",
                                                               fallback="ScreenCountdown0.png"))
        self.screen_countdown_1 = os.path.join(self.screens_abs_file_path,
                                               self.config.get("Screens", "screen_countdown_1",
                                                               fallback="ScreenCountdown1.png"))
        self.screen_countdown_2 = os.path.join(self.screens_abs_file_path,
                                               self.config.get("Screens", "screen_countdown_2",
                                                               fallback="ScreenCountdown2.png"))
        self.screen_countdown_3 = os.path.join(self.screens_abs_file_path,
                                               self.config.get("Screens", "screen_countdown_3",
                                                               fallback="ScreenCountdown3.png"))
        self.screen_countdown_4 = os.path.join(self.screens_abs_file_path,
                                               self.config.get("Screens", "screen_countdown_4",
                                                               fallback="ScreenCountdown4.png"))
        self.screen_countdown_5 = os.path.join(self.screens_abs_file_path,
                                               self.config.get("Screens", "screen_countdown_5",
                                                               fallback="ScreenCountdown5.png"))
        self.screen_black = os.path.join(self.screens_abs_file_path,
                                         self.config.get("Screens", "screen_black",
                                                         fallback="ScreenBlack.png"))
        self.screen_wait = os.path.join(self.screens_abs_file_path,
                                        self.config.get("Screens", "screen_wait",
                                                        fallback="ScreenWait.png"))
        self.screen_print = os.path.join(self.screens_abs_file_path,
                                         self.config.get("Screens", "screen_print",
                                                         fallback="ScreenPrint.png"))
        self.screen_printing = os.path.join(self.screens_abs_file_path,
                                         self.config.get("Screens", "screen_printing",
                                                         fallback="ScreenPrinting.png"))
        self.screen_change_ink = os.path.join(self.screens_abs_file_path,
                                              self.config.get("Screens", "screen_change_ink",
                                                              fallback="ScreenChangeInk.png"))
        self.screen_change_paper = os.path.join(self.screens_abs_file_path,
                                                self.config.get("Screens", "screen_change_paper",
                                                                fallback="ScreenChangePaper.png"))
        self.screen_frame = os.path.join(self.screens_abs_file_path,
                                                self.config.get("Screens", "screen_frame",
                                                                fallback="ScreenFrame.png"))

    # Button1 callback function. Actions depends on state of the Photobooth state machine
    def Button1pressed(self, event):
        logging.debug(f"Button1pressed, active = {self.button_active}")
        time_now = time.time()

        if self.button_active:
            logging.debug("ignoring due to active button")
            return

        # wait until button is released
        while not GPIO.input(self.pin_button_left):
            time.sleep(0.1)
            # if button pressed longer than 5 sec -> shutdown
            if (time.time() - time_now) > 5:
                subprocess.call("sudo poweroff", shell=True)
                return

        # if in PowerOnState - ignore Buttons
        if self.state == "PowerOn":
            return

        # if in PrintPhoto State - ignore Buttons
        if self.state == "PrintPhoto":
            return

        # ignore buttons enqueued during processing
        # so there is a max. frequency of 1 buttonclick per second
        if (time_now - self.time_stamp_button) >= 1:
            self.button_active = True
            try:
                # from state start -> choose layout 1
                if self.state == "Start":
                    logging.debug("State == Start -> Set Photonumbers")
                    self.layout = 1

                logging.debug("self.button1 start")
                self.Button1()
            finally:
                logging.debug("self.button1 ready -> Set new TimeStamp")
                self.time_stamp_button = time.time()
                self.button_active = False
        else:
            logging.debug("ignoring button")        

    # Button2 callback function. Actions depends on state of the Photobooth state machine
    def Button2pressed(self, event):
        logging.debug(f"Button2pressed, active = {self.button_active}")
        time_now = time.time()

        if self.button_active:
            logging.debug("ignoring due to active button")
            return

        # wait until button is released
        while not GPIO.input(self.pin_button_right):
            time.sleep(0.1)
            # if button pressed longer than 5 sec -> shutdown
            if (time.time() - time_now) > 5:
                subprocess.call("sudo reboot", shell=True)
                return

        # if in PowerOnState - ignore Buttons
        if self.state == "PowerOn":
            return

        # if in PrintPhoto State - ignore Buttons
        if self.state == "PrintPhoto":
            return

        # ignore buttons enqueued during processing
        # so there is a max. frequency of 1 buttonclick per second
        if (time_now - self.time_stamp_button) >= 1:
            self.button_active = True
            try:
                # from state start -> choose layout 2
                if self.state == "Start":
                    logging.debug("State == Start -> Set Photonumbers")
                    self.layout = 2

                logging.debug("self.button2 start")
                self.Button2()
            finally:
                logging.debug("self.button2 ready -> Set new TimeStamp")
                self.time_stamp_button = time.time()
                self.button_active = False
        else:
            logging.debug("ignoring button")        

    # Power On Check State
    # check if printer is connected and turned on
    def on_enter_PowerOn(self):
        logging.debug("now on_enter_PowerOn")
        self.overlay_screen_blackbackground = self.overlay_image(self.screen_black, False, 0, 2)
        self.overlay_screen_turnOnPrinter = -1

        while True:
            r = subprocess.run("./camera_start.sh", capture_output=True)
            logging.debug("exec " + str(r.args))
            logging.debug("exit code " + str(r.returncode))
            logging.debug(str(r.stdout))
            logging.debug(str(r.stderr))
            if r.returncode == 0:
                break
            elif "connected:" in str(r.stdout) and "ERROR: already in rec" in str(r.stderr):
                break
            else:
                logging.debug("Camera not found")
                if self.overlay_screen_turnOnPrinter == -1:
                    self.overlay_screen_turnOnPrinter = self.overlay_image(self.screen_turnOnPrinter, True, 0, 3)
                time.sleep(2)

        if not self.CheckPrinter():
            logging.debug("no printer found")
            if self.overlay_screen_turnOnPrinter == -1:
                self.overlay_screen_turnOnPrinter = self.overlay_image(self.screen_turnOnPrinter, True, 0, 3)

            while not self.CheckPrinter():
                time.sleep(2)

        logging.debug("printer found")
        self.PrinterFound()

    # leave Power On Check State
    def on_exit_PowerOn(self):
        logging.debug("now on_exit_PowerOn")

        # remove overlay "turn on printer", if still on display
        self.remove_overlay(self.overlay_screen_turnOnPrinter)

    # Start State -> Show initail Screen
    def on_enter_Start(self):
        self.button_active = False
        
        self.remove_overlay(self.overlay_photo)
        self.overlay_photo = -1

        logging.debug("now on_enter_Start")
        self.startpreview()
        self.overlay_choose_layout = self.overlay_image(self.screen_choose_layout, True, 0, 7)

    # leave start screen
    def on_exit_Start(self):
        logging.debug("now on_exit_Start")
        # on start of every photosession, create an unique filename, containing date and time
        self.fileName = self.get_image_filename()
        self.fileNamePrint = self.fileName.replace(".jpg", "_print.jpg")
        self.fileNamePreview = self.fileName.replace(".jpg", "_preview.png")
        
        self.remove_overlay(self.overlay_choose_layout)

    # countdown to zero and take picture
    def on_enter_CountdownPhoto(self):
        logging.debug("now on_enter_CountdownPhoto")
        if self.layout == 2:
            self.overlay_frame = self.overlay_image(self.screen_frame, True, 0, 4)

        # print the countdown
        self.overlay_screen_Countdown = self.overlay_image(self.screen_countdown_3, True, 0, 7)
        time.sleep(1)
        self.remove_overlay(self.overlay_screen_Countdown)
        self.overlay_screen_Countdown = self.overlay_image(self.screen_countdown_2, True, 0, 7)
        time.sleep(1)
        self.remove_overlay(self.overlay_screen_Countdown)
        self.overlay_screen_Countdown = self.overlay_image(self.screen_countdown_1, True, 0, 7)
        time.sleep(1)
        self.remove_overlay(self.overlay_screen_Countdown)

        self.remove_overlay(self.overlay_frame)
        self.overlay_frame = -1

        # countdown finished
        self.CountdownPhotoTimeout()

    def on_exit_CountdownPhoto(self):
        logging.debug("now on_exit_CountdownPhoto")

    # take a pciture
    def on_enter_TakePhoto(self):
        logging.debug("now on_enter_TakePhoto")
        self.overlay_wait = self.overlay_image(self.screen_wait, True, 0, 7)

        r = subprocess.run(["./camera_shoot.sh", self.fileName], capture_output=True)
        logging.debug(r.args)
        logging.debug(r.returncode)
        logging.debug(r.stdout)
        logging.debug(r.stderr)

        self.to_ShowPhoto()

    def on_exit_TakePhoto(self):
        logging.debug("now on_exit_TakePhoto")


    # show the picture
    def on_enter_ShowPhoto(self):
        logging.debug("now on_enter_ShowPhoto")

        # log filename
        logging.debug(self.fileName)

        # copy photo to USB Drive
        if self.PhotoCopyPath is not None:
            logging.debug(str(self.PhotoCopyPath))
            logging.debug(os.path.basename(str(self.fileName)))
            logging.debug((str(self.PhotoCopyPath)) + '/' + os.path.basename(str(self.fileName)))
            shutil.copyfile((str(self.fileName)),
                            ((str(self.PhotoCopyPath)) + '/' + os.path.basename(str(self.fileName))))

        logging.debug("start processing")

        img = image(filename=self.fileName)
        img.rotate(90)
        s = img.size
        if self.layout == 1:
            logging.debug("layout na vysku")
            h = s[1]
            w = int(h / 1.48)
            logging.debug("crop w="+str(w)+" h="+str(h))
            img.crop(width=w, height=h, gravity='center')
        else:
            logging.debug("layout na sirku")
            w = s[0]
            h = int(w / 1.48)
            logging.debug("crop w="+str(w)+" h="+str(h))
            img.crop(width=w, height=h, gravity='north')

        img.save(filename=self.fileNamePrint)

        if self.layout == 1:
            h2 = self.screen_h
            w2 = int(h2 * w / h)
            if w2 % 2 == 1:
                w2 = w2 + 1
            borderSize = int((self.screen_w - w2) / 2)
            logging.debug("sample w="+str(w2)+" h="+str(h2)+" border="+str(borderSize))
            img.sample(w2, h2)
            img.border('black', borderSize, 0)
        else:
            w2 = self.screen_w
            h2 = int(w2 * h / w)
            if h2 % 2 == 1:
                h2 = h2 + 1
            borderSize = int((self.screen_h - h2) / 2)
            logging.debug("sample w="+str(w2)+" h="+str(h2)+" border="+str(borderSize))
            img.sample(w2, h2)
            img.border('black', 0, borderSize)

        img.save(filename=self.fileNamePreview)

        logging.debug("finish processing")
        self.remove_overlay(self.overlay_wait)
        self.overlay_wait = -1
                
        self.stoppreview()
        self.overlay_photo = self.overlay_image(self.fileNamePreview, False, 0, 6)
        self.overlay_screen_print = self.overlay_image(self.screen_print, True, 0, 7)

    # state show photo
    def on_exit_ShowPhoto(self):
        logging.debug("now on_exit_ShowPhoto")
        self.remove_overlay(self.overlay_screen_print)
        self.overlay_screen_print = -1

    # print the photocard
    def on_enter_PrintPhoto(self):
        logging.debug("now on_enter_PrintPhoto")

        self.overlay_wait = self.overlay_image(self.screen_printing, True, 0, 7)

        # print photo?
        if self.printPicsEnable == False:
            logging.debug("print enable = false")
        else:
            logging.debug("print enable = true")

            # connect to cups
            conn = cups.Connection()

            printers = list(conn.getPrinters().keys())
            printer = next((p for i, p in enumerate(printers) if "SELPHY" in p), None)

            logging.debug("Printer Name: " + printer)
            conn.enablePrinter(printer)
            conn.cancelAllJobs(printer, my_jobs=False, purge_jobs=True)

            # check printer state
            printerstate = conn.getPrinterAttributes(printer, requested_attributes=["printer-state-message"])
    
            # if printer in error state ->
            if str(printerstate).find("error:") > 0:
                logging.debug(str(printerstate))
                if str(printerstate).find("06") > 0:
                    logging.debug("goto refill ink")
                    self.InkEmpty()
                    return
                if str(printerstate).find("03") > 0:
                    logging.debug("goto refill paper")
                    self.PaperEmpty()
                    return
                if str(printerstate).find("02") > 0:
                    logging.debug("goto refill paper")
                    self.PaperEmpty()
                    return
                else:
                    logging.debug("Printer error: unknown: " + printerstate)
    
            # Send the picture to the printer
            conn.printFile(printer, self.fileNamePrint, "Photo Booth", {})
    
            # short wait
            time.sleep(5)
    
            stop = 0
            TIMEOUT = 60
    
            # Wait until the job finishes
            while stop < TIMEOUT:
                printerstate = conn.getPrinterAttributes(printer, requested_attributes=["printer-state-message"])
    
                if str(printerstate).find("error:") > 0:
                    logging.debug(str(printerstate))
                    if str(printerstate).find("06") > 0:
                        logging.debug("goto refill ink")
                        self.InkEmpty()
                        return
                    if str(printerstate).find("03") > 0:
                        logging.debug("goto refill paper")
                        self.PaperEmpty()
                        return
                    if str(printerstate).find("02") > 0:
                        logging.debug("goto refill paper")
                        self.PaperEmpty()
                        return
                    else:
                        logging.debug("Printer error: unknown: " + printerstate)
    
                if printerstate.get("printer-state-message") is "":
                    logging.debug("printer-state-message = /")
                    break
                stop += 1
                time.sleep(1)
    
        self.PrintDone()

    def on_exit_PrintPhoto(self):
        self.remove_overlay(self.overlay_wait)
        self.overlay_wait = -1
        logging.debug("now on_exit_PrintPhoto")

    # show refill paper instructions
    def on_enter_RefillPaper(self):
        logging.debug("now on_enter_RefillPaper")
        self.overlayscreen_refillpaper = self.overlay_image(self.screen_change_paper, False, 0, 8)

    def on_exit_RefillPaper(self):
        logging.debug("now on_exit_RefillPaper")
        self.remove_overlay(self.overlayscreen_refillpaper)

    # show refill ink instructions
    def on_enter_RefillInk(self):
        logging.debug("now on_enter_RefillInk")
        self.overlayscreen_refillink = self.overlay_image(self.screen_change_ink, False, 0, 8)

    def on_exit_RefillInk(self):
        logging.debug("now on_exit_RefillInk")
        self.remove_overlay(self.overlayscreen_refillink)

    # create filename based on date and time
    def get_image_filename(self):
        logging.debug("Get Image Name")
        # returns the filename base
        base_filename = self.photo_abs_file_path + str(datetime.now()).split('.')[0]
        base_filename = base_filename.replace(' ', '_')
        base_filename = base_filename.replace(':', '-')
        base_filename = base_filename + '.jpg'

        logging.debug(base_filename)
        return base_filename

    # remove screen overlay
    def remove_overlay(self, overlay_id):
        # If there is an overlay, remove it
        logging.debug("Remove Overlay")
        logging.debug(overlay_id)
        if overlay_id != -1:
            self.camera.remove_overlay(overlay_id)

    # overlay one image on screen
    def overlay_image(self, image_path, transparent=False, duration=0, layer=3):
        # Add an overlay (and time.sleep for an optional duration).
        # If time.sleep duration is not supplied, then overlay will need to be removed later.
        # This function returns an overlay id, which can be used to remove_overlay(id).

        if not os.path.exists(image_path):
            logging.debug("Overlay Image path not found: " + image_path)
            return -1

        logging.debug("Overlay Image: " + image_path)
        # Load the arbitrarily sized image
        img = Image.open(image_path)
        # Create an image padded to the required size
        pad = Image.new('RGBA' if transparent else 'RGB', (
            ((img.size[0] + 31) // 32) * 32,
            ((img.size[1] + 15) // 16) * 16,
        ))
        # Paste the original image into the padded one
        if transparent: 
            pad.paste(img, (0, 0), img)
        else: 
            pad.paste(img, (0, 0))

        # Add the overlay with the padded image as the source,
        # but the original image's dimensions
        try:
            o_id = self.camera.add_overlay(pad.tobytes(), size=img.size)
        except AttributeError:
            o_id = self.camera.add_overlay(pad.tostring(), size=img.size)  # Note: tostring() is deprecated in PIL v3.x

        o_id.layer = layer

        logging.debug("Overlay ID = " + str(o_id))

        del img
        del pad

        if duration > 0:
            time.sleep(duration)
            self.camera.remove_overlay(o_id)
            return -1  # '-1' indicates there is no overlay
        else:
            return o_id  # we have an overlay, and will need to remove it later

    # get the usb drive mount point
    def GetMountpoint(self):
        logging.debug("Get USB Drive Mount Point")
        try:
            context = pyudev.Context()
            removable = [device for device in context.list_devices(subsystem='block', DEVTYPE='disk') if
                         device.attributes.asstring('removable') == "1"]

            partitions = [removable[0].device_node for removable[0] in
                          context.list_devices(subsystem='block', DEVTYPE='partition', parent=removable[0])]
            for p in psutil.disk_partitions():
                if p.device in partitions:
                    logging.debug("Mountpoint = " + p.mountpoint)
                    return p.mountpoint

        except:
            logging.debug("No Drive Found")
            return None

    # check if the printer is connected and turned on
    def CheckPrinter(self):
        logging.debug("CheckPrinter")

        if self.printPicsEnable == False:
            logging.debug("printing disabled")
            return True

        busses = usb.busses()
        for bus in busses:
            devices = bus.devices
            for dev in devices:
                if dev.idVendor == 1193 and dev.idProduct == 13019:
                    logging.debug("Printer Found")
                    logging.debug("  idVendor: %d (0x%04x)" % (dev.idVendor, dev.idVendor))
                    logging.debug("  idProduct: %d (0x%04x)" % (dev.idProduct, dev.idProduct))
                    return True
        logging.debug("PrinterNotFound")
        return False
    
    def startpreview(self):
        logging.debug("Start Camera preview")
        self.camera.start_preview(fullscreen=False, window=(255,0,770,1024))

    def stoppreview(self):
        logging.debug("Stop Camera Preview")
        self.camera.stop_preview()

# Main Routine
def main():
    # start logging
    log_filename = str(datetime.now()).split('.')[0]
    log_filename = log_filename.replace(' ', '_')
    log_filename = log_filename.replace(':', '-')

    loggingfolder = REAL_PATH + "/Log/"

    if not os.path.exists(loggingfolder):
        os.mkdir(loggingfolder)

    file_handler = logging.FileHandler(filename=loggingfolder + log_filename + ".log")
    stdout_handler = logging.StreamHandler(sys.stdout)
    handlers = [file_handler, stdout_handler]

    # logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.DEBUG, filename=REAL_PATH+"/test.log")
    logging.basicConfig(format='%(asctime)s-%(module)s-%(funcName)s:%(lineno)d - %(message)s', level=logging.DEBUG,
                        handlers=handlers)
    logging.info("info message")
    logging.debug("debug message")

    while True:

        logging.debug("Starting Photobooth")

        photobooth = Photobooth()

        while True:
            time.sleep(0.1)
            pass


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        logging.debug("keyboard interrupt")

    except Exception as exception:
        logging.critical("unexpected error: " + str(exception))

    finally:
        logging.debug("logfile closed")

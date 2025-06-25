import logging
import serial
import threading
import binascii
import time

WAIT_DELAY = 2

_LOGGER = logging.getLogger(__name__)

class CentraliteThread(threading.Thread):

   def __init__(self, serial, notify_event):
      threading.Thread.__init__(self, name='CentraliteThread', daemon=True)
      self._serial = serial
      self._lastline = None
      self._recv_event = threading.Event()
      self._notify_event = notify_event

   def run(self):
   
      while True:
         line = self._readline()
         
         _LOGGER.debug('In While True, Incoming Line "%s"', line)
         
         # Capture notifications that are events and will launch handlers
         #    DEV is load levels, ACT is related to switch top/press/release
         if line[0:3]=='ACT' or line[0:3]=='DEV':
            # load levels/data that are part of the string, get parsed out in the notify event
            _LOGGER.info('  Matches ACT or DEV: %s"', line)
            self._notify_event(line)
            continue                     

         self._lastline = line
         self._recv_event.set()

   def _readline(self):
      _LOGGER.debug('      In While True, top of _readline')
      output = ''
      while True:
         # serial is a byte by byte thing, so we really don't know when to stop until we find the EOL chars
         byte = self._serial.read(size=1)
         
         #_LOGGER.debug('      In While True, readline byte "%s"', byte)                                  
         
         # jetstream is sending Carriage Return + New Line.         
         # if CRNL found, then it is the end of the command; this also removes the CR from the returned data therefore .strip() not needed
         if (byte[0] == 0x0d):  # CR, 2nd to last thing in command (we don't need this char)
            continue
         if (byte[0] == 0x0a):  # NL, last thing in command (we don't need this char)
            break
         output += byte.decode('utf-8')
      return output

   def get_response(self):
      self._recv_event.wait(timeout=WAIT_DELAY)
      self._recv_event.clear()
      return self._lastline

class Centralite:
   _LOGGER.debug('   In pycentralite.py jetstream start of class Centralite')
   # Original Coder loaded all lights/loads by default which is a lot of likely unused devices in HA with a bigger Centralite system.
   #    CW switched code to be a list or dictionary of items to load to slim down HA.    
   # It would be nice if these IDs were defined in YAML rather than in the code but I don't know how to do that at this point.
   
   
   # friendly_name defined in YAML;  add the loads/light IDs you want in HA
   # 
   LOADS_LIST = [ 1, 20, 25, 29, 30 ]
   #LOADS_LIST = [ 1 ]

   
   # HA scenes do not use a 'unique id' like the lights do. friendly_name does not work on scenes.  They only have a name which becomes
   #    the unique id and is used in the UI. We need to know the Centralite scene # and then HA GUI needs the name to be 
   #    something human readable/meaningful
   ACTIVE_SCENES_DICT = {
     '1': 'Scene 1 name',
     '2': 'Scene 2 name'
   }
      
   # friendly_name defined in YAML;  add the switch IDs you want in HA
        #!!! Switches in Jetstream are referenced as switch ID and then button ID on that switch. 
        # ACT01501T would be device 15 button 01 action Tapped
        # a switch can have up to 3 buttons (on my system)   
        # populate this list as switch device 1 button 1 = 101;  dev 15 button 3 = 1503; dev 80 button 2 = 802
        # (juggle zero padding this throughout as needed but not needed here which would require treating these as strings)
   SWITCHES_LIST = [ 101, 1401, 1402, 1403 ]
   
   _LOGGER.info('   In pycentralite.py jetstream startup "%s"', ACTIVE_SCENES_DICT)    

   def __init__(self, url):
      _LOGGER.info('Start serial setup init using %s', url)
      self._serial = serial.serial_for_url(url, baudrate=19200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE)
      self._events = {}
      self._thread = CentraliteThread(self._serial, self._notify_event)
      self._thread.start()
      self._command_lock = threading.Lock()

   def _send(self, command):
      with self._command_lock:
         _LOGGER.info('Send via _send "%s"', command)         
         self._serial.write(command.encode('utf-8'))         
         time.sleep(.1)  # for some reason going too fast can cause duplicate and lost data issues (might be specific to my usb->serial)
                         # this may be an issue with my adapter as I have not seen this with the elegance system with a different brand adapter,
                         # OR it could be a bug with the jetstream bridge (total guesses)
                         
                         # The exact issue: _send would send out requests for load level for 3 different lights but it would get 3 responses
                         # back for the LAST light it requested info about.  With this sleep, it gets 3 correct responses for all 3 lights.

         _LOGGER.info('   AFTER Send via _send "%s"', command)         
      return True

   #! Might stop using this. Jetstream seems to always respond and the read loop catches the response rather than this function. 
   def _sendrecv(self, command):
      with self._command_lock:
         _LOGGER.debug('Send via _sendrecv "%s"', command)
         #command = command + "\n"   #! not necessary
         self._serial.write(command.encode('utf-8'))
         time.sleep(.1)  # for some reason going too fast can cause duplicate and lost data issues (might be specific to my usb->serial)
                         # this may be an issue with my adapter as I have not seen this with the elegance system with a different brand adapter,
                         # OR it could be a bug with the jetstream bridge (total guesses)
                         
                         # The exact issue: _send would send out requests for load level for 3 different lights but it would get 3 responses
                         # back for the LAST light it requested info about.  With this sleep, it gets 3 correct responses for all 3 lights.

         # Testing note/code that's just here as a note.
         #_LOGGER.info('testing A002')
         # adding a .encode seems to break this, the b is necessary
         #blah = "^A001"
         #self._serial.write(blah.encode('utf-8'))
         # this works too
         #self._serial.write(b"Ping\r")
         
         #_LOGGER.debug('   about to get_response()')
         
         #result = self._thread.get_response()
         #result = self._readline()
         
         #_LOGGER.debug('   about to strip response, %s', result)
         #result = result.strip()  # remove leading/trailing whitespace/cr/lf
         #_LOGGER.debug('Recv "%s"', result)
         
         #return result
      return

   def _add_event(self, event_name, handler):
      _LOGGER.debug('IN _add_event, event_name is "%s"', event_name)
      event_name = event_name.strip()  # remove leading/trailing whitespace/cr/lf
      event_list = self._events.get(event_name, None)
      if event_list == None:
         event_list = []
         self._events[event_name] = event_list
      event_list.append(handler)

   def _notify_event(self, event_name):
      event_name = event_name.strip()  # remove leading/trailing whitespace/cr/lf
      
      _LOGGER.debug('Event "%s"', event_name)
      _LOGGER.debug('   Self is "%s"', self)      
      
      handler_params=""
      line = str(event_name)
      
      # LIGHTS pass in a load level;  DEVdddll
      if line[0:3]=='DEV': 
         load = event_name[3:6] # get ddd
         level = event_name[-2:]  # get ll, last two chars
         event_name = 'DEV' + load         
         _LOGGER.debug('    Updated Event name is: %s', event_name)
         _LOGGER.debug('    Load %s Level %s', load, level)
         handler_params=level         
      
      #! change to jetstream commands ACTdddbbT ACTdddbbP ACTdddbbR; T/P/R = Tap, Press, Release
      elif line[0:3]=='ACT':
         _LOGGER.debug('    Switch, command is %s', line)
         sw_device = event_name[3:6] # get ddd
         sw_dev_button = event_name[6:8] # get bb button number
         sw_dev_button_action = event_name[8:9]  # get T/P/R, last 1 char
         
         #! need to set event_name here and params??????
         pass  #not currently using this elif

      #! SCNsss1 = scene activated, SCNsss0 = scene deactivated
      elif line[0:3]=='SCN':
         _LOGGER.debug('    Scene, command is %s', line)
         scene_num = event_name[3:6] # get scene sss
         scene_action = event_name[6:7] # get one/off representated as 1 (on) 0 (off)
         
         #! need to set event_name here and params??????
         pass  #not currently using this elif            
         
      else:
         _LOGGER.debug('    UNKNOWN command is %s', line)
         pass
      
      # _events.get() calls some HA brains?  Hint: .get() pulls a key off of a dictionary.
      event_list = self._events.get(event_name, None)
      _LOGGER.debug('Event list %s', event_list)
      _LOGGER.debug('   handler_params is %s', handler_params)
      if event_list is not None:
         _LOGGER.debug('   Getting handler')
         for handler in event_list:            
            # There is a handler assigned to each device when it is instantiated (e.g. light is _on_load_changed, call it with the new light level)
            _LOGGER.debug('   Before calling handler funct %s ', handler)
            try:               
               handler(handler_params)
            except: #catch all exceptions
               error_msg = sys.exc_info()[0]
               _LOGGER.debug('   TRY failed for handler error_msg is %s ', error_msg)               
      else:
         _LOGGER.debug('   event_list is NONE, handler not run')
         pass
       
   def on_load_activated(self, index, handler):
      self._add_event('N{0:03d}'.format(index), handler)

   def on_load_deactivated(self, index, handler):
      self._add_event('F{0:03d}'.format(index), handler)

   def on_load_change(self, index, handler):
      #! on load change in action, it is DEV12345 but on setup it is DEV123???
      self._add_event('DEV{0:03}'.format(index), handler)

   def on_switch_pressed(self, index, handler):
      # This is called when switch.py adds all the switch devices.  When else could it run?  - cw
      _LOGGER.debug('IN on_switch_pressed, index is "%s"', index)
      _LOGGER.debug('   IN on_switch_pressed, handler is "%s"', handler)
      
      # NOTE! Centralite uses a 0 for a single board system here, format is P0 and then the 3 digit switch #
      # (using T for TAP here, not P for PRESSED, see jetstream docs))
      self._add_event('ACT{0:05d}T'.format(index), handler)

   def on_switch_released(self, index, handler):     
      _LOGGER.debug('IN on_switch_released, index is "%s"', index)
      _LOGGER.debug('   IN on_switch_released, handler is "%s"', handler)      
      self._add_event('ACT{0:05d}R'.format(index), handler)

   def activate_load(self, index):
      self._send('^A{0:03d}'.format(index))

   def deactivate_load(self, index):
      self._send('^B{0:03d}'.format(index))

   def activate_scene(self, index, scene_name):
      # HA can't do an on/off on a single scene, so each Centralite scene has two HA scenes (one for off, one for on)
      _LOGGER.debug('IN pycentralite.py activate_scene, index is "%s"', index)
      _LOGGER.debug('IN pycentralite.py activate_scene, scene_name is "%s"', scene_name)
      index=int(index)
      if "-ON" in scene_name.upper():
        self._send('^C{0:03d}'.format(index))
      elif "-OFF" in scene_name.upper():
        self._send('^D{0:03d}'.format(index))

   # unused, HA does not support OFF for a scene
   #def deactivate_scene(self, index):
   #   self._send('^D{0:03d}'.format(index))

   def activate_load_at(self, index, level, rate):
      self._send('^E{0:03d}{1:02d}{2:02d}'.format(index, level, rate))

   def get_load_level(self, index):
      _LOGGER.debug('   IN pycentralite.py get_load_level(), index is "%s"', index)
      _LOGGER.debug('     Will send this: %s', '^F{0:03d}'.format(index))
      #incoming_result = self._sendrecv('^F{0:03d}'.format(index))
      self._send('^F{0:03d}'.format(index))
      
      #_LOGGER.debug('     Received sendrecv this: %s', incoming_result)
      #incoming_result = incoming_result[-2:]  # get last 2 of string which is the load level
      #_LOGGER.debug('     LL is: %s', incoming_result)
      #return int(incoming_result)
      
      #! sending the ^Fxxx above is triggering an incoming update that is being processed already
      return True


   def press_switch(self, index):      
      # THIS IS NOT FULLY TESTED BUT IT DOES SEND THE COMMANDS but I didn't see any activity in real life from it      
      # I have no use case for it so I'm leaving code as is.
      
      # I'm not sure there's a need to send a button press from HA since loads/lights/scenes can be triggered/read directly.  
      # If you enable this, an immediate release button should be sent too?  (On elegance holding a button is dimming)
            
      # A button press without a release causes, dimming right?  Verify on Jetstream.
      
      # ^T is a tap, ^P is a press, ^R is a release;  my system is only programmed for Taps?
      
      #!!!!  Bug: This is causing brightness to get set to 1
      self._send('^T{0:05d}'.format(index))
      self._send('^R{0:05d}'.format(index))
      return

   def release_switch(self, index):
      _LOGGER.debug('   IN release_switch, index is "%s"', index)
      self._send('^R{0:05d}'.format(index))

   # friendly_name defined in YAML
   def get_switch_name(self, index):
      #return 'SW{0:03d}'.format(index)
      return 'JSSW{0:05d}'.format(index)

   # friendly_name defined in YAML
   def get_load_name(self, index):
      #return 'L{0:03d}'.format(index)
      _LOGGER.debug('   IN get_load_name, index is "%s"', index)
      return 'JSL{0:03d}'.format(index)

   # Called by __init__.py
   def loads(self):
      return (Centralite.LOADS_LIST)

   def update_ui_with_load_levels(self):
      _LOGGER.debug('   IN update ui ll long shot')
      for an_index in Centralite.LOADS_LIST:
         _LOGGER.debug('   IN for loop index is %s', an_index)
         #self.get_load_level(an_index)
         self._send('^F{0:03d}'.format(an_index))

   def button_switches(self):
      return(Centralite.SWITCHES_LIST)

   def scenes(self):
      return(Centralite.ACTIVE_SCENES_DICT)
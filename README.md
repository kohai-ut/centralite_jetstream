# centralite_jetstream
 Centralite Jetstream custom component for Home Assistant

My Centralite Jetstream system has an RS232 to Zigbee bridge/device sold by Centralite. I'm using a USB to serial adapter
to connect my Raspberry Pi 4 to the bridge/device.  

UPDATE: June 2025. I have added code to support for the HA unique_id attribute which is needed for voice assistant support in order to set an verbal alias on a device. 

How To (rough):

Someone asked for details on what to do with the code. I set this up directly in the home assistant directories and edited the yaml to make it work.
 
This is a bit of a rough version that never got fully polished. I can't remember if I ever tested the scenes code. I've contemplated trying out some AI to help finish it up as my python skills are minimal. It's been a long time since I set this up on my rpi with home assistant -- this is what I have going on mine.

1. I put the github files/repo under the home assistant folder: custom_components/centralite-jestream

NOTE: I then edited yaml files below to customize for my setup AND there are some edits to the python code. I do not enable ALL of my switches/loads/scenes. I only set up those I want to show up in HA.

2. Edit pycentralite.py to enter the lights/loads/switches/etc numbers in the right variables. The numbers to enter are the ones from the jetstream system config, see example below.  Look for LOADS_LIST, SWITCHES_LIST, ACTIVE_SCENES_DICT

3. Edit the homeassistant/configuration.yaml and add or merge this stuff in the right places in the yaml file:
```
# Centralite CR for third party integration must be turned on in the Elegance system/software 
centralite-jetstream:
  # using /dev/ttyUSB0 is not persistent between boots
  port: /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AR0K8WLF-if00-port0

# Logger debugging
logger:
  default: critical
  logs:
    # log level for all python scripts
    #homeassistant.components.python_script: warning
    # jetstream
    custom_components.centralite-jetstream: critical
    custom_components.centralite-jetstream.light: critical
    custom_components.centralite-jetstream.switch: critical
    custom_components.centralite-jetstream.scene: critical  

homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 192.168.1.0/24
    - type: homeassistant
  customize: !include centralite_desc.yaml
```




4. Ok, then create a file centralite_desc.yaml in the same directory as configuration.yaml (UPDATE June 2025: these can now be set in the HA web UI)
   
```
  light.jsl001:
    friendly_name: "Jetstream E BEDROOM"
  light.jsl020:
    friendly_name: "Jetstream W HALL N-1-SLAV"
  light.jsl025:
    friendly_name: "Jetstream APT FAM CANS"
  light.jsl029:
    friendly_name: "Jetstream APT KITCHEN N"
  light.jsl030:
    friendly_name: "Jetstream APT KITCHEN S"
  switch.jssw00101:
    friendly_name: "Blah Switch 001"
  switch.jssw01401:
    friendly_name: "Blah Switch 014 Btn 1"
```

In my file I have both jetstream and elegance systems so this is the snippet for my jetstream that I use in HA. The 001 in light.jsl001 is aligned with the jetstream system's ID for that light. I have a jetstream/zigbee style dongle to communicate and configure the jetstream system and see the configuration and save it to a text file for browsing. I assume people can figure out what the numbers should be. Also, the documentation for jestream is available online.

5. Restart HA and watch the log files.  You should be able to see logs showing up in the home-assistant.log file.


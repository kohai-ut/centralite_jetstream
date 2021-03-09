"""
Support for Centralite lights.

For more details about this platform, please refer to the documentation at

Checklist for creating a platform: https://developers.home-assistant.io/docs/creating_platform_code_review/
"""
import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, ENTITY_ID_FORMAT, LightEntity)

#from custom_components import centralite
#from custom_components.centralite import (
#    CENTRALITE_CONTROLLER, CENTRALITE_DEVICES, LJDevice)

# helpful HA guru raman325 on discord said to use this import approach
from . import (
    CENTRALITE_CONTROLLER, CENTRALITE_DEVICES, LJDevice)

    
_LOGGER = logging.getLogger(__name__)

_LOGGER.debug("In jetstream light.py, TOP")

DEPENDENCIES = ['centralite-jetstream']

ATTR_NUMBER = 'number'

# setup is called when HA is loading this component 
def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up lights for the Centralite platform."""
    centralite_ = hass.data[CENTRALITE_CONTROLLER]
    
    _LOGGER.debug("In light.py, hass data centralite devices %s", hass.data[CENTRALITE_DEVICES])
    
    # add_entities() is a home assistant function, if true it triggers an update (or async_update),
    #    if false it allows the state to be discovered later (thus state is inaccurate for a bit).
    # setting to true causes serial communication one by one for each light to pull its status. HA startup is paused until this loop completes.
    
    # archive: previous loop which was hard to debug, so I created a regular for loop
    #add_entities(
    #    [CentraliteLight(device,centralite_) for
    #     device in hass.data[CENTRALITE_DEVICES]['light']], True)    
    
    lights_to_add = []
    
    #loads_list = centralite_.loads()  # get a variable type LIST of loads
    for a_load in hass.data[CENTRALITE_DEVICES]['light']:
        _LOGGER.debug('      In FOR, i is "%s"', a_load)        
        lights_to_add.append(CentraliteLight(a_load,centralite_))
        
    add_entities(lights_to_add, True)  # IF set to true, required me to add .1 sleep to serial write, or it would fail! See other notes.

class CentraliteLight(LJDevice, LightEntity):
    """Representation of a single Centralite light."""
    
    def __init__(self, lj_device, controller):
        """Initialize a Centralite light."""
        _LOGGER.debug("init of the light for %s", lj_device)
        
        #self._brightness = None
        self._brightness = 0
        #self._state = None
        self._state = False
        self._name = controller.get_load_name(lj_device) 
        self._friendly_name = "Horse"
        _LOGGER.debug("    init of the light self._name is %s", self._name)
        super().__init__(lj_device, controller, self._name)
        
        LJDevice.__init__(self,lj_device,controller,self._name)

        # Set handler for this device
        controller.on_load_change(lj_device, self._on_load_changed)

        """
        # Jetstream system stores the human readable name of each device, we could ask it and set it here
        # rather than using the friendly_name in the yaml.  However, I don't know how to make this work. 'NAMxxx' for ask name of device
        
        #_LOGGER.debug("__init__ self_id is %s", self.lj_id)        
        #hass.states.set('self.lj_id', {'friendly_name': 'example name here'})
        """

    def _on_load_changed(self, _new_bright):
        """Handle state changes."""
        _LOGGER.debug("Updating due to notification for %s", self._name)
        _LOGGER.debug("   level is %s", _new_bright)
        _LOGGER.debug("   self.brightness is %s", self._brightness)        
        
        # In the __init__ above, the state is set but it doesn't seem to matter what happens here, it is still None regardless, I'm ignoring for now
        #_LOGGER.debug("   self._state BEFORE is %s", self._state)
        
        #!!! Should this be based on the 255 HA number or the brightness % of centralite?
        self._brightness = int(_new_bright)
                
        _LOGGER.debug("   NEW self.brightness is %s", self._brightness)               
                
        """ 
        Whenever you receive new state from your subscription, you can tell Home Assistant that an update is available by calling schedule_update_ha_state() or async callback async_schedule_update_ha_state(). Pass in the boolean True to the method if you want Home Assistant to call your update method (which causes a device query - cw) before writing the update to Home Assistant.
        """
        self.schedule_update_ha_state()
        #self.schedule_update_ha_state(True)

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def name(self):
        """Return the light's name."""
        return self._name

    @property
    def brightness(self):
        """Return the light's brightness."""
        return self._brightness

    @property
    def is_on(self):
        """Return if the light is on."""
        return self._brightness != 0

    @property
    def should_poll(self):
        """Return that lights do not require polling."""
        return False

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        return {
            ATTR_NUMBER: self.lj_device,
        }

    # HA function https://developers.home-assistant.io/docs/core/entity/light/
    def turn_on(self, **kwargs):
        """Turn on the light."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = int(kwargs[ATTR_BRIGHTNESS] / 255 * 99)
            self.controller.activate_load_at(self.lj_device, brightness, 1)
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            self.controller.activate_load(self.lj_device)
            self._brightness = 255
        self._state = True
        self.schedule_update_ha_state()


    # HA function https://developers.home-assistant.io/docs/core/entity/light/
    def turn_off(self, **kwargs):
        """Turn off the light."""
        self.controller.deactivate_load(self.lj_device)
        self._state = False
        self._brightness = 0
        self.schedule_update_ha_state()


    def update(self):
        """Retrieve the light's brightness from the Centralite system."""
        _LOGGER.debug("In light.py update() what is self %s", self)
        _LOGGER.debug("    In light.py update() lj_device %s", self.lj_device)
        #!!!! this is likely wrong as get_load_level is not returning a value
        #self._brightness = self.controller.get_load_level(self.lj_device) / 99 * 255
        #self.controller._send('^F{0:03d}'.format(self.lj_device))
        self.controller.get_load_level(self.lj_device)
        return True

    def update_ha_from_controller(self, _bin_string):
        # THIS DOESN'T DO ANYTHING YET - cw
        # Process binary string bit-by-bit, start at 1 to use as light id below
        i = 1 
        while i < len(_bin_string)+1:
            if _bin_string[i-1] > 0:
                _light_id = str(i).zfill(3)  # zero pad for centralight id
                #self._state = ????
            
            i = i + 1      

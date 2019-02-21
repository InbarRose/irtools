# Standard Imports
import ctypes
import string
import time

# irtools Imports
from irtools import *

# External Imports

log = logging.getLogger('irtools.kits.virtual_interface')

# convenience
user32 = ctypes.windll.user32


# Thanks to GameMaster's post here https://stackoverflow.com/a/54729193/1561176
# for inspiring me to write a proper VirtualInterface kit.

class VirtualInterfaceError(Exception):
    pass


class UnknownKeyOrButtonError(VirtualInterfaceError):
    pass


class UnknownKeyError(UnknownKeyOrButtonError):
    pass


class UnknownButtonError(UnknownKeyOrButtonError):
    pass


class KeyboardKey(object):
    cancel = 0x03
    backspace = 0x08
    tab = 0x09
    enter = 0x0D
    shift = 0x10
    ctrl = 0x11
    alt = 0x12
    capslock = 0x14
    esc = 0x1B
    space = 0x20
    pgup = 0x21
    pgdown = 0x22
    end = 0x23
    home = 0x24
    leftarrow = 0x26
    uparrow = 0x26
    rightarrow = 0x27
    downarrow = 0x28
    select = 0x29
    print_btn = 0x2A
    execute = 0x2B
    printscreen = 0x2C
    insert = 0x2D
    delete = 0x2E
    help = 0x2F
    num0 = 0x30
    num1 = 0x31
    num2 = 0x32
    num3 = 0x33
    num4 = 0x34
    num5 = 0x35
    num6 = 0x36
    num7 = 0x37
    num8 = 0x38
    num9 = 0x39
    a = 0x41
    b = 0x42
    c = 0x43
    d = 0x44
    e = 0x45
    f = 0x46
    g = 0x47
    h = 0x48
    i = 0x49
    j = 0x4A
    k = 0x4B
    l = 0x4C
    m = 0x4D
    n = 0x4E
    o = 0x4F
    p = 0x50
    q = 0x51
    r = 0x52
    s = 0x53
    t = 0x54
    u = 0x55
    v = 0x56
    w = 0x57
    x = 0x58
    y = 0x59
    z = 0x5A
    leftwin = 0x5B
    rightwin = 0x5C
    apps = 0x5D
    sleep = 0x5F
    numpad0 = 0x60
    numpad1 = 0x61
    numpad3 = 0x63
    numpad4 = 0x64
    numpad5 = 0x65
    numpad6 = 0x66
    numpad7 = 0x67
    numpad8 = 0x68
    numpad9 = 0x69
    multiply = 0x6A
    add = 0x6B
    seperator = 0x6C
    subtract = 0x6D
    decimal = 0x6E
    divide = 0x6F
    F1 = 0x70
    F2 = 0x71
    F3 = 0x72
    F4 = 0x73
    F5 = 0x74
    F6 = 0x75
    F7 = 0x76
    F8 = 0x77
    F9 = 0x78
    F10 = 0x79
    F11 = 0x7A
    F12 = 0x7B
    F13 = 0x7C
    F14 = 0x7D
    F15 = 0x7E
    F16 = 0x7F
    F17 = 0x80
    F19 = 0x82
    F20 = 0x83
    F21 = 0x84
    F22 = 0x85
    F23 = 0x86
    F24 = 0x87
    numlock = 0x90
    scrolllock = 0x91
    leftshift = 0xA0
    rightshift = 0xA1
    leftctrl = 0xA2
    rightctrl = 0xA3
    leftmenu = 0xA4
    rightmenu = 0xA5
    browserback = 0xA6
    browserforward = 0xA7
    browserrefresh = 0xA8
    browserstop = 0xA9
    browserfavories = 0xAB
    browserhome = 0xAC
    volumemute = 0xAD
    volumedown = 0xAE
    volumeup = 0xAF
    nexttrack = 0xB0
    prevoustrack = 0xB1
    stopmedia = 0xB2
    playpause = 0xB3
    launchmail = 0xB4
    selectmedia = 0xB5
    launchapp1 = 0xB6
    launchapp2 = 0xB7
    semicolon = 0xBA
    equals = 0xBB
    comma = 0xBC
    dash = 0xBD
    period = 0xBE
    forwardslash = 0xBF
    accent = 0xC0
    openingsquarebracket = 0xDB
    backslash = 0xDC
    closingsquarebracket = 0xDD
    quote = 0xDE
    play = 0xFA
    zoom = 0xFB
    PA1 = 0xFD
    clear = 0xFE


class MouseButton(object):
    left = 0
    right = 1
    middle = 2


class VirtualInterface(object):
    # press/release time delay_press
    delay_hold = 0.01
    delay_release = 0.01

    @classmethod
    def _delay_hold(cls, delay_hold=None):
        delay = delay_hold or cls.delay_hold
        time.sleep(delay)

    @classmethod
    def _delay_release(cls, delay_release=None):
        delay = delay_release or cls.delay_release
        time.sleep(delay)


class VirtualKeyboard(VirtualInterface):

    @classmethod
    def hold_key(cls, key, **kwargs):
        """Presses key"""
        user32.keybd_event(key, 0, 0, 0)
        cls._delay_hold(**kwargs)

    @classmethod
    def release_key(cls, key, **kwargs):
        """Releases key"""
        user32.keybd_event(key, 0, 2, 0)
        cls._delay_release(**kwargs)

    @classmethod
    def press_key(cls, key, **kwargs):
        """Presses and releases the key"""
        cls.hold_key(key, **kwargs)
        cls.release_key(key, **kwargs)

    @classmethod
    def shift_press_key(cls, key, **kwargs):
        """Presses a key while shift is held down"""
        cls.hold_key(KeyboardKey.shift, **kwargs)
        cls.press_key(key, **kwargs)
        cls.release_key(KeyboardKey.shift, **kwargs)

    @classmethod
    def type_character(cls, character, **kwargs):
        """type the character using the virtual keyboard"""
        use_shift = KeyboardCharacters.character_requires_shift(character)
        key_to_press = KeyboardCharacters.character_to_key_name(character)
        if use_shift:
            cls.shift_press_key(key_to_press, **kwargs)
        else:
            cls.press_key(key_to_press, **kwargs)

    @classmethod
    def type_sequence(cls, sequence, **kwargs):
        """type out a sequence of characters using the virtual keyboard"""
        for character in sequence:
            cls.type_character(character, **kwargs)


class VirtualMouse(VirtualInterface):

    @classmethod
    def set_mouse_to_position(cls, x, y):
        user32.SetCursorPos(x, y)

    @classmethod
    def click_left_button(cls, **kwargs):
        cls.hold_left_button(**kwargs)
        cls.release_left_button(**kwargs)

    @classmethod
    def click_right_button(cls, **kwargs):
        cls.hold_right_button(**kwargs)
        cls.release_right_button(**kwargs)

    @classmethod
    def click_middle_button(cls, **kwargs):
        cls.hold_middle_button(**kwargs)
        cls.release_middle_button(**kwargs)

    @classmethod
    def hold_left_button(cls, **kwargs):
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        cls._delay_hold(**kwargs)

    @classmethod
    def hold_right_button(cls, **kwargs):
        user32.mouse_event(0x0008, 0, 0, 0, 0)
        cls._delay_hold(**kwargs)

    @classmethod
    def hold_middle_button(cls, **kwargs):
        user32.mouse_event(0x00020, 0, 0, 0, 0)
        cls._delay_hold(**kwargs)

    @classmethod
    def release_left_button(cls, **kwargs):
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        cls._delay_release(**kwargs)

    @classmethod
    def release_right_button(cls, **kwargs):
        user32.mouse_event(0x00010, 0, 0, 0, 0)
        cls._delay_release(**kwargs)

    @classmethod
    def release_middle_button(cls, **kwargs):
        user32.mouse_event(0x00040, 0, 0, 0, 0)
        cls._delay_release(**kwargs)

    @classmethod
    def click_mouse_button(cls, button, **kwargs):
        if button == MouseButton.left:
            cls.click_left_button(**kwargs)
        elif button == MouseButton.right:
            cls.click_right_button(**kwargs)
        elif button == MouseButton.middle:
            cls.click_middle_button(**kwargs)
        else:
            raise UnknownButtonError(button)

    @classmethod
    def hold_mouse_button(cls, button, **kwargs):
        if button == 0:
            cls.hold_left_button(**kwargs)
        elif button == 1:
            cls.hold_right_button(**kwargs)
        elif button == 2:
            cls.hold_middle_button(**kwargs)
        else:
            raise UnknownButtonError(button)

    @classmethod
    def release_mouse_button(cls, button, **kwargs):
        if button == 0:
            cls.release_left_button(**kwargs)
        elif button == 1:
            cls.release_right_button(**kwargs)
        elif button == 2:
            cls.release_middle_button(**kwargs)
        else:
            raise UnknownButtonError(button)


class KeyboardCharacters(object):
    lowercase_letters = string.ascii_lowercase
    uppercase_letters = string.ascii_uppercase
    characters_that_are_letters = lowercase_letters + uppercase_letters
    shift_map_letter_characters = dict(zip(lowercase_letters, uppercase_letters))
    shift_map_numbers = {
        '1': '!',
        '2': '@',
        '3': '#',
        '4': '$',
        '5': '%',
        '6': '^',
        '7': '&',
        '8': '*',
        '9': '(',
        '0': ')',
    }
    characters_that_are_numbers = shift_map_numbers.keys() + shift_map_numbers.values()
    shift_map_punctuation_characters = {
        '`': '~',   # accent
        '-': '_',   # dash
        '=': '+',   # equals
        '[': '{',   # openingsquarebracket
        ']': '}',   # closingsquarebracket
        ';': ':',   # semicolon
        "'": '"',   # quote
        '\\': '|',  # backslash
        ',': '<',   # comma
        '.': '>',   # period
        '/': '?',   # forwardslash
    }
    characters_that_are_punctuation = shift_map_punctuation_characters.keys() + \
                                      shift_map_punctuation_characters.values()
    characters_requiring_shift = shift_map_letter_characters.values() + \
                                 shift_map_numbers.values() + \
                                 shift_map_punctuation_characters.values()
    characters_that_are_whitespace = string.whitespace
    # map to key names for special characters
    map_key_to_punctuation_characters = {
        KeyboardKey.accent: ['`', '~'],
        KeyboardKey.dash: ['-', '_'],
        KeyboardKey.equals: ['=', '+'],

        KeyboardKey.openingsquarebracket: ['[', '{'],
        KeyboardKey.closingsquarebracket: [']', '}'],

        KeyboardKey.semicolon: [';', ':'],
        KeyboardKey.quote: ["'", '"'],
        KeyboardKey.backslash: ['\\', '|'],

        KeyboardKey.comma: [',', '<'],
        KeyboardKey.period: ['.', '>'],
        KeyboardKey.forwardslash: ['/', '?'],

    }
    map_key_to_whitespace_characters = {
        KeyboardKey.space: [' '],
        KeyboardKey.tab: ['\t'],
        KeyboardKey.enter: ['\n'],
    }
    map_key_to_number_characters = {
        KeyboardKey.num1: ['1', '!'],
        KeyboardKey.num2: ['2', '@'],
        KeyboardKey.num3: ['3', '#'],
        KeyboardKey.num4: ['4', '$'],
        KeyboardKey.num5: ['5', '%'],
        KeyboardKey.num6: ['6', '^'],
        KeyboardKey.num7: ['7', '&'],
        KeyboardKey.num8: ['8', '*'],
        KeyboardKey.num9: ['9', '('],
        KeyboardKey.num0: ['0', ')'],
    }

    @classmethod
    def character_to_key_name(cls, character):
        """get the key_name of the keyboard button that maps to this character"""
        assert character in string.printable
        if character in cls.characters_that_are_letters:
            key_name = character.lower()
            return cls.get_key(key_name)
        elif character in cls.characters_that_are_numbers:
            for key, numbers in cls.map_key_to_number_characters.items():
                if character in numbers:
                    return key
        elif character in cls.characters_that_are_punctuation:
            for key, punctuations in cls.map_key_to_punctuation_characters.items():
                if character in punctuations:
                    return key
        elif character in cls.characters_that_are_whitespace:
            for key, whitespace in cls.map_key_to_whitespace_characters.items():
                if character in whitespace:
                    return key
        raise UnknownKeyError(character)

    @classmethod
    def character_requires_shift(cls, character):
        return bool(character in cls.characters_requiring_shift)

    @classmethod
    def get_key(cls, key_name):
        return getattr(KeyboardKey, key_name)

#
# TM1637.py
#
#   python library for driving TM1637 based led displays
#   John Clark, 2018
#
#   resources:
#     https://os.mbed.com/components/TM1637-LED-controller-48-LEDs-max-Keyboa
#     https://sourceforge.net/projects/raspberry-gpio-python
#
#     requires gpio permissions: sudo adduser <userid> gpio
#
#
#    MIT License
#
#    Copyright (c) 2018 John Clark
#
#    Permission is hereby granted, free of charge, to any person obtaining a copy
#    of this software and associated documentation files (the "Software"), to deal
#    in the Software without restriction, including without limitation the rights
#    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#    copies of the Software, and to permit persons to whom the Software is
#    furnished to do so, subject to the following conditions:
#
#    The above copyright notice and this permission notice shall be included in all
#    copies or substantial portions of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#    SOFTWARE.
#


import RPi.GPIO as gpio


class TM1637(object):
    #
    #      a
    #     ---
    #  f |   | b
    #     -g-
    #  e |   | c
    #     --- x
    #      d
    #
    HEX_SEG_MAP = [
        # xgfedcba
        0b00111111,  # 0
        0b00000110,  # 1
        0b01011011,  # 2
        0b01001111,  # 3
        0b01100110,  # 4
        0b01101101,  # 5
        0b01111101,  # 6
        0b00000111,  # 7
        0b01111111,  # 8
        0b01101111,  # 9
        0b01110111,  # A
        0b01111100,  # b
        0b00111001,  # C
        0b01011110,  # d
        0b01111001,  # E
        0b01110001   # F
    ]
    SEG_POINT = 0b10000000  # .

    # commmands
    CMD_DATA      = 0x40
    CMD_DISPLAY   = 0x80
    CMD_ADDRESS   = 0xC0
    # flags
    DATA_INC_ADDR = 0x00
    DATA_FIX_ADDR = 0x04
    DISPLAY_OFF   = 0x00
    DISPLAY_ON    = 0x08


    def __init__(self, gpio_clk, gpio_dio, brightness=4):
        self.gpio_clk = gpio_clk
        self.gpio_dio = gpio_dio

        gpio.setmode(gpio.BCM)
        gpio.setup(self.gpio_clk, gpio.OUT, initial=gpio.HIGH)
        gpio.setup(self.gpio_dio, gpio.OUT, initial=gpio.HIGH)

        self.clear()
        self.brightness = brightness

    def __del__(self):
        gpio.cleanup()

    def write_byte(self, val):
        # lsb -> msb
        for i in range(8):
            b = (val >> i) & 0x01
            gpio.output(self.gpio_dio, b)
            self.delay()
            gpio.output(self.gpio_clk, gpio.HIGH)
            self.delay()
            gpio.output(self.gpio_clk, gpio.LOW)
            self.delay()

        # read ack
        gpio.setup(self.gpio_dio, gpio.IN, gpio.PUD_UP)
        self.delay()
        gpio.output(self.gpio_clk, gpio.HIGH)
        self.delay()

        for i in range(1, 1025):
            if gpio.input(self.gpio_dio) == gpio.LOW:
                break
            if i % 128 == 0:
                gpio.setup(self.gpio_dio, gpio.OUT, gpio.PUD_OFF, initial=gpio.LOW)
                self.delay()
                gpio.setup(self.gpio_dio, gpio.IN, gpio.PUD_UP)
                self.delay()

        gpio.output(self.gpio_clk, gpio.LOW)
        self.delay()
        gpio.setup(self.gpio_dio, gpio.OUT, gpio.PUD_OFF, initial=gpio.LOW)
        self.delay()

    def set_char(self, pos, segs):
        self.start();
        self.write_byte(self.CMD_DATA | self.DATA_FIX_ADDR);
        self.stop();

        self.start();
        self.write_byte(self.CMD_ADDRESS | (pos & 0x07));
        self.write_byte(segs);
        self.stop();

    def set_chars(self, segs_list, start=0):
        self.start();
        self.write_byte(self.CMD_DATA | self.DATA_INC_ADDR);
        self.stop();

        self.start();
        self.write_byte(self.CMD_ADDRESS | (start & 0x07));
        for segs in segs_list:
            self.write_byte(segs);
        self.stop();

    def set_string(self, str):
        segs_list = []

        rstr = reversed(str)
        for ch in rstr:
            pt = (ch == '.')
            if pt:
                ch = next(rstr)
            segs = 0
            if ch != ' ':
                dg = int(ch, 16)
                segs = self.HEX_SEG_MAP[dg]
            if pt:
                segs |= self.SEG_POINT
            segs_list.insert(0, segs)

        self.set_chars(segs_list, 4-len(segs_list))

    # display 0-8: 0=off, 8=brightest
    @property
    def brightness(self):
        return self._brightness
    @brightness.setter
    def brightness(self, val):
        self._brightness = min(8, max(0, val))
        self.start();
        if self._brightness == 0:
            self.write_byte(self.CMD_DISPLAY | self.DISPLAY_OFF);
        else:
            self.write_byte(self.CMD_DISPLAY | self.DISPLAY_ON | (self._brightness-1));
        self.stop();

    def clear(self):
        self.set_chars([0,0,0,0]) # 4 char display

    def start(self):
        # high->low clock while dio low
        gpio.output(self.gpio_clk, gpio.HIGH)
        self.delay()
        gpio.output(self.gpio_dio, gpio.LOW)
        self.delay()
        gpio.output(self.gpio_clk, gpio.LOW)
        self.delay()

    def stop(self):
        # low->high dio while clock high
        gpio.output(self.gpio_dio, gpio.LOW)
        self.delay()
        gpio.output(self.gpio_clk, gpio.HIGH)
        self.delay()
        gpio.output(self.gpio_dio, gpio.HIGH)
        self.delay()

    def delay(self):
        pass


def main():
    # demo hex counter
    disp = TM1637(gpio_clk=17, gpio_dio=18)
    from itertools import cycle
    for num in cycle(range(0x10000)):
        if num % 2 == 0:  # alternate
            disp.set_string('{:x}'.format(num))
        else:
            disp.set_char(0, disp.HEX_SEG_MAP[(num >> 12) & 0x0f])
            disp.set_char(1, disp.HEX_SEG_MAP[(num >>  8) & 0x0f])
            disp.set_char(2, disp.HEX_SEG_MAP[(num >>  4) & 0x0f])
            disp.set_char(3, disp.HEX_SEG_MAP[num & 0x0f])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(' break')
        pass


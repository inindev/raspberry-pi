#
# HD44780.py
#
#   python library for driving HD44780 based i2c displays
#   John Clark, 2018
#
#   resources:
#     https://www.sparkfun.com/datasheets/LCD/HD44780.pdf
#
#     sudo apt-get update
#     sudo apt-get install -y python-smbus i2c-tools
#     sudo i2cdetect -y 0
#     sudo i2cdetect -y 1
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

from time import sleep
import smbus

Left = False
Right = True


class HD44780(object):
    # commands (p.24-27)
    CLEAR_DISPLAY      = 0x01
    RETURN_HOME        = 0x02
    ENTRY_MODE_SET     = 0x04
    DISPLAY_SET        = 0x08
    CURSOR_SHIFT       = 0x10
    FUNCTION_SET       = 0x20
    CGRAM_ADDR_SET     = 0x40
    DDRAM_ADDR_SET     = 0x80
    # entry mode flags
    ENTRY_MODE_DEC     = 0x00
    ENTRY_MODE_INC     = 0x01
    ENTRY_MODE_SHRIGHT = 0x00
    ENTRY_MODE_SHLEFT  = 0x02
    # display flags
    DISPLAY_BLINK_OFF  = 0x00
    DISPLAY_BLINK_ON   = 0x01
    DISPLAY_CURSOR_OFF = 0x00
    DISPLAY_CURSOR_ON  = 0x02
    DISPLAY_OFF        = 0x00
    DISPLAY_ON         = 0x04
    # cursor shift flags
    DC_MOVE_LEFT       = 0x00
    DC_MOVE_RIGHT      = 0x04
    DC_CURSOR_MOVE     = 0x00
    DC_DISPLAY_MOVE    = 0x08
    # function set flags
    FUNCTION_5X8       = 0x00
    FUNCTION_5X10      = 0x04
    FUNCTION_1LINE     = 0x00
    FUNCTION_2LINE     = 0x08
    FUNCTION_4BIT      = 0x00
    FUNCTION_8BIT      = 0x10
    # i2c 8bit register layout
    # D7 | D6 | D5 | D4 | BL | EN | RW | RS
    REG_RS = 0b00000001  # register select bit
    REG_RW = 0b00000010  # read/write bit
    REG_EN = 0b00000100  # enable bit
    REG_BL = 0b00001000  # backlight bit
    REG_D4 = 0b00010000  # 4bit D4 lsb
    REG_D5 = 0b00100000  # 4bit D5
    REG_D6 = 0b01000000  # 4bit D6
    REG_D7 = 0b10000000  # 4bit D7 msb


    # run "sudo i2cdetect -y 1" to find i2c address of display
    def __init__(self, rows=2, cols=16, addr=0x3f, bus=1):
        self.rows = 1 if rows==1 else 2
        self.cols = cols
        self.addr = addr
        self.i2c = smbus.SMBus(bus)
        self.backlight = True
        self._display = 0
        self._entry_mode = 0

        # init to 4 bit mode (p.46)
        self.write_reg(self.REG_D5 | self.REG_D4)
        sleep(0.0045)   # wait >4.1ms (p.46)
        self.write_reg(self.REG_D5 | self.REG_D4)
        sleep(0.00011)  # wait >100us (p.46)
        self.write_reg(self.REG_D5 | self.REG_D4)
        self.write_reg(self.REG_D5)

        # 4-bit mode, font, rows
        self.write_cmd(self.FUNCTION_SET | self.FUNCTION_4BIT | self.FUNCTION_5X8
                                         | self.FUNCTION_1LINE if rows==1 else self.FUNCTION_2LINE)

        # display / cursor / blink
        self._display = self.DISPLAY_ON | self.DISPLAY_CURSOR_OFF | self.DISPLAY_BLINK_OFF
        self.write_cmd(self.DISPLAY_SET | self._display)

        # clear display
        self.write_cmd(self.CLEAR_DISPLAY)
        sleep(0.00167)  # wait >1.52ms (p.24)

        # text direction & scroll
        self._entry_mode = self.ENTRY_MODE_SHLEFT | self.ENTRY_MODE_DEC
        self.write_cmd(self.ENTRY_MODE_SET | self._entry_mode)

    def write_reg(self, reg):
        self.i2c.write_byte(self.addr, reg |  self.REG_EN)  # EN high
        sleep(0.000001)  # enable time >450ns (p.49)
        self.i2c.write_byte(self.addr, reg & ~self.REG_EN)  # EN low
        sleep(0.000044)  # command settle time >40us (p.25)

    def write_cmd(self, val, flags=0):
        flags |= self.REG_BL if self.backlight else 0
        self.write_reg(val & 0xF0 | flags)
        self.write_reg(val << 4 | flags)

    def write_char(self, val):
        self.write_cmd(val, self.REG_RS)

    def write_text(self, val):
        for c in val:
            self.write_char(ord(c))

    def set_cursor(self, row, col):
        pos = 0x40 * row + col
        if row > 1:
            pos -= (0x80 - self.cols)
        self.write_cmd(self.DDRAM_ADDR_SET | pos)

    def clear():
        self.write_cmd(self.CLEAR_DISPLAY)
        sleep(0.00167)  # wait >1.52ms (p.24)

    def home():
        self.write_cmd(self.RETURN_HOME)
        sleep(0.00167)  # wait >1.52ms (p.24)

    # backlight - note that backlight is a first-class property

    @property
    def display(self):
        return self.DISPLAY_ON == (self._display & self.DISPLAY_ON)
    @display.setter
    def display(self, val):
        if val:
            self._display |= self.DISPLAY_ON
        else:
            self._display &= ~self.DISPLAY_ON
        self.write_cmd(self.DISPLAY_SET | self._display)

    @property
    def cursor(self):
        return self.DISPLAY_CURSOR_ON == (self._display & self.DISPLAY_CURSOR_ON)
    @cursor.setter
    def cursor(self, val):
        if val:
            self._display |= self.DISPLAY_CURSOR_ON
        else:
            self._display &= ~self.DISPLAY_CURSOR_ON
        self.write_cmd(self.DISPLAY_SET | self._display)

    @property
    def cursor_blink(self):
        return self.DISPLAY_BLINK_ON == (self._display & self.DISPLAY_BLINK_ON)
    @cursor_blink.setter
    def cursor_blink(self, val):
        if val:
            self._display |= self.DISPLAY_BLINK_ON
        else:
            self._display &= ~self.DISPLAY_BLINK_ON
        self.write_cmd(self.DISPLAY_SET | self._display)

    @property
    def scroll_lock(self):
        return self.ENTRY_MODE_INC == (self._entry_mode & self.ENTRY_MODE_INC)
    @scroll_lock.setter
    def scroll_lock(self, val):
        if val:
            self._entry_mode |= self.ENTRY_MODE_INC
        else:
            self._entry_mode &= ~self.ENTRY_MODE_INC
        self.write_cmd(self.ENTRY_MODE_SET | self._entry_mode)

    @property
    def left_to_right(self):
        return self.ENTRY_MODE_SHLEFT == (self._entry_mode & self.ENTRY_MODE_SHLEFT)
    @left_to_right.setter
    def left_to_right(self, val):
        if val:
            self._entry_mode |= self.ENTRY_MODE_SHLEFT
        else:
            self._entry_mode &= ~self.ENTRY_MODE_SHLEFT
        self.write_cmd(self.ENTRY_MODE_SET | self._entry_mode)

    @property
    def right_to_left(self):
        return not self.left_to_right
    @right_to_left.setter
    def right_to_left(self, val):
        self.left_to_right = not val

    def scroll_cursor(self, cols=1, dir=Right):
        for col in range(cols):
            self.write_cmd(self.CURSOR_SHIFT | self.DC_CURSOR_MOVE | self.DC_MOVE_RIGHT if dir else self.DC_MOVE_LEFT)

    def scroll_display(self, cols=1, dir=Right):
        for col in range(cols):
            self.write_cmd(self.CURSOR_SHIFT | self.DC_DISPLAY_MOVE | self.DC_MOVE_RIGHT if dir else self.DC_MOVE_LEFT)


def main():
#    lcd = HD44780(rows=2, cols=16, addr=0x27)
    lcd = HD44780(rows=4, cols=20, addr=0x3f)
    lcd.set_cursor(3, 2)
    lcd.write_text('HD44780 is cool!')

    from datetime import datetime
    from pytz import timezone
    while True:
        utc = datetime.utcnow().replace(tzinfo=timezone('UTC'))
        local = utc.astimezone(timezone('US/Eastern'))
        ts = local.strftime('%m/%d/%y %I:%M %p')

        lcd.set_cursor(0, 1)
        lcd.write_text(ts)

        sleep(60 - utc.second)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(' break')
        pass


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

from time import sleep
import smbus


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
        self.write_cmd(self.DISPLAY_SET | self.DISPLAY_ON | self.DISPLAY_CURSOR_OFF | self.DISPLAY_BLINK_OFF)

        # clear display
        self.write_cmd(self.CLEAR_DISPLAY)
        sleep(0.00167)  # wait >1.52ms (p.24)

        # text direction & scroll
        self.write_cmd(self.ENTRY_MODE_SET | self.ENTRY_MODE_SHLEFT | self.ENTRY_MODE_DEC)

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


def main():
#    lcd = HD44780(rows=2, cols=16, addr=0x27)
    lcd = HD44780(rows=4, cols=20, addr=0x3f)
    lcd.set_cursor(3, 0)
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
        pass


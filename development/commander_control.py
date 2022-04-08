'''
Control of the Axoclamp 900A commander panel.
'''
import pyautogui as auto

capa_check = (18, 270)
capa_value = (215, 268)
offset_lock = (294, 228)
offset_zero = (316, 233)

class AxoclampController(object):
    def __init__(self):
        self.window = auto.getWindowsWithTitle('Axoclamp')[0]

    def shift(self, xy):
        return (xy[0] + self.window.left, xy[0] + self.window.top)

    def is_capaneut_on(self):
        return sum(auto.pixel(*self.shift(capa_check)))==0

    def is_offset_locked(self):
        return sum(auto.pixel(*self.shift(offset_lock)))>0

    def set_capneut(self, C):
        x, y = auto.position()
        auto.doubleClick(*self.shift(capa_value))
        auto.typewrite(str(C)+'\n')
        if not self.is_capaneut_on():
            auto.click(*self.shift(capa_check))
        auto.moveTo((x,y))

    def offset_zero(self):
        x, y = auto.position()
        if self.is_offset_locked():
            auto.click(*self.shift(offset_lock))
        auto.click(*self.shift(offset_zero))
        if not self.is_offset_locked():
            auto.click(*self.shift(offset_lock))
        auto.moveTo(x,y)

if __name__ == '__main__':
    controller = AxoclampController()

    controller.set_capneut(100)

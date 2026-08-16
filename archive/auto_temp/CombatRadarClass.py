import pyautogui

class CombatRadar:
    def __init__(self, config):
        self.cfg = config['combat_system']
        
    def is_target_detected(self):
        """Quét dải ngang tìm Đỏ/Trắng/Vàng"""
        try:
            start_x = self.cfg['radar_center_x'] - (self.cfg['scan_width'] // 2)
            start_y = self.cfg['radar_center_y'] - (self.cfg['scan_height'] // 2)
            
            img = pyautogui.screenshot(region=(start_x, start_y, 
                                              self.cfg['scan_width'], 
                                              self.cfg['scan_height']))
            pixels = list(img.getdata())
            
            # for r, g, b in pixels:
            #     # Logic Trắng/Vàng/Đỏ đã chốt
            #     if r > 250 and g > 250 and b > 250: return True # WHITE
            #     if r > 240 and g > 240 and (100 < b < 150): return True # YELLOW
            #     if (110 <= r <= 185) and (g < 95) and (b < 95) and (abs(g - b) < 15): return True # RED
            # return False
            for r, g, b in pixels:
                # Logic phát hiện màu
                if (r > 250 and g > 250 and b > 250) or \
                   (r > 240 and g > 240 and (100 < b < 150)) or \
                   ((110 <= r <= 185) and (g < 95) and (b < 95)):
                    print("DEBUG: Found Color!", end='\r') # Bật dòng này để test
                    return True 
            return False
        except:
            return False
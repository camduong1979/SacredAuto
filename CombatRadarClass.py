import pyautogui

class CombatRadar:
    def __init__(self, config):
        self.cfg = config['combat_system']
        
    def is_target_detected(self):
        """Quét dải ngang tìm Đỏ/Trắng/Vàng trên thanh HP quái"""
        try:
            start_x = self.cfg['radar_center_x'] - (self.cfg['scan_width'] // 2)
            start_y = self.cfg['radar_center_y'] - (self.cfg['scan_height'] // 2)
            
            img = pyautogui.screenshot(region=(start_x, start_y, 
                                              self.cfg['scan_width'], 
                                              self.cfg['scan_height']))
            pixels = list(img.getdata())

            for r, g, b in pixels:
                # WHITE: thanh HP đầy
                if r > 250 and g > 250 and b > 250:
                    return True
                # YELLOW: thanh HP vàng
                if r > 240 and g > 240 and (100 < b < 150):
                    return True
                # RED: thanh HP đỏ (quái đang bị tấn công / HP thấp)
                if (110 <= r <= 185) and (g < 95) and (b < 95):
                    return True
            return False
        except Exception as e:
            print(f"[RADAR ERROR] {e}")
            return False
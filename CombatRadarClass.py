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

            # --- OLD CODE (REPLACED) ---
            # Early-return ngay pixel đầu tiên → không đếm được RED, dễ bị noise trigger
            # Thiếu abs(g - b) < 15 → nhận diện sai màu RED (false positive tím/magenta)
            # for r, g, b in pixels:
            #     if r > 250 and g > 250 and b > 250:
            #         return True
            #     if r > 240 and g > 240 and (100 < b < 150):
            #         return True
            #     if (110 <= r <= 185) and (g < 95) and (b < 95):
            #         return True
            # return False
            # ---------------------------

            # NEW LOGIC (sync với debug_v3.py):
            # - Duyệt TOÀN BỘ pixel, tích lũy red_count trước khi quyết định
            # - RED thêm abs(g - b) < 15: đảm bảo g và b gần nhau → màu đỏ thuần, loại tím/magenta
            # - Ngưỡng red_count >= 2: chống nhiễu pixel đơn lẻ ngẫu nhiên
            found_text = False
            red_count  = 0

            for r, g, b in pixels:
                # WHITE: thanh HP đầy
                if r > 250 and g > 250 and b > 250:
                    found_text = True
                # YELLOW: thanh HP vàng
                elif r > 240 and g > 240 and (100 < b < 150):
                    found_text = True
                # RED: thanh HP đỏ — thêm abs(g-b)<15 để lọc màu đỏ thuần, chống false positive
                elif (110 <= r <= 185) and (g < 95) and (b < 95) and (abs(g - b) < 15):
                    red_count += 1

            return found_text or (red_count >= 2)

        except Exception as e:
            print(f"[RADAR ERROR] {e}")
            return False
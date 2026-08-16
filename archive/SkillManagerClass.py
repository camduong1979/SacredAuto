# # ================= MODULE 3: QUẢN LÝ SKILL (VISION & DURATION) =================
# class SkillManager:
#     def __init__(self, class_name, skill_list):
#         self.class_name = class_name
#         self.skills = skill_list
#         for s in self.skills: s['last_cast_time'] = 0

#     def is_pixel_match(self, sct, skill):
#         # Chụp màn hình 1 pixel
#         bbox = {'top': skill['y'], 'left': skill['x'], 'width': 1, 'height': 1}
#         img = np.array(sct.grab(bbox))
#         pixel = img[0, 0]
#         b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
        
#         # So sánh màu
#         tr, tg, tb = skill['color_rgb']
#         tolerance = skill.get('tolerance', 30)
#         return (abs(r - tr) < tolerance) and \
#                (abs(g - tg) < tolerance) and \
#                (abs(b - tb) < tolerance)

#     def process_skills(self, sct):
#         current_time = time.time()
#         for skill in self.skills:
#             # 1. Check Duration (Hết hiệu lực chưa?)
#             duration = skill.get('duration', 0)
#             if current_time - skill['last_cast_time'] < duration:
#                 continue 

#             # 2. Check Vision (Skill có sáng màu không?)
#             if self.is_pixel_match(sct, skill):
#                 print(f"[SKILL] Cast {skill['name']} (Duration: {duration}s)")
                
#                 # Thực hiện Combo
#                 pydirectinput.press(skill['key'])
#                 time.sleep(0.05)
#                 pydirectinput.click(button='right')
                
#                 skill['last_cast_time'] = current_time
#                 return True # Báo là vừa cast xong để main loop delay
#         return False
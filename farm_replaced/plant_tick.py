# Lưu tuổi của cây bằng dictionary
# Kiểm tra tuổi cây = lấy thời gian trồng trừ thời gian hiện tại
# Print nó ra
# Lấy được giá trị thời gian fully grow của từng loại cây

plant_tick = {}

def time_plant():
    x = get_pos_x()
    y = get_pos_y()
    plant_tick[(x,y)] = get_tick_count()

def check_threshold():
    if can_harvest():
        threshold = get_tick_count() - plant_tick[(x,y)]
        print(threshold)
    else:
        do_a_flip()

while True:
    till()
    plant(Entities.Pumpkin)
    time_plant()
    check_threshold()
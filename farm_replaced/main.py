clear()

# ==== Import handlers ====
from hay_mode import handle_hay_tile
#from carrot_tree_mode import handle_carrot_tree_tile
#from pumpkin_mode import handle_pumpkin_tile

# ==== Mode constant ===
MODE_HAY = 0
MODE_CARROT_TREE = 1
MODE_PUMPKIN = 2

# Change farm mode
mode = MODE_HAY

# ==== Moving config ==== 
dir = 1 # di sang phai
MAX_INDEX = 5 # do rong cua farm -1 theo index

# ==== Tile dispatch ====
def handle_tile():
	if mode == MODE_HAY:
		handle_hay_tile()
	elif mode == MODE_CARROT_TREE:
		handle_carrot_tree_tile()
	elif mode == MODE_PUMPKIN:
		handle_pumpkin_tile()

# ==== Movement helpers ====
def go_bottom_left():
	while get_pos_x() > 0:
		move(West)
	while get_pos_y() > 0:
		move(South)

def move_around():
    global dir

    # Xử lý ô hiện tại
    handle_tile()

    # Khi đã lên HÀNG TRÊN CÙNG và đang ở GÓC TRÁI (0, MAX_INDEX)
    # => reset về (0,0) rồi làm lại
    if get_pos_y() == MAX_INDEX and get_pos_x() == 0:
        go_bottom_left()
        dir = 1
        return

    # Di chuyển zigzag
    if dir == 1:
        # Đang đi sang phải
        if get_pos_x() < MAX_INDEX:
            move(East)
        else:
            # Chạm mép phải -> lên trên + đổi hướng
            if get_pos_y() < MAX_INDEX:
                move(North)
            dir = -1
    else:
        # Đang đi sang trái
        if get_pos_x() > 0:
            move(West)
        else:
            # Chạm mép trái -> lên trên + đổi hướng
            if get_pos_y() < MAX_INDEX:
                move(North)
            dir = 1


# ==== Main loop =====
while True:
	move_around()
# Xử lý 1 ô trong chế độ farm PUMPKIN
def water_crop():
	use_item(Items.Water)

square = 6 # dung de xac dinh vung trong pumpkin

def handle_pumpkin_tile():
	x = get_pos_x()
	y = get_pos_y()

	#Trong pumpkin tren title 4x4, con lai trong cay khac
	if x < square and y < square:
		if get_ground_type() != Grounds.Soil:
			till()
			plant(Entities.Pumpkin)    

		# Neu da trong pumpkin va trong range 4x4 theo quy dinh phia tren
		if can_harvest() == True:
			harvest()
			plant(Entities.Pumpkin)
		
		else:
			water_crop()
			plant(Entities.Pumpkin)					

	else:
		if get_ground_type() != Grounds.Soil:
			till()
			plant(Entities.Carrot)
		if can_harvest():
			harvest()
			plant(Entities.Carrot)
	return
	
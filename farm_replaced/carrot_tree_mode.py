def water_tree():
	use_item(Items.Water)

def handle_carrot_tree_tile():
	x = get_pos_x()
	y = get_pos_y()

	# Ô chẵn = Tree, ô lẻ = Carrot
	if (x + y) % 2 == 0:
		target = Entities.Tree
	else:
		target = Entities.Carrot

	entity = get_entity_type()

	# --- ƯU TIÊN 1: Nếu thu hoạch được ---
	if can_harvest():
		harvest()

		# sau harvest nếu đất chưa Soil → till
		if get_ground_type() != Grounds.Soil:
			till()

		plant(target)
		if target == Entities.Tree:
			water_tree()
		return

	# --- ƯU TIÊN 2: Nếu ô TRỐNG ---
	entity = get_entity_type()
	if entity == None:
		if get_ground_type() != Grounds.Soil:
			till()
		plant(target)
		if target == Entities.Tree:
			water_tree()
		return

	# --- ƯU TIÊN 3: Có cây nhưng chưa chín ---
	if target == Entities.Tree:
		water_tree()
	# Nếu là Carrot thì không tưới


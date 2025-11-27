# Xử lý 1 ô trong chế độ farm HAY
def handle_hay_tile():
    if can_havest() and get_entity_type() == Entities.Grass:
        harvest()
    return
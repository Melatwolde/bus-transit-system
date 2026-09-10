class BusRoute:
    def __init__(self, route_id: str, origin: str, destination: str, capacity: int = 40):
        self.route_id = route_id
        self.origin = origin
        self.destination = destination
        self.capacity = capacity
        self.booked_seats = 0

    def reserve_seat(self) -> bool:
        if self.booked_seats >= self.capacity:
            return False
        self.booked_seats += 1
        return True

    def release_seat(self) -> bool:
        if self.booked_seats > 0:
            self.booked_seats -= 1
            return True
        return False

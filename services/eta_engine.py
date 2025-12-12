# Mock Route Data (In production, load this from DB)
# "avg_time" is minutes needed to reach the NEXT stop
ROUTE_TOPOLOGY = {
    "STOP_A": {"avg_time": 10}, 
    "STOP_B": {"avg_time": 15},
    "STOP_C": {"avg_time": 8},
    "STOP_D": {"avg_time": 0}  # Terminal
}

class ETAEngine:
    def __init__(self):
        self.current_delay = 0  # Global delay accumulator

    def calculate(self, current_stop, next_stop, progress, speed):
        """
        Calculates ETA based on remaining distance + dynamic delay.
        """
        # 1. Update Dynamic Delay based on speed
        # If speed is < 20km/h, assume we are building up delay
        if speed < 20:
            self.current_delay += 0.5 # Add 30 seconds delay per tick
        elif speed > 50 and self.current_delay > 0:
            self.current_delay -= 0.5 # Recover time if moving fast
            
        # 2. Get baseline time for segment
        segment = ROUTE_TOPOLOGY.get(current_stop)
        if not segment:
            return 0.0, "Unknown Route", 0

        total_segment_time = segment['avg_time']
        
        # 3. Calculate remaining time
        time_remaining = total_segment_time * (1 - progress)
        
        # 4. Final ETA
        final_eta = time_remaining + self.current_delay
        
        status = "On Time"
        if self.current_delay > 5:
            status = f"Delayed by {int(self.current_delay)} mins"
        elif self.current_delay < -2:
            status = "Early"

        return round(final_eta, 1), status, int(self.current_delay)

# Singleton instance
eta_service = ETAEngine()
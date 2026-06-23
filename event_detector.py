import time
import math

class LitterEventDetector:
    """
    Rule-based prototype to detect littering violations.
    Transitions litter state between 'carrying', 'dropped', 'violation', and 'unowned'.
    """
    def __init__(self, stationary_time_threshold=3.0, walk_away_distance=150, position_noise_threshold=15):
        self.stationary_time_threshold = stationary_time_threshold
        self.walk_away_distance = walk_away_distance
        self.position_noise_threshold = position_noise_threshold
        
        # State:
        # Maps litter_track_id -> dict containing event state details
        self.litter_states = {}

    def update(self, tracked_persons, tracked_litter):
        """
        Updates the event states of all visible litter items.
        
        Args:
            tracked_persons: List of dicts representing detected people in the frame
            tracked_litter: List of dicts representing detected litter items in the frame
            
        Returns:
            tracked_litter: The input list updated with 'event_status' and 'time_since_drop'
            violations_triggered: List of new violation dictionaries detected in this frame
        """
        person_map = {p["id"]: p for p in tracked_persons if p["id"] is not None}
        current_time = time.time()
        violations_triggered = []
        
        visible_litter_ids = set()
        
        for litter in tracked_litter:
            litter_id = litter["id"]
            if litter_id is None:
                continue
                
            visible_litter_ids.add(litter_id)
            
            associated_person_id = litter.get("associated_person_id")
            owner_person_id = litter.get("owner_person_id")
            
            lx1, ly1, lx2, ly2 = litter["bbox"]
            lcx = (lx1 + lx2) // 2
            lcy = (ly1 + ly2) // 2
            
            if litter_id not in self.litter_states:
                # First time seeing this litter item in the event pipeline
                if associated_person_id is not None:
                    self.litter_states[litter_id] = {
                        "dropped_time": None,
                        "dropped_pos": None,
                        "owner_id": associated_person_id,
                        "status": "carrying",
                        "triggered": False
                    }
                else:
                    self.litter_states[litter_id] = {
                        "dropped_time": None,
                        "dropped_pos": None,
                        "owner_id": None,
                        "status": "unowned",
                        "triggered": False
                    }
            else:
                state = self.litter_states[litter_id]
                
                # If currently held, reset dropped timer (carried again)
                if associated_person_id is not None:
                    state["status"] = "carrying"
                    state["dropped_time"] = None
                    state["dropped_pos"] = None
                    state["owner_id"] = associated_person_id
                    state["triggered"] = False
                else:
                    # Transition from carrying/unowned to dropped
                    if state["status"] in ("carrying", "unowned") or state["owner_id"] is None:
                        if owner_person_id is not None:
                            state["status"] = "dropped"
                            state["dropped_time"] = current_time
                            state["dropped_pos"] = (lcx, lcy)
                            state["owner_id"] = owner_person_id
                    
                    # If in dropped state, check if stationary and owner has walked away
                    elif state["status"] == "dropped":
                        if state["dropped_pos"] is not None:
                            dx = lcx - state["dropped_pos"][0]
                            dy = lcy - state["dropped_pos"][1]
                            dist_from_dropped = math.sqrt(dx**2 + dy**2)
                            
                            # Check if the object is stationary (allowing for small tracker noise)
                            if dist_from_dropped <= self.position_noise_threshold:
                                elapsed = current_time - state["dropped_time"]
                                owner_id = state["owner_id"]
                                
                                owner_walked_away = False
                                if owner_id not in person_map:
                                    # Owner left frame completely
                                    owner_walked_away = True
                                else:
                                    # Owner still in frame, check distance
                                    p_bbox = person_map[owner_id]["bbox"]
                                    px1, py1, px2, py2 = p_bbox
                                    
                                    # Find closest distance from owner bounding box to litter centroid
                                    x_closest = max(px1, min(lcx, px2))
                                    y_closest = max(py1, min(lcy, py2))
                                    owner_dist = math.sqrt((lcx - x_closest)**2 + (lcy - y_closest)**2)
                                    
                                    if owner_dist > self.walk_away_distance:
                                        owner_walked_away = True
                                
                                # Violation condition: stationary >= threshold AND owner walked away
                                if elapsed >= self.stationary_time_threshold and owner_walked_away:
                                    state["status"] = "violation"
                                    if not state["triggered"]:
                                        state["triggered"] = True
                                        violations_triggered.append({
                                            "litter_id": litter_id,
                                            "owner_id": owner_id,
                                            "class_name": litter["class_name"],
                                            "bbox": litter["bbox"],
                                            "timestamp": current_time
                                        })
                            else:
                                # Object moved significantly, update dropped position and reset timer
                                state["dropped_time"] = current_time
                                state["dropped_pos"] = (lcx, lcy)
            
            # Attach status and details back to litter dictionary for drawing/UI
            if litter_id in self.litter_states:
                litter["event_status"] = self.litter_states[litter_id]["status"]
                litter["event_owner_id"] = self.litter_states[litter_id]["owner_id"]
                if self.litter_states[litter_id]["dropped_time"] is not None:
                    litter["time_since_drop"] = current_time - self.litter_states[litter_id]["dropped_time"]
                else:
                    litter["time_since_drop"] = 0.0
            else:
                litter["event_status"] = "unknown"
                litter["event_owner_id"] = None
                litter["time_since_drop"] = 0.0

        # Clean up entries for litter items that disappeared
        for litter_id in list(self.litter_states.keys()):
            if litter_id not in visible_litter_ids:
                self.litter_states.pop(litter_id, None)
                
        return tracked_litter, violations_triggered

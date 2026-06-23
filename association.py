import math
import time

class LitterAssociator:
    """
    Stateful association logic to link detected litter/garbage items
    to the people carrying or dropping them.
    Supports trajectory-based history matching to resolve ID switches/losses when dropped.
    """
    def __init__(self, distance_threshold=120, max_stale_frames=100, trajectory_history_seconds=5.0):
        self.distance_threshold = distance_threshold
        self.max_stale_frames = max_stale_frames
        self.trajectory_history_seconds = trajectory_history_seconds
        
        # State:
        # Maps litter_track_id -> person_track_id (last known owner)
        self.litter_owners = {}
        
        # Maps litter_track_id -> frames since last seen (used to clean up state)
        self.litter_stale_counters = {}
        
        # Maps person_track_id -> list of ((cx, cy), timestamp) representing trajectory
        self.person_trajectories = {}

    def associate(self, tracked_persons, tracked_litter):
        """
        Associates each litter item with the closest person or their historical trajectory.
        
        Args:
            tracked_persons: List of dicts representing detected people
            tracked_litter: List of dicts representing detected litter items
            
        Returns:
            tracked_litter: Updated list with associated/owner IDs
        """
        current_time = time.time()
        
        # 1. Update person trajectories
        for person in tracked_persons:
            person_id = person["id"]
            if person_id is None:
                continue
                
            px1, py1, px2, py2 = person["bbox"]
            pcx = (px1 + px2) // 2
            pcy = (py1 + py2) // 2
            
            if person_id not in self.person_trajectories:
                self.person_trajectories[person_id] = []
                
            self.person_trajectories[person_id].append(((pcx, pcy), current_time))
            
            # Prune old trajectory points
            self.person_trajectories[person_id] = [
                pt for pt in self.person_trajectories[person_id]
                if current_time - pt[1] <= self.trajectory_history_seconds
            ]
            
        # Clean up trajectories for persons no longer in frame (optional: keep for a bit, pruned by time)
        active_person_ids = {p["id"] for p in tracked_persons if p["id"] is not None}
        for p_id in list(self.person_trajectories.keys()):
            if p_id not in active_person_ids:
                # Still prune old points
                self.person_trajectories[p_id] = [
                    pt for pt in self.person_trajectories[p_id]
                    if current_time - pt[1] <= self.trajectory_history_seconds
                ]
                if not self.person_trajectories[p_id]:
                    self.person_trajectories.pop(p_id, None)

        # 2. Update litter stale counters for state cleanup
        visible_litter_ids = {litter["id"] for litter in tracked_litter if litter["id"] is not None}
        for litter_id in list(self.litter_owners.keys()):
            if litter_id not in visible_litter_ids:
                self.litter_stale_counters[litter_id] = self.litter_stale_counters.get(litter_id, 0) + 1
                if self.litter_stale_counters[litter_id] > self.max_stale_frames:
                    self.litter_owners.pop(litter_id, None)
                    self.litter_stale_counters.pop(litter_id, None)
            else:
                self.litter_stale_counters[litter_id] = 0

        # 3. Find association for each litter item
        for litter in tracked_litter:
            litter_id = litter["id"]
            if litter_id is None:
                litter["associated_person_id"] = None
                litter["owner_person_id"] = None
                litter["closest_person_dist"] = None
                continue
                
            lx1, ly1, lx2, ly2 = litter["bbox"]
            lcx = (lx1 + lx2) // 2
            lcy = (ly1 + ly2) // 2
            
            # A. Try direct spatial overlap/proximity in current frame
            closest_person_id = None
            min_dist = float('inf')
            
            for person in tracked_persons:
                person_id = person["id"]
                if person_id is None:
                    continue
                    
                px1, py1, px2, py2 = person["bbox"]
                x_closest = max(px1, min(lcx, px2))
                y_closest = max(py1, min(lcy, py2))
                
                dist = math.sqrt((lcx - x_closest) ** 2 + (lcy - y_closest) ** 2)
                if dist < min_dist:
                    min_dist = dist
                    closest_person_id = person_id
            
            # Direct association threshold
            if min_dist <= self.distance_threshold:
                litter["associated_person_id"] = closest_person_id
                litter["closest_person_dist"] = min_dist
                self.litter_owners[litter_id] = closest_person_id
            else:
                litter["associated_person_id"] = None
                litter["closest_person_dist"] = min_dist if min_dist != float('inf') else None
                
                # B. If direct spatial link failed, and this litter item has NO owner in state:
                # Use trajectory-based historical proximity matching!
                if litter_id not in self.litter_owners:
                    best_match_person_id = None
                    best_match_dist = float('inf')
                    
                    for p_id, trajectory in self.person_trajectories.items():
                        for pt_pos, pt_time in trajectory:
                            p_dist = math.sqrt((lcx - pt_pos[0])**2 + (lcy - pt_pos[1])**2)
                            if p_dist < best_match_dist:
                                best_match_dist = p_dist
                                best_match_person_id = p_id
                                
                    # Match if the closest historical point was within threshold * 1.5
                    if best_match_dist <= self.distance_threshold * 1.5:
                        self.litter_owners[litter_id] = best_match_person_id
                        print(f"[ASSOCIATOR] Trajectory Match: Linked new litter #{litter_id} to Person #{best_match_person_id} (dist: {best_match_dist:.1f}px)")
            
            # Fetch final historical owner ID from state
            litter["owner_person_id"] = self.litter_owners.get(litter_id, None)
            
        return tracked_litter

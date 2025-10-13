from datetime import time, timedelta


def generate_timeslots() -> list[str]:
    """Generate 18 timeslots (20-minute intervals)."""
    slots = []
    # Morning: 9:00-11:55 (9 slots)
    times = [
        "09:00-09:20", "09:20-09:40", "09:40-10:00",
        "10:00-10:20", "10:20-10:40", "10:40-11:00",
        "11:00-11:20", "11:20-11:40", "11:40-12:00"
    ]
    slots.extend(times)
    
    # Afternoon: 13:00-16:40 (9 slots)
    times = [
        "13:00-13:20", "13:20-13:40", "13:40-14:00",
        "14:00-14:20", "14:20-14:40", "14:40-15:00",
        "15:00-15:20", "15:20-15:40", "15:40-16:00"
    ]
    slots.extend(times)
    
    return slots


def parse_unavailable_times(time_str: str) -> list[str]:
    """Parse unavailable time string to list of timeslots.
    
    Supports format: day・time or just time
    Example: "金・14:30" or "14:30-15:30"
    """
    if not time_str or str(time_str).strip() == '' or str(time_str) == 'nan':
        return []
    
    import re
    import unicodedata
    
    timeslots = generate_timeslots()
    unavailable = []
    
    # Normalize text (full-width to half-width)
    time_str = unicodedata.normalize('NFKC', str(time_str))
    
    # Split by ・ to separate day and time
    parts = time_str.split('・')
    
    # Extract time part (last part after ・, or the whole string)
    time_part = parts[-1] if parts else time_str
    
    # Extract time patterns like "14:30" or "14:30-15:30"
    time_patterns = re.findall(r'(\d{1,2}):(\d{2})', time_part)
    
    if not time_patterns:
        return []
    
    # If we have 2 times, treat as start-end range
    if len(time_patterns) >= 2:
        start_h, start_m = int(time_patterns[0][0]), int(time_patterns[0][1])
        end_h, end_m = int(time_patterns[1][0]), int(time_patterns[1][1])
    else:
        # Single time, assume 1 hour block
        start_h, start_m = int(time_patterns[0][0]), int(time_patterns[0][1])
        end_h, end_m = start_h + 1, start_m
    
    # Find matching timeslots
    for slot in timeslots:
        slot_start = slot.split('-')[0]
        slot_h, slot_m = map(int, slot_start.split(':'))
        
        if (start_h, start_m) <= (slot_h, slot_m) < (end_h, end_m):
            unavailable.append(slot)
    
    return unavailable


def timeslot_to_index(timeslot: str) -> int:
    """Convert timeslot string to matrix index."""
    timeslots = generate_timeslots()
    try:
        return timeslots.index(timeslot)
    except ValueError:
        return -1


def check_shift_availability(shift_code: str, timeslot: str) -> bool:
    """Check if therapist is available based on shift code."""
    if not shift_code or str(shift_code).strip() == '' or str(shift_code) == 'nan':
        return False
    
    code = str(shift_code).strip()
    
    if code == '○':
        return True
    
    slot_start = timeslot.split('-')[0]
    hour = int(slot_start.split(':')[0])
    
    if code == 'AN':  # 12:45-17:30
        return hour >= 13
    elif code == 'PN':  # 8:45-12:00
        return hour < 12
    
    return False

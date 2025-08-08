from datetime import datetime

def normalize_datetime(dt):
    if hasattr(dt, "replace"):  # works for both datetime and DatetimeWithNanoseconds
        return dt.replace(tzinfo=None)  # remove tzinfo if needed
    return dt
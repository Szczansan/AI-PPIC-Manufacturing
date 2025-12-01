def output_per_hour(ct, cav, efficiency):
    if not ct or ct == 0:
        return 0
    return (3600 / ct) * cav * efficiency


def required_hours(forecast_qty, output_hr):
    if output_hr == 0:
        return 0
    return forecast_qty / output_hr


def required_days(req_hours, effective_hours_day):
    if effective_hours_day == 0:
        return 0
    return req_hours / effective_hours_day

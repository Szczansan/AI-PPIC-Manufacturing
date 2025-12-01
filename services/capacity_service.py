from utils.calculator import output_per_hour, required_hours, required_days

def calculate_part_capacity(forecast_row, master_row, rules, working_days):
    ct = master_row["cycle_time"]
    cav = master_row["cavity"]
    tonage = master_row["tonage"]
    qty = forecast_row["forecast_qty"]

    eff = rules["efficiency"]
    eff_hours_day = rules["shift_hours"] * rules["shift_per_day"] * rules["efficiency"]

    out_hr = output_per_hour(ct, cav, eff)
    req_hr = required_hours(qty, out_hr)
    req_days = required_days(req_hr, eff_hours_day)

    return {
        "part_no": forecast_row["part_no"],
        "part_name": master_row["part_name"],
        "tonage": tonage,
        "forecast_qty": qty,
        "cycle_time": ct,
        "cavity": cav,
        "output_per_hour": out_hr,
        "required_hours": req_hr,
        "required_days": req_days,
    }

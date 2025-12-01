def allocate_hours_to_machines(cluster_hours, machine_list, cap_month):
    assignments = []
    remaining = cluster_hours

    for mc in machine_list:
        if remaining <= 0:
            assignments.append({"machine_id": mc, "assigned_hours": 0})
            continue

        if remaining > cap_month:
            assignments.append({"machine_id": mc, "assigned_hours": cap_month})
            remaining -= cap_month
        else:
            assignments.append({"machine_id": mc, "assigned_hours": remaining})
            remaining = 0

    return assignments

import pandas as pd
import random

# Konfigurasi Data Dummy
num_rows = 1000
materials = ['ABS', 'PP', 'PC', 'PA6', 'POM', 'PMMA']
grades = ['GP-100', 'HI-121', 'V0-55', 'GF-30', 'Standard']
colors = ['Black', 'Natural', 'White', 'Grey', 'Red', 'Blue']
customers = ['Astra Honda', 'Toyota Motor', 'Yamaha Music', 'Samsung', 'LG Electronics']
part_types = ['Cover', 'Housing', 'Bracket', 'Gear', 'Cap', 'Lever', 'Panel']

# List Mesin (Kode - Tonase)
small_machines = ['MC-01 (50T)', 'MC-02 (80T)', 'MC-03 (110T)', 'MC-04 (150T)']
big_machines = ['MC-05 (250T)', 'MC-06 (350T)', 'MC-07 (450T)', 'MC-08 (650T)']

data = []

for i in range(1, num_rows + 1):
    # --- Logic Lama ---
    mat = random.choice(materials)
    weight = round(random.uniform(5.0, 500.0), 2)
    cycle = round((weight / 10) + random.uniform(5, 20), 1)
    
    # --- Logic Baru untuk Kolom Tambahan ---
    # 1. Machine ID: Pilih mesin gede kalau barangnya berat (>200g) biar realistis dikit
    if weight > 200:
        selected_machine = random.choice(big_machines)
    else:
        selected_machine = random.choice(small_machines)

    # 2. Mold ID
    mold_suffix = random.randint(100, 999)
    
    row = {
        'part_no': f"PN-{random.randint(1000, 9999)}-{random.choice(['A', 'B', 'C'])}",
        'part_name': f"{random.choice(part_types)} {random.choice(['Front', 'Rear', 'Inner', 'Outer'])}",
        'model': f"MDL-{random.randint(10, 99)}",
        'customer': random.choice(customers),
        'cav': random.choice([1, 2, 4, 8, 16]),
        'cycle_time': cycle,
        'weight_part': weight,
        'weight_runner': round(weight * random.uniform(0.05, 0.2), 2),
        'spq': random.choice([50, 100, 200, 500, 1000]),
        'type_material': mat,
        'grade_material': f"{mat}-{random.choice(grades)}",
        'color_material': random.choice(colors),
        
        # --- Kolom Baru ---
        'mold_id': f"MLD-{mold_suffix}",
        'machine_id': selected_machine,
        'scrap_rate': round(random.uniform(0.5, 3.0), 2), # Persentase (%)
        'changeover_min': random.choice([30, 45, 60, 90, 120]) # Menit
    }
    data.append(row)

# Buat DataFrame
df = pd.DataFrame(data)

# Export ke Excel
file_name = "sample_injection_data_v2.xlsx"
df.to_excel(file_name, index=False)

print(f"Mantap bre! File '{file_name}' sudah jadi dengan kolom tambahan (mold, machine, scrap, changeover).")
print(df[['part_no', 'machine_id', 'scrap_rate']].head()) # Preview dikit
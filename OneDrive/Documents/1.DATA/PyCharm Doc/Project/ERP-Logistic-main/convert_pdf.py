from PIL import Image
import os

# Ganti nama file ini sesuai nama file gambar lo kalau beda
input_path = 'logo-white.png'
output_path = 'logo-white.pdf'

if os.path.exists(input_path):
    try:
        image = Image.open(input_path)

        # Convert mode ke RGB kalau lo mau backgroundnya jadi putih otomatis
        # Kalau mau tetep transparan/apa adanya, biarin default (Pillow handle RGBA)
        # image = image.convert('RGB') 

        image.save(output_path, "PDF", resolution=100.0)
        print(f"Sukses bre! File udah jadi: {output_path}")
    except Exception as e:
        print(f"Waduh error: {e}")
else:
    print(f"File {input_path} gak ketemu bre, cek lagi namanya atau foldernya.")
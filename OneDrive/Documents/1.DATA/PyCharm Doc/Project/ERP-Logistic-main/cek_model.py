import google.generativeai as genai

genai.configure(api_key="AIzaSyDdpEUN9te2DbWHTFwB2tU5vjKh-vQosW4")

print("Daftar Model yang Tersedia:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")
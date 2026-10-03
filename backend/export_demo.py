# import json
# import sys
# import urllib.request

# doc_id = sys.argv[1]
# d = json.load(urllib.request.urlopen(f"http://127.0.0.1:8000/api/documents/{doc_id}"))
# if not d["hindi"]:
#     sys.exit("No Hindi saved for this document. Tap the Hindi button in the app first.")
# out = {
#     "text": d["original_text"],
#     "result": d["result"],
#     "hindi": d["hindi"],
#     "disclaimer": d["disclaimer"],
# }
# with open("../frontend/src/demo-data.json", "w", encoding="utf-8") as f:
#     json.dump(out, f, ensure_ascii=False, indent=1)
# print("wrote frontend/src/demo-data.json")
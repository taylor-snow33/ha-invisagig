import urllib.request
import json
import time

API_KEY = "pk.95477a0b2d1b490fd2af22b4e9fa5198"
MCC = 311
MNC = 480
LAC = 11271
ENODEB = 344442
BASE_ID = ENODEB * 256

# Common Verizon sector maps.
SECTORS_TO_TRY = [1, 2, 3, 11, 12, 13, 21, 22, 23, 31, 32, 33]

print(f"Testing Tower {ENODEB} (Base CID: {BASE_ID})")

for sector in SECTORS_TO_TRY:
    cid = BASE_ID + sector
    url = f"https://opencellid.org/cell/get?key={API_KEY}&mcc={MCC}&mnc={MNC}&lac={LAC}&cellid={cid}&format=json"
    
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode())
            
        if "bit_error" in data or "error" in data:
            print(f"Sector {sector} (CID {cid}): Not Found")
        else:
            print(f"!!! SUCCESS !!! Sector {sector} (CID {cid}) FOUND!")
            print(data)
            break
    except Exception as e:
        print(f"Sector {sector} (CID {cid}): Failed/Not Found ({e})")
    
    time.sleep(0.5)

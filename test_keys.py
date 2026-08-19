import os
import json
import urllib.request
import urllib.error

def check_anthropic(key):
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }, data=b'{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}')
    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        # If it's a 401 or 403, it's dead/invalid. 
        # If it's 400 (bad request), it might be active but payload is wrong, though 400 with API key usually means key is valid.
        if e.code in (401, 403):
            return False
        return True
    except Exception:
        return False

def check_gemini(key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        return False
    except Exception:
        return False

def check_openrouter(key):
    req = urllib.request.Request("https://openrouter.ai/api/v1/auth/key", headers={
        "Authorization": f"Bearer {key}"
    })
    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        return False
    except Exception:
        return False

def check_generic(key):
    # Can't reliably check unknown keys, mark as unknown
    return None

keys_to_check = []
for k, v in os.environ.items():
    if "API_KEY" in k or "TOKEN" in k:
        if v and v != "your_key" and v != "your_token":
            keys_to_check.append((k, v))

# Add from .env files if we find them
# Just to be thorough in the current dir
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                if "API_KEY" in k or "TOKEN" in k:
                    if v and v != "your_key" and v != "your_token" and not any(ek[0] == k for ek in keys_to_check):
                        keys_to_check.append((k, v))

out_dir = r"C:\Users\lenovo\OneDrive\Desktop\supaagent\Keys_Compiled"
os.makedirs(out_dir, exist_ok=True)

for k, v in keys_to_check:
    platform = k.split("_")[0].capitalize()
    
    # Check status
    status = "Unknown"
    if "ANTHROPIC" in k:
        is_active = check_anthropic(v)
        status = "Active" if is_active else "Dead"
    elif "GEMINI" in k:
        is_active = check_gemini(v)
        status = "Active" if is_active else "Dead"
    elif "OPENROUTER" in k:
        is_active = check_openrouter(v)
        status = "Active" if is_active else "Dead"
    else:
        status = "Unknown"
        
    platform_dir = os.path.join(out_dir, platform)
    status_dir = os.path.join(platform_dir, status)
    os.makedirs(status_dir, exist_ok=True)
    
    key_file = os.path.join(status_dir, f"{k}.txt")
    with open(key_file, "w") as f:
        f.write(f"Key Name: {k}\n")
        f.write(f"Key Value: {v}\n")
        f.write(f"Status: {status}\n")

print(f"Compiled {len(keys_to_check)} keys into {out_dir}")

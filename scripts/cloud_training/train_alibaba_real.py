import os
import json
import urllib.request
from openai import OpenAI
import time

# 1. Fetch Real Data about Alibaba
print("Fetching real data about Alibaba Group from Wikipedia...")
url = "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&titles=Alibaba_Group&format=json"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    extract = page.get("extract", "")

import re
text = re.sub('<[^<]+>', '', extract)

# 2. Create Real Q&A Pairs for Fine-Tuning
print("Generating authentic QA pairs from real data...")
qa_pairs = [
    {
        "messages": [
            {"role": "system", "content": "You are NES, a knowledgeable AI assistant."},
            {"role": "user", "content": "What is Alibaba Group?"},
            {"role": "assistant", "content": "Alibaba Group Holding Limited is a Chinese multinational technology company specializing in e-commerce, retail, Internet, and technology."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are NES, a knowledgeable AI assistant."},
            {"role": "user", "content": "When was Alibaba founded and by whom?"},
            {"role": "assistant", "content": "Alibaba was founded on 28 June 1999 in Hangzhou, Zhejiang, by Jack Ma and 17 of his students and friends."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are NES, a knowledgeable AI assistant."},
            {"role": "user", "content": "Tell me about Alibaba's business scope."},
            {"role": "assistant", "content": "The company provides consumer-to-consumer (C2C), business-to-consumer (B2C), and business-to-business (B2B) sales services via web portals, as well as electronic payment services, shopping search engines and cloud computing services."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are NES, a knowledgeable AI assistant."},
            {"role": "user", "content": "What are some notable achievements of Alibaba?"},
            {"role": "assistant", "content": "Alibaba is one of the world's largest retailers and e-commerce companies. In 2020, it was also rated as the fifth-largest artificial intelligence company."}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are NES, a knowledgeable AI assistant."},
            {"role": "user", "content": "Summarize Alibaba's operations."},
            {"role": "assistant", "content": f"Based on authentic encyclopedia data: {text[:200]}..."}
        ]
    }
]

dataset_path = "alibaba_real_sft.jsonl"
with open(dataset_path, "w", encoding="utf-8") as f:
    for pair in qa_pairs:
        f.write(json.dumps(pair) + "\n")
print(f"Wrote {len(qa_pairs)} authentic training examples to {dataset_path}")

# 3. Authenticate and Upload to Alibaba DashScope
print("Connecting to Alibaba DashScope...")
os.environ['OPENAI_API_KEY'] = 'sk-ws-H.XPHXDY.sATT.MEYCIQCDahlSsP4_CpyvbejcRamVciFucCDwMCXMfSAeC4HMTwIhAOkqf0ihlHGTIlhnkTMo__MDFwf163gmjBpfpCCnbxfp'
os.environ['OPENAI_BASE_URL'] = 'https://ws-2w8douvgerv91zia.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1'

client = OpenAI()

print("Uploading training file...")
with open(dataset_path, "rb") as f:
    file_obj = client.files.create(file=f, purpose="fine-tune")

print(f"File uploaded successfully! File ID: {file_obj.id}")

print("Waiting for file processing...")
time.sleep(5)

print("Starting fine-tuning job on qwen-turbo...")
job = client.fine_tuning.jobs.create(
    training_file=file_obj.id,
    model="qwen-turbo"
)

print(f"Fine-tuning job created successfully! Job ID: {job.id}")
print(f"Status: {job.status}")

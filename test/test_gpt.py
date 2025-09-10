# test_gpt.py
import os
from dotenv import load_dotenv, find_dotenv
import openai

# 1) Load environment
load_dotenv(find_dotenv())

# 2) Confirm key
print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))

# 3) Configure client
openai.api_key = os.getenv("OPENAI_API_KEY")

# 4) New‐style chat call
resp = openai.chat.completions.create(
    model="o4-mini",
    messages=[
      {"role":"system","content":"You are a helpful assistant."},
      {"role":"user","content":"Ping"}
    ]
)

# 5) Show reply
print("GPT replied:", resp.choices[0].message.content)

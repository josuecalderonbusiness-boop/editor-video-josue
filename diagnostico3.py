import subprocess, json

with open('editor_josue_v7.py', encoding='utf-8') as f:
    c = f.read()

OPENAI_KEY = c.split('OPENAI_API_KEY = "')[1].split('"')[0]
CLAUDE_KEY = c.split('CLAUDE_API_KEY = "')[1].split('"')[0]

print('OpenAI key:', OPENAI_KEY[:15] + '...')
print('Claude key:', CLAUDE_KEY[:15] + '...')
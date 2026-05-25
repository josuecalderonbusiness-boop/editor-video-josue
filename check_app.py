with open("app.py", "r", encoding="utf-8") as f:
    lineas = f.readlines()

# Mostrar contexto alrededor de las lineas 33-34
for i, l in enumerate(lineas[28:45], 29):
    print(f"{i}: {repr(l)}")

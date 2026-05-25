with open('editor_josue_v7_clean.py', 'r', encoding='utf-8') as f:
    contenido = f.read()

nueva_funcion = open('color_workshop.py', 'r', encoding='utf-8').read()

contenido = contenido.replace(
    'def convertir_916(entrada, salida):',
    nueva_funcion + '\ndef convertir_916(entrada, salida):'
)

contenido = contenido.replace(
    "parser.add_argument('--limpia-audio', action='store_true')",
    "parser.add_argument('--limpia-audio', action='store_true')\n    parser.add_argument('--color-workshop', action='store_true')"
)

contenido = contenido.replace(
    'limpia_audio=args.limpia_audio\n    )',
    'limpia_audio=args.limpia_audio,\n        color_workshop=getattr(args, \"color_workshop\", False)\n    )'
)

with open('editor_josue_v7_clean.py', 'w', encoding='utf-8') as f:
    f.write(contenido)

print('Listo.')

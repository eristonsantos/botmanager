from PIL import Image, ImageDraw, ImageFont

# Cria imagem 512x512 com canal ALPHA (RGBA)
img = Image.new('RGBA', (512, 512), color=(102, 126, 234, 255))

draw = ImageDraw.Draw(img)

# Adiciona texto "RPA"
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 150)
except:
    font = ImageFont.load_default()

text = "RPA"
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
position = ((512 - text_width) // 2, (512 - text_height) // 2 - 20)

# Texto branco
draw.text(position, text, fill=(255, 255, 255, 255), font=font)

# Salva como PNG RGBA
img.save('icon.png', 'PNG')
print("✅ Ícone RGBA criado: icon.png")

# Cria outros tamanhos
sizes = [(32, 32), (128, 128), (256, 256)]
for size in sizes:
    resized = img.resize(size, Image.Resampling.LANCZOS)
    filename = f'{size[0]}x{size[1]}.png'
    if size == (256, 256):
        filename = '128x128@2x.png'
    resized.save(filename, 'PNG')
    print(f"✅ Criado: {filename}")

# Para .ico (Windows)
img.save('icon.ico', format='ICO', sizes=[(32, 32), (64, 64), (128, 128), (256, 256)])
print("✅ Criado: icon.ico")

print("\n🎉 Todos os ícones criados com sucesso!")

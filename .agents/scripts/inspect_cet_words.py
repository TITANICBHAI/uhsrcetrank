from pathlib import Path
import fitz

path = Path('attached_assets/150926cetugresult_1789488607089.pdf')
doc = fitz.open(path)
for page_number in [0, 1, 338, 677]:
    page = doc.load_page(page_number)
    print(f'\n===== PAGE {page_number + 1} rect={page.rect} =====')
    words = page.get_text('words')
    for word in words[:180]:
        x0, y0, x1, y1, text, block, line, word_index = word
        print(f'x={x0:7.1f} y={y0:7.1f} text={text!r} b={block} l={line} w={word_index}')

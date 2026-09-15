from pathlib import Path
import fitz

pdf_path = Path('attached_assets/150926cetugresult_1789488607089.pdf')
out_dir = Path('.agents/outputs/cet_pdf_samples')
out_dir.mkdir(parents=True, exist_ok=True)

doc = fitz.open(pdf_path)
print('pages', doc.page_count)
print('metadata', doc.metadata)

sample_pages = sorted(set([0, 1, 2, 9, 49, 99, 199, 399, 599, doc.page_count - 2, doc.page_count - 1]))
with (out_dir / 'text_samples.txt').open('w', encoding='utf-8') as output:
    for page_number in sample_pages:
        page = doc.load_page(page_number)
        text = page.get_text('text')
        print(f'page {page_number + 1}: chars={len(text)} images={len(page.get_images(full=True))}')
        output.write(f'\n===== PAGE {page_number + 1} =====\n{text}\n')
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        pix.save(out_dir / f'page-{page_number + 1:04d}.png')

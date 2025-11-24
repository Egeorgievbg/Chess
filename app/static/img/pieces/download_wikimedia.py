"""
Download individual piece images from Wikimedia Commons in high quality.
Save as PNG files locally.
"""
import os
import urllib.request

# Mapping of piece code to Wikimedia filename
pieces = {
    'wK': 'https://upload.wikimedia.org/wikipedia/commons/f/f1/Chess_klt45.svg',
    'wQ': 'https://upload.wikimedia.org/wikipedia/commons/1/15/Chess_qlt45.svg',
    'wR': 'https://upload.wikimedia.org/wikipedia/commons/7/72/Chess_rlt45.svg',
    'wB': 'https://upload.wikimedia.org/wikipedia/commons/b/bf/Chess_blt45.svg',
    'wN': 'https://upload.wikimedia.org/wikipedia/commons/7/70/Chess_nlt45.svg',
    'wP': 'https://upload.wikimedia.org/wikipedia/commons/4/45/Chess_plt45.svg',
    'bK': 'https://upload.wikimedia.org/wikipedia/commons/6/6f/Chess_kdt45.svg',
    'bQ': 'https://upload.wikimedia.org/wikipedia/commons/4/47/Chess_qdt45.svg',
    'bR': 'https://upload.wikimedia.org/wikipedia/commons/f/ff/Chess_rdt45.svg',
    'bB': 'https://upload.wikimedia.org/wikipedia/commons/9/98/Chess_bdt45.svg',
    'bN': 'https://upload.wikimedia.org/wikipedia/commons/e/ef/Chess_ndt45.svg',
    'bP': 'https://upload.wikimedia.org/wikipedia/commons/c/c7/Chess_pdt45.svg',
}

out_dir = os.path.dirname(os.path.abspath(__file__))

def download_piece(code, url):
    filename = os.path.join(out_dir, f'{code.lower()}.svg')
    try:
        print(f'Downloading {code} from {url}...')
        urllib.request.urlretrieve(url, filename)
        print(f'✓ Saved {filename}')
    except Exception as e:
        print(f'✗ Error downloading {code}: {e}')

if __name__ == '__main__':
    for code, url in pieces.items():
        download_piece(code, url)
    print('All pieces downloaded!')

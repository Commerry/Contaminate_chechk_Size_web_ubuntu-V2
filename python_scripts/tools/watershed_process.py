import sys
import cv2
import numpy as np
from pathlib import Path
import json

def process_image(in_path, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(in_path))
    if img is None:
        print(f"ERROR: cannot read image: {in_path}")
        return 1

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    # CLAHE to enhance contrast
    try:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        gray_clahe = clahe.apply(blur)
    except Exception:
        gray_clahe = blur

    # Otsu threshold on inverted (assume objects lighter/darker depending)
    # Try both and pick the one with larger foreground area
    _, bw1 = cv2.threshold(gray_clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, bw2 = cv2.threshold(gray_clahe, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # choose variant with more foreground pixels
    fg1 = np.count_nonzero(bw1)
    fg2 = np.count_nonzero(bw2)
    bw = bw1 if fg1 > fg2 else bw2

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=2)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, iterations=1)

    # Distance transform and watershed markers
    dist = cv2.distanceTransform(cv2.bitwise_not(bw) if np.mean(bw)>127 else bw, cv2.DIST_L2, 5)
    dmax = dist.max() if dist.max()>0 else 1.0
    _, sure_fg = cv2.threshold(dist, 0.45 * dmax, 255, 0)
    sure_fg = np.uint8(sure_fg)
    sure_bg = cv2.dilate(bw, kernel, iterations=3)
    unknown = cv2.subtract(sure_bg, sure_fg)

    num_labels, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown==255] = 0

    img_mark = img.copy()
    try:
        markers = cv2.watershed(img_mark, markers)
    except Exception as e:
        print('watershed error:', e)

    # prepare masks
    binary_vis = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
    cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(gray)
    cv2.drawContours(filled, cnts, -1, 255, thickness=cv2.FILLED)
    filled_vis = cv2.cvtColor(filled, cv2.COLOR_GRAY2BGR)

    outline = np.zeros_like(gray)
    cv2.drawContours(outline, cnts, -1, 255, thickness=2)
    outline_vis = cv2.cvtColor(outline, cv2.COLOR_GRAY2BGR)

    # Annotate instances from markers
    annot = img.copy()
    instances = []
    for m in np.unique(markers):
        if m <= 1:
            continue
        mask = np.uint8(markers == m)
        cts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cts:
            continue
        c = max(cts, key=cv2.contourArea)
        area = cv2.contourArea(c)
        if area < 200:  # filter tiny
            continue
        x,y,w,h = cv2.boundingRect(c)
        cv2.rectangle(annot, (x,y), (x+w, y+h), (0,255,0), 2)
        cv2.putText(annot, f'{int(area)}px', (x, y-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
        instances.append({'label':int(m), 'bbox':[int(x),int(y),int(w),int(h)], 'area_px': float(area)})

    # Save outputs
    cv2.imwrite(str(out_dir / 'annotated.jpg'), annot)
    cv2.imwrite(str(out_dir / 'binary.jpg'), binary_vis)
    cv2.imwrite(str(out_dir / 'filled.jpg'), filled_vis)
    cv2.imwrite(str(out_dir / 'outline.jpg'), outline_vis)

    summary = {
        'input': str(in_path),
        'out_dir': str(out_dir),
        'instances_count': len(instances),
        'instances': instances
    }
    with open(out_dir / 'summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print('Done. instances:', len(instances))
    print('Saved to', out_dir)
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python watershed_process.py <image_path> [out_dir]')
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else r'd:\temp\watershed_out'
    sys.exit(process_image(inp, out))

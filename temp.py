import zipfile, xml.etree.ElementTree as ET
from pathlib import Path
path=Path(r"task_tracking/251201. SHG _ Website SH 2025 - Overview.xlsx")
ns={'main':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(path) as z:
    shared={}
    if 'xl/sharedStrings.xml' in z.namelist():
        root=ET.fromstring(z.read('xl/sharedStrings.xml'))
        for idx,si in enumerate(root.findall('main:si',ns)):
            text=[]
            for child in si:
                if child.tag.endswith('t'):
                    text.append(child.text or '')
                elif child.tag.endswith('r'):
                    t=child.find('main:t',ns)
                    text.append(t.text if t is not None else '')
            shared[idx]=''.join(text)
    def col_idx(ref):
        letters=''.join(filter(str.isalpha, ref))
        idx=0
        for ch in letters:
            idx=idx*26 + (ord(ch.upper())-64)
        return idx
    def dump_sheet(target, limit=40):
        sheet=ET.fromstring(z.read(target))
        rows=[]
        for row in sheet.findall('main:sheetData/main:row',ns):
            cells=[]
            for c in row.findall('main:c',ns):
                ref=c.get('r')
                v=c.find('main:v',ns)
                if v is None:
                    val=''
                else:
                    val=v.text or ''
                    if c.get('t')=='s':
                        val=shared.get(int(val), '')
                cells.append((col_idx(ref), val))
            cells.sort(key=lambda x:x[0])
            rows.append([val for _,val in cells])
        for row in rows[:limit]:
            print('\t'.join(row))
    dump_sheet('xl/worksheets/sheet5.xml')

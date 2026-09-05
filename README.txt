RANISAA ERP - BARCODE PRINT POSITION + TEMPLATE PRESERVATION UPDATE

ONLY BARCODE/MRP PRINTING AND TEMPLATE EDITOR HANDLING WERE UPDATED.
Existing database.py, repair.py and requirements.txt are unchanged.

1. MRP GENERATOR
- Existing party + invoice Load Purchase flow remains.
- MRP calculation and Save All MRP remain.

2. BARCODE GENERATOR
- Separate dashboard option.
- Same party + invoice Load Purchase flow.
- Barcode printing only; MRP save controls are hidden.

3. QTY LABEL LOGIC
- Each purchase row prints one label per piece/quantity.
- Example Qty 4 = 4 identical item labels.
- All rows in the loaded bill are included.

4. A4 POSITION MEMORY
- A4 = 24 labels (3 x 8), 64 x 34 mm each.
- The ERP stores the next physical sticker position in the database setting:
  barcode_next_position
- If 16 labels are printed starting at position 1, next print starts at 17.
- If printing continues past position 24, it automatically continues on the next A4 page.
- The saved position is updated after the print command is prepared.

5. TEMPLATE MEMORY
- The Canva-style Barcode Template Editor saves the template in the ERP database
  setting key: template_barcode
- The saved template is loaded automatically when the editor opens.
- The print renderer reads the saved template positions/visibility/rotation/font settings,
  so the user does not need to set the layout again.
- Business records are not stored in the template setting.

6. SAFETY
- Do not delete the existing data/ folder or database.
- The application update does not intentionally alter business records.

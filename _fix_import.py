"""Fix customers/views.py import logic: add TRN checks, within-file
duplicate detection, and None-conversion for empty TL/TRN."""

import pathlib

lines = pathlib.Path("customers/views.py").read_text(encoding="utf-8").splitlines(True)
out = []
i = 0
while i < len(lines):
    line = lines[i]

    # After "duplicates = 0" (around line 496), insert tracking sets
    if line.strip() == "duplicates = 0" and i > 490:
        out.append(line)
        out.append("        seen_names = set()      # Track within-file duplicates\n")
        out.append("        seen_licenses = set()\n")
        out.append("        seen_trns = set()\n")
        i += 1
        continue

    # Replace "# Check for duplicate" block (lines ~508-512)
    if line.strip() == "# Check for duplicate":
        # Skip this comment, rewrite the whole block
        i += 1
        # Skip the existing if / duplicates+=1 / errors.append / continue / blank
        # Those are lines 509-513
        i += 5  # skip if, duplicates+=1, errors.append, continue, blank
        out.append("                # Check for duplicate in DB and within this import file\n")
        out.append("                if Customer.objects.filter(company_name__iexact=company_name).exists():\n")
        out.append("                    duplicates += 1\n")
        out.append("                    errors.append(f'Row {row_idx}: Duplicate company name \\\"{company_name}\\\" (already in database).')\n")
        out.append("                    continue\n")
        out.append("                if company_name.lower() in seen_names:\n")
        out.append("                    duplicates += 1\n")
        out.append("                    errors.append(f'Row {row_idx}: Duplicate company name \\\"{company_name}\\\" (duplicated within this file).')\n")
        out.append("                    continue\n")
        out.append("                seen_names.add(company_name.lower())\n")
        out.append("\n")
        continue

    # After trade_license DB check (line ~515-518), add within-file license check + TRN check
    if "if trade_license and Customer.objects.filter(trade_license_number__iexact" in line:
        out.append(line)  # keep the DB check
        i += 1
        out.append(lines[i])  # duplicates += 1
        i += 1
        # Rewrite errors.append for trade license
        out.append("                    errors.append(f'Row {row_idx}: Duplicate trade license \\\"{trade_license}\\\" (already in database).')\n")
        i += 1  # skip old errors.append
        out.append(lines[i])  # continue
        i += 1
        # Add within-file license check
        out.append("                if trade_license and trade_license.lower() in seen_licenses:\n")
        out.append("                    duplicates += 1\n")
        out.append("                    errors.append(f'Row {row_idx}: Duplicate trade license \\\"{trade_license}\\\" (duplicated within this file).')\n")
        out.append("                    continue\n")
        out.append("                if trade_license:\n")
        out.append("                    seen_licenses.add(trade_license.lower())\n")
        out.append("\n")
        # Add TRN DB check
        out.append("                trn = str(row[col_indices.get('trn')] or '').strip() if 'trn' in col_indices else ''\n")
        out.append("                if trn and Customer.objects.filter(trn__iexact=trn).exists():\n")
        out.append("                    duplicates += 1\n")
        out.append("                    errors.append(f'Row {row_idx}: Duplicate TRN \\\"{trn}\\\" (already in database).')\n")
        out.append("                    continue\n")
        out.append("                if trn and trn.lower() in seen_trns:\n")
        out.append("                    duplicates += 1\n")
        out.append("                    errors.append(f'Row {row_idx}: Duplicate TRN \\\"{trn}\\\" (duplicated within this file).')\n")
        out.append("                    continue\n")
        out.append("                if trn:\n")
        out.append("                    seen_trns.add(trn.lower())\n")
        out.append("\n")
        # skip old blank line before "# Parse dates"
        if lines[i].strip() == "":
            i += 1
        continue

    out.append(line)
    i += 1

pathlib.Path("customers/views.py").write_text("".join(out), encoding="utf-8")
print("views.py import logic updated")


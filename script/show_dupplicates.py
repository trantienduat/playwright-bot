from collections import defaultdict
from pathlib import Path

def show_duplicates():
    kimtin_path = Path('data/vantoi/KIMTIN_list.txt')
    
    # Store entries by invoice number (without search code)
    entries = defaultdict(list)
    
    with open(kimtin_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Split by underscore and get everything except the last part (search code)
            invoice_key = '_'.join(line.split('_')[:-1])
            entries[invoice_key].append(line)

    # Filter and display only duplicates
    duplicates = {k: v for k, v in entries.items() if len(v) > 1}
    
    if not duplicates:
        print("✅ No duplicates found!")
        return
        
    print(f"Found {len(duplicates)} duplicated invoices:\n")
    
    for invoice_key, dupes in duplicates.items():
        print(f"\n🔍 {invoice_key}")
        for entry in dupes:
            print(f"   {entry}")

if __name__ == "__main__":
    show_duplicates()
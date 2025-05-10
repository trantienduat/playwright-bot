
# Fetching invoices from json files
echo ">>>>>>>>>>>>>> FETCHING INVOICES FOR February 2025 <<<<<<<<<<<<<<<"
python3 db.py fetch --input ./data/2025_Feb_invoices.json;
echo ""
echo ""

echo ">>>>>>>>>>>>>> FETCHING INVOICES FOR March 2025 <<<<<<<<<<<<<<<"
python3 db.py fetch --input ./data/2025_Mar_invoices.json;
echo ""
echo ""
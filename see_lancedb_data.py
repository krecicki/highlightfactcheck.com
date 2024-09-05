import lancedb
import os

# Connect to the database
db = lancedb.connect(os.path.dirname(os.path.abspath(__file__))+"/localdb")

# Open the table you want to inspect
table = db.open_table("facts_checked")

# Fetch all rows (be careful with this if you have a large dataset)
all_data = table.to_pandas()

# Print the data
print(all_data)

# Or, if you want to see just the first few rows:
print(all_data.head())
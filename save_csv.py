import os

def save_to_csv(csv_content, filename="/tmp/regatta_results.csv"):
    """Save formatted CSV data to a file."""
    with open(filename, "w", newline="", encoding="utf-8") as file:
        file.write(csv_content)
    return filename

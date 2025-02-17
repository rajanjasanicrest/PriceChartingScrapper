import os
import json
import openpyxl
import urllib.parse

def write_data_to_file(data, set_name, folder):
    try:
        print("Writing Data to Excel File.")
        wb = openpyxl.Workbook()
        ws = wb.active
        safe_set_name = set_name.replace("/", "").replace("\\", "").replace("?", "").replace("*", "").replace(':','')
        ws.title = safe_set_name
        
        # Define static headers with capitalization
        headers = [
            "Product Name", "Set Name", "Genre", "Card Number", "TCGPlayer ID", "PriceCharting ID",  "eBay id", "Ungraded Price", "Ungraded Volume", "Grade 7 Price", "Grade 7 Volume", "Grade 8 Price", "Grade 8 Volume", "Grade 9 Price", "Grade 9 Volume", "Grade 9.5 Price", "Grade 9.5 Volume", "PSA 10 Price", "PSA 10 Volume", "Release Date", "Publisher", "Print Run", "Notes", "Description", "Photo URLs"
            
        ]
        ws.append(headers)

        for card in data:
            if card:
                row = [           
                    card.get('product_name',''),
                    card.get('set',''),
                    card.get('genre',''),
                    card.get('card_number',''),
                    card.get('tcgplayer_id',''),
                    card.get('pricecharting_id',''),
                    card.get('epid',''),

                    card.get('ungraded_price',''),
                    card.get('volume_ungraded',''),
                    card.get('grade7_price',''),
                    card.get('volume_grade7',''),
                    card.get('grade8_price',''),
                    card.get('volume_grade8',''),
                    card.get('grade9_price',''),
                    card.get('volume_grade9',''),
                    card.get('grade95_price',''),
                    card.get('volume_grade95',''),
                    card.get('psa10_price',''),
                    card.get('volume_psa10',''),

                    card.get('release_date',''),
                    card.get('publisher',''),
                    card.get('print_run',''),
                    card.get('notes',''),
                    card.get('description',''),

                    ','.join(list(map(urllib.parse.urlencode, card.get('photos',[])))),

                ]

                ws.append(row)

        base_dir = "excels"

        # Ensure the target folder exists
        folder_path = os.path.join(base_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
    
        file_path = os.path.join(folder_path, f"{safe_set_name}.xlsx")

        wb.save(file_path)
        print(f"Data successfully written to {file_path}")
    
    except Exception as e:
        print(e)


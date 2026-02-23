import xml.etree.ElementTree as ET

class InventoryParserAgent:
    def __init__(self):
        self.descriptor = {
            "name": "SupplierXMLParser",
            "domain": "INVENTORY_MANAGEMENT"
        }

    def process_xml(self, filepath, gatekeeper):
        # The agent must check with gatekeeper if it's allowed to read specific domains (mocked tool check)
        if not gatekeeper.validate_action(self.descriptor, "read_supplier_xml"):
            return None
            
        print(f"📦 [SupplierXMLParser] Reading file: {filepath}")
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            extracted_data = []
            for item in root.findall('.//Item'):
                sku = item.get('SKU')
                price = float(item.find('Price').text)
                quantity = int(item.find('Quantity').text)
                
                extracted_data.append({
                    "sku": sku,
                    "new_price": price,
                    "new_stock": quantity
                })
                
            print(f"📦 [SupplierXMLParser] Successfully parsed {len(extracted_data)} items.")
            return extracted_data
        except Exception as e:
            print(f"Failed to parse XML: {e}")
            return None

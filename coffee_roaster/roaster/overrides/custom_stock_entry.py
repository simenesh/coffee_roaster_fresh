from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry

class CustomStockEntry(StockEntry):
    def validate(self):
        super().validate()
        # Auto‐link Roast Batch reference to batch_no on each item
        for item in self.items:
            if item.reference_type == "Roast Batch":
                item.batch_no = item.reference_name


class Validation:
    @staticmethod
    def validate_product_data(product_data):
        errors = []
        
        # Check if sale price is less than or equals to the original price
        original_price = product_data.get('price', 0)
        sale_prices = product_data.get('sale_prices', [])
        
        for sale_price in sale_prices:
            if sale_price > original_price:
                errors.append(f"Sale price {sale_price} is greater than original price {original_price}")

        # Check if mandatory fields are present
        mandatory_fields = ['title', 'product_id', 'price']
        for field in mandatory_fields:
            if not product_data.get(field):
                errors.append(f"Mandatory field '{field}' is missing")

        # Check if each variant has images and prices
        models = product_data.get('models', [])
        for model in models:
            variants = model.get('variants', [])
            if variants:  # Only validate variants if there are any
                for variant in variants:
                    if not variant.get('image'):
                        errors.append(f"Variant {variant.get('id')} is missing an image")
                    if not variant.get('price'):
                        errors.append(f"Variant {variant.get('id')} is missing a price")

        return errors

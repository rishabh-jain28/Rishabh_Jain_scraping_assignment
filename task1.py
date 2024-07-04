import requests
import re
from lxml import html
import json
from validation import validation
class BaseProductScraper:
    def __init__(self, url):
        self.url = url
        self.tree = None
    
    def fetch_page(self):
        response = requests.get(self.url)
        self.tree = html.fromstring(response.content)
    
    def extract_product_details(self):
        raise NotImplementedError("This method should be implemented by subclasses.")
    
    def save_to_json(self, data, filename):
        with open(filename, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        print(f"JSON data saved to {filename}")

class ForeignFortuneScraper(BaseProductScraper):
    name = "foreign_fortune"
    
    def _extract_meta_json(self, page_text):
        output = re.findall(r'var\s+meta\s*=\s*(\{.*?\});', page_text)
        return json.loads(output[0]) if output else {}
    
    def extract_product_details(self):
        self.fetch_page()
        meta_json = self._extract_meta_json(requests.get(self.url).text)
        
        title = self.tree.xpath('//meta[@property="og:title"]/@content')[0]
        url = self.tree.xpath('//meta[@property="og:url"]/@content')[0]
        description = self.tree.xpath('//meta[@property="og:description"]/@content')[0]
        price_amount = self.tree.xpath('//meta[@property="og:price:amount"]/@content')[0]
        price_currency = self.tree.xpath('//meta[@property="og:price:currency"]/@content')[0]
        image_url = self.tree.xpath('//meta[@property="og:image"]/@content')[0]
        images = self.tree.xpath("//img[@class='product-single__thumbnail-image']/@src")
        labels = self.tree.xpath("//label[contains(@for,'SingleOptionSelector')]/text()")
        
        brand = meta_json.get('product', {}).get('vendor')
        product_id = meta_json.get('product', {}).get('id')
        variants = meta_json.get('product', {}).get('variants', [])
        
        images = ["http:" + i for i in images]

        selected_variants = self._process_variants(variants, image_url, labels)
        
        data = {
            "brand": brand,
            "description": description,
            "image": image_url,
            "images": images,
            "models": [{"variants": selected_variants}],
            "price": float(price_amount),
            "prices": [float(price_amount)],
            "sale_prices": [float(price_amount)],
            "title": title,
            "url": url,
            "product_id": product_id
        }
        # Validate data
        errors = validation.Validation.validate_product_data(data)
        if errors:
            print("Validation Errors:")
            for error in errors:
                print(f" - {error}")
            return None
        else:
            return data

    def _process_variants(self, variants, image_url, labels):
        selected_variants = []
        
        for variant in variants:
            try:
                public_title = variant.get('public_title')
                if public_title:
                    public_title_parts = public_title.split("/")
                    variant_data = {
                        "id": variant['id'],
                        "image": image_url,
                        "price": float(variant['price']) / 100
                    }
                    for i in range(min(len(public_title_parts), len(labels))):
                        variant_data[labels[i].strip()] = public_title_parts[i].strip()

                    selected_variants.append(variant_data)
                else:
                    print(f"Skipping variant with id {variant['id']} because public_title is None or empty")
            except Exception as e:
                print(f"Error processing variant {variant['id']}: {e}")

        return selected_variants

class LeChocolatScraper(BaseProductScraper):
    name = "lechocolat"
    
    def extract_product_details(self):
        self.fetch_page()
        
        title = self.tree.xpath('//meta[@property="og:title"]/@content')[0]
        brand = self.tree.xpath('//meta[@property="og:site_name"]/@content')[0]
        url = self.tree.xpath('//meta[@property="og:url"]/@content')[0]
        description = self.tree.xpath('//meta[@property="og:description"]/@content')[0]
        price_amount = self.tree.xpath('//meta[@property="product:price:amount"]/@content')[0]
        price_currency = self.tree.xpath('//meta[@property="product:price:currency"]/@content')[0]
        image_url = self.tree.xpath('//meta[@property="og:image"]/@content')[0]
        output = re.findall(r'var\s+prestashop\s*=\s*(\{.*?\});', requests.get(self.url).text)
        meta_json = json.loads(output[0]) if output else {}
        product_id = re.findall(r"prodid = '(.*)';", requests.get(self.url).text)
        images = self.tree.xpath("//li[contains(@class,'productImages')]/a/@href")

        data =  {
            "brand": brand,
            "description": description,
            "image": image_url,
            "images": images,
            "price": float(price_amount),
            "prices": [float(price_amount)], 
            "sale_prices": [float(price_amount)],
            "title": title,
            "url": url,
            "product_id": product_id[0]
        }

        errors = validation.Validation.validate_product_data(data)
        if errors:
            print("Validation Errors:")
            for error in errors:
                print(f" - {error}")
            return None
        else:
            return data

class TraderJoesScraper(BaseProductScraper):
    name = "trader_joes"
    def extract_product_details(self):
        self.fetch_page()

        api_url = "https://www.traderjoes.com/api/graphql"
        sku = self.url.split('-')[-1]
        payload = json.dumps({
            "operationName": "SearchProduct",
            "variables": {
                "storeCode": "TJ",
                "published": "1",
                "sku": sku
            },
            "query": ("query SearchProduct($sku: String, $storeCode: String = \"TJ\", $published: String = \"1\") { "
                      "products(filter: {sku: {eq: $sku}, store_code: {eq: $storeCode}, published: {eq: $published}}) { "
                      "items { category_hierarchy { id url_key description name position level created_at updated_at product_count __typename } "
                      "item_story_marketing product_label fun_tags primary_image primary_image_meta { url metadata __typename } "
                      "other_images other_images_meta { url metadata __typename } context_image context_image_meta { url metadata __typename } "
                      "published sku url_key name item_description item_title item_characteristics item_story_qil use_and_demo sales_size "
                      "sales_uom_code sales_uom_description country_of_origin availability new_product promotion price_range { "
                      "minimum_price { final_price { currency value __typename } __typename } __typename } retail_price nutrition { "
                      "display_sequence panel_id panel_title serving_size calories_per_serving servings_per_container details { display_seq "
                      "nutritional_item amount percent_dv __typename } __typename } ingredients { display_sequence ingredient __typename } "
                      "allergens { display_sequence ingredient __typename } created_at first_published_date last_published_date updated_at "
                      "related_products { sku item_title primary_image primary_image_meta { url metadata __typename } price_range { "
                      "minimum_price { final_price { currency value __typename } __typename } __typename } retail_price sales_size "
                      "sales_uom_description category_hierarchy { id name __typename } __typename } __typename } total_count page_info { "
                      "current_page page_size total_pages __typename } __typename } }"
            )
        })
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.traderjoes.com',
            'priority': 'u=1, i',
            'referer': self.url,
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Brave";v="126"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        }

        response = requests.request("POST", api_url, headers=headers, data=payload)
        output_json = json.loads(response.text)

        title = output_json.get('data').get('products').get('items')[0].get('item_title')
        brand = self.tree.xpath('//meta[@property="og:site_name"]/@content')[0]
        url = self.url
        description = output_json.get('data').get('products').get('items')[0].get('item_story_qil')
        price_amount = output_json.get('data').get('products').get('items')[0].get('price_range').get('minimum_price').get('final_price').get('value')
        sale_price = output_json.get('data').get('products').get('items')[0].get('retail_price')
        image_url = "https://www.traderjoes.com" + output_json.get('data').get('products').get('items')[0].get('primary_image')
        product_id = output_json.get('data').get('products').get('items')[0].get('sku')
        image_links = output_json.get('data').get('products').get('items')[0].get('primary_image_meta').get('metadata')
        images = json.loads(image_links.replace('\\', ''))
        image_links = ["https://www.traderjoes.com{}".format(((i.get('src')).split('/jcr')[0])) for i in images.get('srcSet')]

        data = {
            "brand": brand,
            "description": description,
            "image": image_url,
            "images": image_links,
            "price": float(sale_price),
            "prices": [float(price_amount)],
            "sale_prices": [float(price_amount)],
            "title": title,
            "url": url,
            "product_id": product_id
        }
        errors = validation.Validation.validate_product_data(data)
        if errors:
            print("Validation Errors:")
            for error in errors:
                print(f" - {error}")
            return None
        else:
            return data

# Example usage:
foreign_fortune_url = "https://foreignfortune.com/collections/foreign-accesories/products/foreign-fortune-shades"
lechocolat_url = "https://www.lechocolat-alainducasse.com/uk/soveria-candied-fruit-citrus-trio#/52-size-250g"
trader_joes_url = "https://www.traderjoes.com/home/products/pdp/peach-raspberry-crisp-079424"

scrapers = [
    ForeignFortuneScraper(foreign_fortune_url),
    LeChocolatScraper(lechocolat_url),
    TraderJoesScraper(trader_joes_url)
]

for scraper in scrapers:
    product_details = scraper.extract_product_details()
    scraper.save_to_json(product_details, f'{scraper.name}_output.json')

import io
import boto3
import requests
import logging
from dotenv import load_dotenv
import urllib.parse
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_to_monthly(volume_text: str) -> float:
    """Convert volume text to annual sales number."""
    try:
        if not volume_text or volume_text.lower() == 'volume:':
            return 0
        
        volume_text = volume_text.lower()
        number = ''.join(filter(lambda x: x.isdigit() or x == '.', volume_text.split()[0]))
        
        if not number:
            return 0
            
        number = float(number)
        if 'per day' in volume_text:
            return number * 30
        elif 'per week' in volume_text:
            return number * 4
        elif 'per month' in volume_text:
            return number
        elif 'per year' in volume_text:
            return number / 12
        else:
            return 0
    except Exception as e:
        logger.warning(f"Error converting volume text '{volume_text}': {str(e)}")
        return 0
    

def get_volume_text(page, condition: str) -> str:
    """Get volume text for a specific condition using Playwright."""
    try:

        selector = f'.sales_volume td[data-show-tab="completed-auctions-{condition}"] a'
        element = page.wait_for_selector(selector, timeout=5000)
        if element:
            return element.inner_text()
        return "0"
    except Exception as e:
        logger.warning(f"Error getting volume text for condition {condition}: {str(e)}")
        return "0"


def scrape_card_details(card_uri, detail_page):
    try:

        url = f'https://www.pricecharting.com{card_uri}'
        print(f"scrapping game details for url: {url}")
        detail_page.goto(url)
        detail_page.wait_for_selector('h1.chart_title', timeout=60000)

        product_name = detail_page.locator('h1#product_name').evaluate("""
            (element) => {
                // Filter out text nodes and return their combined text
                return Array.from(element.childNodes)
                    .filter(node => node.nodeType === Node.TEXT_NODE) // Select only text nodes
                    .map(node => node.textContent.trim()) // Get text content and trim
                    .join(''); // Combine all text nodes
            }
            """)
        
        volume_ungraded = convert_to_monthly(get_volume_text(detail_page, 'used'))
        volume_grade7 = convert_to_monthly(get_volume_text(detail_page, 'cib'))
        volume_grade8 = convert_to_monthly(get_volume_text(detail_page, 'new'))
        volume_grade9 = convert_to_monthly(get_volume_text(detail_page, 'graded'))
        volume_grade95 = convert_to_monthly(get_volume_text(detail_page, 'box-only'))
        volume_psa10 = convert_to_monthly(get_volume_text(detail_page, 'manual-only'))
        AWS_PRICE_CHARTING_BUCKET = 'salient-price-charting'

        set = detail_page.locator('h1.chart_title a').inner_text().strip()

        selectors = {
            'ungraded_price': '#used_price .price',
            'grade7_price': '#complete_price .price',
            'grade8_price': '#new_price .price',
            'grade9_price': '#graded_price.tablet-portrait-hidden .price',
            'grade95_price': '#box_only_price.tablet-portrait-hidden .price',
            'psa10_price': '#manual_only_price.tablet-portrait-hidden .price',

            'genre': '#attribute td[itemprop="genre"]',
            'release_date': '#attribute td[itemprop="datePublished"]',
            'publisher': '#attribute td[itemprop="publisher"]',
            'print_run': '#attribute tr:has(td.title:text("Print Run")) td.details', 
            'notes': '#attribute tr:has(td.title:text("Notes")) td.details',
            'description': '#attribute td[itemprop="description"]', 
            'card_number': '#attribute td[itemprop="model-number"]',
            'tcgplayer_id': '#attribute tr:has(td.title:text("TCGPlayer ID")) td.details',
            'pricecharting_id': '#attribute tr:has(td.title:text("PriceCharting ID")) td.details',
            'epid': '#attribute tr:has(td.title:text("ePID (eBay)")) td.details',
        }

        details = {}
        for key, selector in selectors.items():
            try:
                element = detail_page.locator(selector)
                if element.is_visible():
                    details[key] = element.inner_text().replace('$', '').strip()
                    # print(key, details[key])
                else:
                    details[key] = ''
            except Exception as e:
                details[key] = ''


        try:
            photos_selector = '#extra-images .extra a'
            photo_urls = detail_page.locator(photos_selector).evaluate_all(
                'elements => elements.map(el => el.getAttribute("href"))'
            )

            for index, photo_url in enumerate(photo_urls):
                if photo_url:
                    # Download image from URL
                    try:
                        response = requests.get(photo_url)
                        if response.status_code == 200:
                            image_content = response.content
                            # Create S3 client
                            s3_client = boto3.client('s3')
                            # Clean up filenames
                            set_name = set.replace(' ', '_')

                            s3_name = product_name
                            s3_name = s3_name.replace(' ', '_')
                            
                            # Generate unique filename
                            filename = f'{set_name}/{product_name}/{s3_name}_{index}_{photo_url.split("/")[-1]}'
                            
                            # Upload to S3 using BytesIO
                            s3_client.upload_fileobj(
                                io.BytesIO(image_content),
                                AWS_PRICE_CHARTING_BUCKET,
                                filename,
                                ExtraArgs={
                                    'ContentType': f'image/{photo_url.split(".")[-1].lower()}',
                                }
                            )
                            # Update photo URL to S3 URL
                            s3_url = f"https://{AWS_PRICE_CHARTING_BUCKET}.s3.amazonaws.com/{urllib.parse.quote(filename)}"
                            photo_urls[index] = s3_url
                            print(s3_url)
                            print(f"Successfully uploaded {filename} to S3")
                        else:
                            print(f"Failed to download image from {photo_url}. Status code: {response.status_code}")
                            continue
                    except Exception as e:
                        logger.error(f"Error processing image {photo_url}: {str(e)}")
                        continue
        except Exception as e:

                logger.warning(f"Error getting photo URLs: {str(e)}")
                photo_urls = []


        product_details = {
            'product_name': product_name,
            'set': set,

            'volume_ungraded':volume_ungraded,
            'volume_grade7':volume_grade7,
            'volume_grade8':volume_grade8,
            'volume_grade9':volume_grade9,
            'volume_grade95':volume_grade95,
            'volume_psa10':volume_psa10,

            'ungraded_price': details['ungraded_price'],
            'grade7_price': details['grade7_price'],
            'grade8_price': details['grade8_price'],
            'grade9_price': details['grade9_price'],
            'grade95_price': details['grade95_price'],
            'psa10_price': details['psa10_price'],

            'genre': details['genre'],
            'release_date': details['release_date'],
            'publisher': details['publisher'],
            'print_run': details['print_run'],
            'notes': details['notes'],
            'description': details['description'],

            'card_number': details['card_number'],
            'tcgplayer_id': details['tcgplayer_id'],
            'pricecharting_id': details['pricecharting_id'],
            'epid': details['epid'],
            "photos": photo_urls,
        }

        return product_details
    except Exception as e:
        print(e)

import scrapy,json,os,platform,unicodedata
from lxml import etree
from crawldata.functions import *
from datetime import datetime
from lxml.etree import XMLSyntaxError

class CrawlerSpider(scrapy.Spider):
    name = 'sklep_korisiaki'
    DATE_CRAWL=datetime.now().strftime('%Y-%m-%d')
    #custom_settings={'LOG_FILE':'./log/'+name+'_'+DATE_CRAWL+'.log'}
    if platform.system()=='Linux':
        URL='file:////' + os.getcwd()+'/scrapy.cfg'
    else:
        URL='file:///' + os.getcwd()+'/scrapy.cfg'
    domain='https://sklep-kosiarki.pl/'
    # url='https://www.hochrather.at/ersatzteile'
    url='https://sklep-kosiarki.pl/1_index_sitemap.xml'
    item_count=0
    URLS=[]
    def start_requests(self):
        # yield scrapy.Request('https://sklep-kosiarki.pl/czesci-do-maszyn-i-urzadzen-wg-marki/john-deere/kosiarki-samojezdne/serii-332/przelaczniki-i-czujniki-elektryczne/stacyjka-7-pin-john-deere-ar58126-40611.html', callback=self.parse_data, dont_filter=True)
        yield scrapy.Request(self.url,callback=self.parse_sitemap,dont_filter=True)
    
    def parse_sitemap(self, response):
        root = etree.fromstring(response.body)
        urls = root.xpath('//sitemap:loc',
                          namespaces={'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'})
        
        for url in urls:
            if url != 'https://sklep-kosiarki.pl/1_pl_11_sitemap.xml':
                yield scrapy.Request(url.text, callback=self.parse_sub_sitemap, dont_filter=True)

    def parse_sub_sitemap(self, response):
        try:
            root = etree.fromstring(response.body)
            urls = root.xpath('//xmlns:loc', namespaces={'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'})

            self.item_count += len(urls)
            for url in urls:
                url_text = url.text
                if url_text:
                    yield scrapy.Request(url_text, callback=self.parse_data, dont_filter=True)

        except XMLSyntaxError as e:
            print(response.url)
        except Exception as e:
            print(response.url)

    def remove_prefix_if_pattern(self, s):
        if len(s) >= 4 and s[:3].isdigit() and s[3].isalpha():
            return s[4:]
        return s

    def remove_suffix_if_pattern(self, s):
        if len(s) >= 4 and s[-4:-1].isdigit() and s[-1].isalpha():
            return s[:-5]
        return s

    def parse_data(self,response):
        item={}

        item['availability'] = None
        item['base_image'] = None
        item['brand'] = None
        item['breadcrumb'] = None
        item['description'] = None
        item['gtin13'] = None
        item['name'] = None
        item['original_page_url'] = None
        item['original_language'] ='Polish'
        item['part_number'] = None
        item['price'] = None
        item['price_currency'] = None
        item['qty'] = None
        item['equivalent_part_numbers'] = None
        item['sku'] = None
        item['thumbnail_image'] = None
        item['reviews'] = []
        item['review_number'] = None

        part_number = response.xpath('//span[@itemprop="sku"]/text()').extract_first()
        if part_number:
            item['part_number'] = self.remove_prefix_if_pattern(part_number)
        else:
            return

        base_image = response.xpath('//div[@id="image-block"]//img/@src').extract_first()
        if base_image:
            item['base_image'] = response.urljoin(base_image)
            item['thumbnail_image'] = response.urljoin(base_image)
            item['small_image'] = response.urljoin(base_image)
        
        brand = response.xpath('//ol[@class="breadcrumb"]/li[position() > 1][last() - 1]/a/@title').extract_first()
        if not brand:
            brand = 'unbranded'
        else:
            brand = self.remove_suffix_if_pattern(brand)

        item['brand'] = brand
        breadcrumb_all = response.xpath('//ol[@class="breadcrumb"]//span/text()').getall()
        if breadcrumb_all:
            breadcrumb = " / ".join(breadcrumb_all)
            item['breadcrumb'] = breadcrumb

        descriptions = response.xpath('//h3[contains(., "Opis produktu")]/following-sibling::div[@class="rte"]//text()').getall()
        if descriptions:
            item['description'] = ''.join(descriptions)

        name = response.xpath('//ol[@class="breadcrumb"]/li[last()]/span/text()').get()
        if name:
            item['name'] = name.strip()

        item['original_page_url'] = response.url

        price = response.xpath('//span[@id="our_price_display"]/@content').extract_first()
        if price:
            item['price'] = float(price)

        price_currency = response.xpath('//meta[@itemprop="priceCurrency"]/@content').extract_first()
        if price_currency:
            item['price_currency'] = price_currency

        qty = response.xpath('//span[@id="quantityAvailable"]/text()').extract_first()
        if qty:
            item['qty'] = int(qty)

        if part_number and brand:
            part_number = re.sub(r'[^A-Za-z0-9]', '', item['part_number'])
            sku = f"{item['brand']}-{part_number}"
            sku = sku.lower().replace(' - ', '-')
            item['sku'] = sku.replace(' ', '-')
        
        gtin13 = response.xpath('//meta[@itemprop="gtin13"]/@content').get()
        if gtin13:
            item['gtin13'] = gtin13
        
        equivalent_part_numbers = response.xpath('//div[@id="short_description_content"]/text()').get()
        if equivalent_part_numbers:
            equivalent_part_numbers = equivalent_part_numbers.replace(' ', ',')
            equivalent_part_numbers = equivalent_part_numbers.replace(',,', ',')
            item['equivalent_part_numbers'] = equivalent_part_numbers

        review_number = response.xpath('//span[@itemprop="reviewCount"]/text()').get()
        if review_number:
            item['review_number'] = int(review_number)

        reviews_data = response.xpath('//div[@id="product_comments_block_tab"]/div[@itemprop="review"]')
        for review_data in reviews_data:
            it = {}
            author = review_data.xpath('.//meta[@itemprop="name"]/@content').get()
            rating = review_data.xpath('.//meta[@itemprop="ratingValue"]/@content').get()
            details = review_data.xpath('.//p[@itemprop="reviewBody"]//text()').get()
            date = review_data.xpath('.//meta[@itemprop="datePublished"]/@content').get()
            
            it['author'] = author
            it['rating'] = rating
            it['details'] = details
            it['date'] = date

            item['reviews'].append(it)
        
        availablity = response.xpath('//span[@id="availability_value"]/text()').get()
        if availablity:
            availablity = availablity.strip()
            if availablity:
                item['availability'] = availablity
        
        yield item

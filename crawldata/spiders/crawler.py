import scrapy,json,os,platform,unicodedata
from lxml import etree
from crawldata.functions import *
from datetime import datetime
from lxml.etree import XMLSyntaxError

class CrawlerSpider(scrapy.Spider):
    name = 'hochrather'
    DATE_CRAWL=datetime.now().strftime('%Y-%m-%d')
    #custom_settings={'LOG_FILE':'./log/'+name+'_'+DATE_CRAWL+'.log'}
    if platform.system()=='Linux':
        URL='file:////' + os.getcwd()+'/scrapy.cfg'
    else:
        URL='file:///' + os.getcwd()+'/scrapy.cfg'
    domain='https://www.hochrather.at'
    # url='https://www.hochrather.at/ersatzteile'
    url='https://www.hochrather.at/products_sitemap_index.xml'
    URLS=[]
    def start_requests(self):
        yield scrapy.Request(self.url,callback=self.parse_sitemap,dont_filter=True)
    
    def parse_sitemap(self, response):
        root = etree.fromstring(response.body)
        urls = root.xpath('//sitemap:loc',
                          namespaces={'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'})
        
        for url in urls:
            yield scrapy.Request(url.text, callback=self.parse_sub_sitemap, dont_filter=True)

    def parse_sub_sitemap(self, response):
        try:
            # Parse the XML content
            root = etree.fromstring(response.body)  # Use response.body for bytes

            # Extract URLs using the correct XPath and namespace
            urls = root.xpath('//xmlns:loc', namespaces={'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'})

            # Iterate through the extracted URLs
            for url in urls:
                url_text = url.text  # Get the text content of the URL element
                if url_text:  # Ensure the URL is not None or empty
                    yield scrapy.Request(url_text, callback=self.parse_data, dont_filter=True)

        except XMLSyntaxError as e:
            print(response.url)
        except Exception as e:
            print(response.url)

    def parse_data(self,response):
        ID=response.xpath('//div[contains(@id,"product-")]/@id').get()
        if ID:            
            title=response.xpath('//h1/text()').get()
            sku=response.xpath('//p[@class="sku"]/text()').get()
            item={}
            item['oem_quality']=0
            original=response.xpath('//span[@class="original"]')
            if original:
                item['oem_quality']=1
            img=response.xpath('//img[contains(@class,"embed-responsive-item")]/@src').get()
            if img:
                item['base_image']=img
                item['small_image']=str(item['base_image']).replace("-large.",".")
                item['thumbnail_image']=item['base_image']
            item['part_number']=str(sku).strip().split()[-1]
            item['name']=str(title).strip()

            item['brand'] = 'unbranded'
            brands = ['Amazone', 'Case', 'Granit', 'Horsch', 'Iseki', 'Kramp', 'Krone', 'Prillinger', 'Simtecx', 'Steyr']
            for brand in brands:
                if brand in item['name']:
                    item['brand'] = brand
                    break

            item['name']=str(title).strip()

            breadcrumb = response.xpath('//div[@id="breadcrumb"]/a[position() > 2]/text() | //span[@class="curr-bradcrumb"]/text()').getall()
            item['breadcrumb']=('/'.join(breadcrumb))
            item['original_page_url']=response.url
            item['sku']=item['brand']+'-'+item['part_number']
            item['qty']=response.xpath('//div[contains(@class,"entry-summary")]//input[@name="quantity"]/@value').get()
            # item['item_position']=response.meta['pos']
            item['original_id']=key_MD5(item['breadcrumb'])+'_'+ID

            item['price']=Get_Number(response.xpath('//div[@class="discount"]//bdi/text()').get())
            if not item['price']:
                item['price'] = 0.0

            item['discount_price']=Get_Number(response.xpath('//p[@class="price-with-discount"]//bdi/text()').get())
            if not item['discount_price']:
                item['discount_price'] = 0.0

            if not item['qty']:
                item['qty'] = 0

            currency=response.xpath('//div[@class="discount"]//span[@class="woocommerce-Price-currencySymbol"]/text()').get()
            if currency:
                if currency=='€':
                    currency='EUR'
                item['price_currency']=currency
            item['tech_spec']={}
            tecths=response.xpath('//div[contains(@id,"product-")]//div[contains(@class,"col-tech")]//table[@class="prop-table"]//tr')
            for rs in tecths:
                TXT=rs.xpath('./td[not(@title)]/text()').get()
                if TXT:
                    item['tech_spec'][rs.xpath('./td[@title]/@title').get()]=unicodedata.normalize("NFKD",rs.xpath('./td[not(@title)]/text()').get()).replace('\"', '')
            desc=[]
            spec=response.xpath('//div[contains(@id,"product-")]//div[contains(@class,"col-spec")]/div//text()').getall()
            for rs in spec:
                rs=str(rs).strip()
                if rs!='':
                    desc.append(rs)
            item['description']="; ".join(desc)
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0','Accept': '*/*','Accept-Language': 'en-US,en;q=0.5','Referer': response.url,'Connection': 'keep-alive','Sec-Fetch-Dest': 'empty','Sec-Fetch-Mode': 'cors','Sec-Fetch-Site': 'same-origin','Priority': 'u=4'}
            url='https://www.hochrather.at/wp-json/product/v1/get-product-terms?product_id='+str(ID).replace("product-","")
            yield scrapy.Request(url,callback=self.parse_fit,headers=headers,meta={'item':item},dont_filter=True)
        else:
            print(response.url)
    def parse_fit(self,response):
        item=response.meta['item']
        Data=json.loads(response.text)
        if len(Data['data'])>0:
            item['equipment_fit']=Data['data']
        yield(item)

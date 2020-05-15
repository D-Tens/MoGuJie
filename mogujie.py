'''
蘑菇街商品信息的爬取
https://www.mogu.com/
'''
from lxml import etree
from selenium.webdriver import Chrome, ChromeOptions
import requests
import re
import pymongo
import time
import json
import random
import hashlib
from config import *

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]
collec_mogu = db[COLLECTION_NAME]

headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36'
}
opt = ChromeOptions()
opt.headless = True
browser = Chrome(options=opt)


def request_html(url):
    response = requests.get(url, headers=headers)
    html = etree.HTML(response.text)
    return html


def kind_ls(html):
    shop_ls = html.xpath('//div[@class="item-wrap"]/div[1]/a[@class="cate-item-link"]/@href')[:-1]
    for shop_url in shop_ls:
        id = re.search('/(\d+)\?', shop_url).group(1)
        action = re.search('book/(.*?)/', shop_url).group(1)
        acm = re.search('acm=(.*)', shop_url).group(1)
        ls_url = 'https://list.mogu.com/search?'
        page = 1
        while True:
            params = {
                'callback': 'jQuery2110' + str("".join(random.choice("0123456789") for i in range(15))) + '_' + str(
                    int(time.time() * 1000)),
                '_version': '8193',
                'ratio': '3:4',
                'cKey': '15',
                'page': page,
                'sort': 'pop',
                'ad': '0',
                'fcid': id,
                'action': action,
                'acm': acm,
                'ptp': '31.v5mL0b.0.0.xDGHAVE3',
                '_': int(time.time() * 1000),
            }
            response = requests.get(ls_url, params=params, headers=headers)
            result = re.search('"result":(.*?),"success"', response.text).group(1)
            data = json.loads(result)
            # 判断
            judge = data['wall']['isEnd']
            if judge == False:
                page += 1
                # 商品数据
                s_ls = data['wall']['docs']
                for each in s_ls:
                    d_link = each['link']
                    yield d_link
                print('下一页', '-' * 20)
            else:
                break
        print('下一类', '=' * 20)


def detail_info(link):
    try:
        # hashlib.md5加密链接进行去重
        s_link = link.split('?')[0]
        s = hashlib.md5()
        s.update(s_link.encode('utf-8'))
        md5_link = s.hexdigest()
        img_ls = []
        browser.get(link)
        time.sleep(random.random())
        shopName=browser.find_element_by_css_selector('a.text.text-hasim').text
        title = browser.find_element_by_xpath('//span[@class="title small"]').text
        oldPrice = browser.find_element_by_id('J_OriginPrice').text
        newPrice = browser.find_element_by_id('J_NowPrice').text
        comment = browser.find_element_by_xpath('//dd[@class="property-extra fr"]/span[1]/span').text
        saleNum = browser.find_element_by_css_selector('span.num.J_SaleNum').text
        inventory = browser.find_element_by_css_selector('div.J_GoodsStock.goods-stock.fl').text
        enshrineNum = browser.find_element_by_css_selector('span.fav-num').text
        color = \
            browser.find_element_by_xpath(
                '//*[@id="J_ParameterTable"]/tbody//tr/td[contains(text(), "颜色")]').text.split(
                ':')[1]
        size = \
            browser.find_element_by_xpath(
                '//*[@id="J_ParameterTable"]/tbody//tr/td[contains(text(), "尺码")]').text.split(
                ':')[1]
        img_url = browser.find_elements_by_xpath('//*[@id="J_SmallImgs"]/div/div/ul//li')
        if img_url:
            for each in img_url:
                img = each.find_element_by_xpath('./img').get_attribute('src')
                img_ls.append(img)
            img_url = ' ,'.join(img_ls)
        else:
            img_url = browser.find_element_by_xpath('//img[@id="J_BigImg"]').get_attribute('src')
        return {
            'md5_link': md5_link,
            'shopName':shopName,
            'title': title,
            'oldPrice': oldPrice,
            'newPrice': newPrice,
            'comment': comment,
            'saleNum': saleNum,
            'inventory': inventory,
            'enshrineNum': enshrineNum,
            'color': color,
            'size': size,
            'img_url': img_url,
            'line': link
        }
    except Exception as e:
        print('错误信息:', e)


def save(data):
    if collec_mogu.update_one({
        'md5_link': data.get('md5_link')
    }, {
        '$set': data
    }, upsert=True):
        print('保存成功...', data)
    else:
        print('保存失败...')


def main():
    try:
        html = request_html(BASE_URL)
        detail_urls = kind_ls(html)
        for url in detail_urls:
            shop_info = detail_info(url)
            save(shop_info)
    finally:
        browser.close()


if __name__ == '__main__':
    main()

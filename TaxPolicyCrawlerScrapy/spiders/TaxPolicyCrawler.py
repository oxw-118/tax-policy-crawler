# coding=utf-8
import threading
import scrapy
from bs4 import BeautifulSoup
from TaxPolicyCrawlerScrapy.items import PolicyItem

# 国税总局，税收法规库的抓取
# http://hd.chinatax.gov.cn/guoshui/main.jsp
# 2017.9.8 共3531项查询结果236页

base_url = 'http://hd.chinatax.gov.cn/guoshui'


class TaxPolicyCrawler(scrapy.Spider):
    # 框架使用的属性
    name = 'TaxPolicyCrawler'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    def start_requests(self):
        yield scrapy.Request(base_url + '/main.jsp', method='GET', headers=self.headers, callback=self.parse_main)

    # 刷新了主页后的解析：获取了cookies，下一步抓取分页总数summary
    def parse_main(self, response):
        if not response:
            return

        print('获取分页信息：')
        form_data = 'articleField01=' \
                    '&articleField03=' \
                    '&articleField04=' \
                    '&articleField05=' \
                    '&articleField06=' \
                    '&articleField07_d=' \
                    '&articleField07_s=' \
                    '&articleField08=' \
                    '&articleField09=' \
                    '&articleField10=' \
                    '&articleField11=' \
                    '&articleField12=' \
                    '&articleField13=' \
                    '&articleField14=' \
                    '&articleField18=%E5%90%A6' \
                    '&articleRole=0000000' \
                    '&channelId=' \
                    '&intvalue=-1' \
                    '&intvalue1=4' \
                    '&rtoken=fgk' \
                    '&shuizhong=%E6%80%BB%E5%B1%80%E6%B3%95%E8%A7%84'

        yield scrapy.Request(base_url + '/action/InitNewArticle.do',
                             method='POST',
                             body=form_data,
                             headers=self.headers,
                             callback=self.parse_summary)

    # 刷新列表首页后的解析：获取分页数，然后根据分页抓取
    def parse_summary(self, response):
        page_count = parse_item_summary(response.body)
        print('page_count:' + str(page_count))

        if not page_count or page_count <= 0:
            print('获取税收法规库信息失败，可能被禁止权限了。。。')
            return

        for index in range(page_count):
            form_data = 'articleField01=' \
                        '&articleField03=' \
                        '&articleField04=' \
                        '&articleField05=' \
                        '&articleField06=' \
                        '&articleField07_d=' \
                        '&articleField07_s=' \
                        '&articleField08=' \
                        '&articleField09=' \
                        '&articleField10=' \
                        '&articleField11=' \
                        '&articleField12=' \
                        '&articleField13=' \
                        '&articleField14=' \
                        '&articleField18=%E5%90%A6' \
                        '&articleRole=0000000' \
                        '&intvalue=-1' \
                        '&intvalue1=4' \
                        '&intFlag=0' \
                        '&cPage=' + str(index + 1) + '' \
                        '&rtoken=fgk' \
                        '&shuizhong=%E6%80%BB%E5%B1%80%E6%B3%95%E8%A7%84'
            yield scrapy.Request(base_url + '/action/InitNewArticle.do',
                                 method='POST',
                                 headers=self.headers,
                                 body=form_data,
                                 callback=self.parse_list)

    # 刷新分页的列表后的解析：获取每项政策详情链接，然后抓取详情
    def parse_list(self, response):
        item_list = parse_item_list(response.body)

        if not item_list:
            return

        for item in item_list:
            url = item.get('url')
            print(threading.current_thread().name + ',抓取网页：' + url)
            if url is None:
                continue
            yield scrapy.Request(base_url + url[2:],
                                 method='GET',
                                 headers=self.headers,
                                 meta={'policy_item': item})

    # 默认解析器，在Request没有填写callback时调用：解析最后的详情，并发送到items及pipelines
    def parse(self, response):
        # TODO: cookiejar
        yield get_policy_detail(response.body, response.meta['policy_item'])


# 解析分页总数
def parse_item_summary(page_text):
    soup = BeautifulSoup(page_text, "lxml")
    all_table_tags = soup.find_all('table')

    if not all_table_tags:
        return

    for tableTag in all_table_tags:
        tr_tags = tableTag.find_all('tr')

        if not tr_tags:
            continue

        page_size = get_page_size(tr_tags[0])  # 从第一个tr里分析页数
        if page_size >= 0:
            return page_size
    return 0


# 获取政策列表（分页）
def get_page_size(tr_tag):
    td_str = get_text_in_tr(tr_tag, 0)  # 获取第一个节点的字符串
    start = td_str.find('页 1/')

    if start < 0:
        return start

    start += len('页 1/')
    end = td_str.find(' ', start)

    return int(td_str[start: end])


# 解析每页里的详情标题、链接
def parse_item_list(page_text):
    soup = BeautifulSoup(page_text, "lxml")
    target_table = soup.find('table', {'cellspacing': "1"})

    if not target_table:
        return []

    tr_tags = target_table.find_all('tr')

    if not tr_tags:
        return []

    policy_list = []
    for tr in tr_tags:
        all_tds = tr.find_all('td')
        if len(all_tds) <= 0:
            continue

        a_tag = all_tds[0].find('a')
        if not a_tag:
            continue

        policy_list.append(PolicyItem(title=a_tag.text,
                                      url=a_tag.attrs['href'],
                                      subtitle=all_tds[2].text,
                                      date=all_tds[1].text))

    return policy_list


# 根据链接爬取详情
def get_policy_detail(page_text, item):
    if not item or not item.get('url'):
        return

    # 获取详情页
    soup = BeautifulSoup(page_text, "lxml")
    all_table_tags = soup.find_all('tbody')
    if not all_table_tags or len(all_table_tags) < 3:
        return

    # 找到td
    target_td = all_table_tags[2].find('td')

    # 所有内容的<p>节
    content_p_list = target_td.find_all('p')
    item['content'] = ''
    for p in content_p_list:
        item['content'] += '\n<br>\n'
        item['content'] += p.text

    # 签名的<p>节
    publisher_p_list = target_td.find_all('p', style=True)
    item['publisher'] = ''
    for p in publisher_p_list:
        item['publisher'] += '\n<br>\n'
        item['publisher'] += p.text

    return item


# 从table的tr节里，获取文案
def get_text_in_tr(tr_tag, index):
    all_tds = tr_tag.find_all('td')
    if len(all_tds) <= index:
        return ''

    td_str = all_tds[index]

    return td_str.text


#
#
# # 结果输出到Excel
# def save_to_excel(policy_source, start_index, item_list):
#     filename = 'TaxPolicy.xls'
#     sheet_name = '税收政策'
#     is_reset = start_index == 0
#     # 先删除目标文件
#     if os.path.exists(filename) and is_reset:
#         os.remove(filename)
#
#     if os.path.exists(filename):
#         # 打开Excel
#         rdbook = xlrd.open_workbook(filename)
#         book = copy(rdbook)
#         excel_sheet = book.get_sheet(0)
#     else:
#         # 生成导出文件
#         book = xlwt.Workbook()
#         excel_sheet = book.add_sheet(sheet_name)
#
#     # 标题行
#     if is_reset:
#         excel_sheet.write(0, 0, '序号')
#         excel_sheet.write(0, 1, '政策来源')
#         excel_sheet.write(0, 2, '政策类型')
#         excel_sheet.write(0, 3, '税种')
#         excel_sheet.write(0, 4, '标题')
#         excel_sheet.write(0, 5, '副标题')
#         excel_sheet.write(0, 6, '链接地址')
#         excel_sheet.write(0, 7, '发文日期')
#         excel_sheet.write(0, 8, '正文内容')
#         excel_sheet.write(0, 9, '发文部门')
#
#     for i in range(1, len(item_list) + 1):
#         row_item = item_list[i - 1]
#         excel_sheet.write(start_index + i, 0, start_index + i)
#         excel_sheet.write(start_index + i, 1, policy_source.source)
#         excel_sheet.write(start_index + i, 2, policy_source.policyType)
#         excel_sheet.write(start_index + i, 3, policy_source.taxLevel)
#
#         excel_sheet.write(start_index + i, 4, row_item.title)
#         excel_sheet.write(start_index + i, 5, row_item.subtitle)
#         excel_sheet.write(start_index + i, 6, row_item.url)
#         excel_sheet.write(start_index + i, 7, row_item.date)
#         excel_sheet.write(start_index + i, 8, row_item.content)
#         excel_sheet.write(start_index + i, 9, row_item.publisher)
#
#     book.save(filename)
#
#
# def crawl_by_page(index, page_size):
#     try:
#         start_time = time.time()
#         policy_source = PolicySource('国税总局', '税收法规库', '')
#         request_util = get_request_util()  # 每页分开刷：不同代理、不同线程、重试单元
#         print(threading.current_thread().name + ',获取第' + str(index + 1) + '/' + str(page_size) + '页的列表数据')
#         item_list = get_item_list(request_util, str(index + 1))  # 网站url从1开始
#
#         if not item_list:
#             return False
#
#         policy_list_page = []
#         for item in item_list:
#             print(threading.current_thread().name + ',抓取网页：' + item.url)
#             policy_list_page.append(get_policy_detail(request_util, item))
#             # 不能频率太快，否则会被禁止访问, 随机延迟1~3秒
#             time.sleep((1 + random.random() * 2))
#
#         # saveToExcel(policy_source, start_index, policy_list_page)
#         # start_index += len(policy_list_page)
#         save_to_excel(policy_source, index * 20 + 1, policy_list_page)
#         print('finish crawling page ' + str(index) + '! take time:' + str(time.time() - start_time))
#         return True
#
#     except Exception as ex:
#         print('crawl_by_page generated an exception: %s' % str(ex))
#         return False
#
#
# def start_crawl():
#     page_count = get_item_summary()
#     print('page_size:' + str(page_count))
#
#     if not page_count or page_count <= 0:
#         print('获取税收法规库信息失败，可能被禁止权限了。。。')
#         return
#
#     # 测试一页
#     # page_count = 5
#
#     start_time = time.time()
#     # 每页分开刷：不同代理、不同线程、重试单元
#     page_index_to_crawl = [i for i in range(page_count)]
#     with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
#         round_times = 1
#         while len(page_index_to_crawl) > 0:
#             print('crawl for %d th round' % round_times)
#             future_to_crawl = {executor.submit(crawl_by_page, index, page_count): index for index in
#                                page_index_to_crawl}
#             for future in concurrent.futures.as_completed(future_to_crawl):
#                 index = future_to_crawl[future]
#                 try:
#                     data = future.result()
#                     if data:
#                         page_index_to_crawl.remove(index)
#                 except Exception as exc:
#                     print('page %d crawl failed! %s' % (index, str(exc)))
#             round_times += 1
#         print('all complete! take time:' + str(time.time() - start_time))
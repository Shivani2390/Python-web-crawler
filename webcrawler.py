# Program to build a focused crawler in Python.
# Input - search query and total number pages to be crawled.
# Output - the Crawler Output folder containing all the downloaded pages and Crawler Log file containing the URLs that were crawled and the details pertaining to each URL.
# Assumptions - the machine running the code supports multi-threading.

# Author - Shivani Gupta and Anusha Gupta.
# CS 6913.1195 - Assignment 1
# Date 2/21/2014.

#importing all the necessary libraries
import urllib, urllib2
import threading
import robotparser
import htmllib, formatter
import math
from bs4 import BeautifulSoup
import mimetypes
import threading
import os, datetime
from urlparse import urljoin

#defining global variables 
errors = {}
unimportantWords = [" a", " an", " the", " if", " else", " by", " of", " off", " on", " into", " onto", " unto", " is", " then", " beneath", " below", " as", " at", " before", " in", " inside" , " until", " unlike", " with", " within" , " without", "!", ",", "/", "?", ".", "'", "'"]
ignoredMimeTypeList = ["image/mng", "image/bmp", "image/gif", "image/jpg", "image/jpeg", "image/png", "image/pst", "image/psp", "image/fif", "image/tiff", "image/ai", "image/drw", "image/x-dwg", "audio/mp3", "audio/wma" ,"audio/mpeg", "audio/wav", "audio/midi", "audio/mpeg3", "audio/mp4", "audio/x-realaudio", "video/3gp", "video/avi", "video/mov", "video/mp4", "video/mpg", "video/mpeg", "video/wmv", "text/css", "application/x-pointplus", "application/pdf", "application/octet-stream", "application/x-binary", "application/zip"]

'''
data structures used - 
linksToParse queue stores [pagescore, url]
parsedLinks dictionary stores url = [[linksFound], score, len, time]
'''

# Class for keeping a track of the number of pages crawled.
class PageCounter():
	def __init__(self):
		self.lock = threading.Lock()
		self.pageNo = 0
	def increment(self):
		self.lock.acquire()
		page = self.pageNo
		self.pageNo += 1
		self.lock.release()
	def getPageNum(self):
		return self.pageNo

pageC = PageCounter() 

# Class to perform multi threaded crawling
class myThread(threading.Thread):
	def __init__(self, linksToParse, parsedLinks, query, pages):
		#initializing all the thread attributes
		threading.Thread.__init__(self)
		self.linksToParse = linksToParse
		self.parsedLinks = parsedLinks
		self.query = query
		self.stoprequest = threading.Event()
		self.pages = pages
	def join(self, timeout = None):
		super(myThread, self).join(timeout)
	def run(self):
		item = self.linksToParse.dequeue() 	# get the first item from the queue for processing. item - [pagescorescore,url]
		#print self.linksToParse.getSize()
		#print item 
		url = item[1]
		htmlText, links = readPage(url)	#read the HTML content of the URL.
		while (htmlText, links) == None:
			item = self.linksToParse.dequeue()
			url = item[1]
			htmlText, links = readPage(url)
		
		pageC.increment()	#increment the page counter
		writeInFile(htmlText, pageC.getPageNum())	#downloading the HTML file content.
		self.parsedLinks.addItem(url, links, item[0], len(htmlText), str(datetime.datetime.now().time()))	# adding the crawled URL and details into the dictionary.
		#print self.parsedLinks.display()
		#print "Pages " + str(pageC.getPageNum())
		for index in range(0, len(links)): 	#adding all the links present on the URL to the queue.
			#print "Going in again"
			id = self.linksToParse.find(links[index])	# check if the link is already present in the queue
			#print "ID found " + str(id)
			if id != -1:
				#print "Found"
				self.linksToParse.updateQueue(id, item[0]) 	# if present update the queue.
			else:
				#print self.linksToParse.getSize()
				#print "Not Found"
				canBeCrawled = checkIfWebsiteCrawlable(links[index])	#else check for the validity of the link and add to queue
				isCorrect = checkCorrectPage(links[index])
				#print str(url) + ' ' + str(notDoneAlready)
				if checkIfWebsiteCrawlable(links[index]) and checkCorrectPage(links[index]) and (not self.parsedLinks.find(links[index])):
				#	print "Checking again"
					page = readHTML(url)
					if page != None:
						score = findScore(page, self.query, item[0])
						newItem = [score, links[index]]
						#print newItem
						self.linksToParse.enqueue(newItem)
						#print self.linksToParse.getSize()
						#print index
					else:
						print "Page is None"
				#print "Thread count " + str(threading.active_count())
	
# Class to implement priority queue used for storing the [pagescore,url]
class PriorityQueue():

    def __init__(self):
    	self.condition = threading.Condition()
        self.queue = []

	# find the index at which the new item will be stored. Searching algorithm for index used is binary search.
    def __calculateIndex(self, item, start, end):
    	if len(self.queue) > 0:
    		if start < end:
    			index = int((start + end)/2)
    			#print self.queue[index]
    			#print index
        		if item[0] > self.queue[index][0]:
        			return self.__calculateIndex(item, start, index - 1)
        		elif item[0] < self.queue[index][0]:
        			return self.__calculateIndex(item, index + 1, end)
        		elif item[0] == self.queue[index][0]:
        			return index
    		elif start == end:
    			if end != len(self.queue):
    				if item[0] > self.queue[start][0]:
    					return start
    				else:
    					return start + 1
    			else:
    				if item[0] < self.queue[end-1][0]:
    					return end
    				else:
    					return end - 1
    		else:
    			return start
    	else:
    		#print start
    		return start
			
    #display the contents of the queue. 
    def displayQueue(self):
    	print "Displaying Queue"
    	for item in self.queue:
    		print item 		
			
    #add an item to the queue - enqueue
    def enqueue(self, item):
    	#print item
    	self.condition.acquire(True)
    	#print "Acquired In Enqueue"
    	if item not in self.queue:
    		index = self.__calculateIndex(item, 0, len(self.queue))
    		self.queue.insert(index, item)
    	self.condition.notifyAll()
    	self.condition.release()
    	#print len(self.queue)
    	#print "Released in enqueue"
   
	#pop an item from the queue - dequeue
    def dequeue(self):
    	#print len(self.queue)
    	self.condition.acquire(True)
    	#print "Acquired in dequeue"
    	while len(self.queue) <= 0:
    		self.condition.wait()
    		#print "Waiting"
        item = self.queue[0]
        del self.queue[0]
        #print "Dequeued"
        self.condition.release()
        #print "Released in dequeue"
        print item
        return item
    #Returns the size of the queue		
    def getSize(self):
    	return len(self.queue)
    	
	# delete the item from the queue.
    def delete(self, index):
    	self.condition.acquire(True)
    	item = self.queue[index]
    	del self.queue[index]
    	self.condition.release()
    	return item
    	
	#find an element in the queue.
    def find(self, url):
    	ind = -1
    	self.condition.acquire(True)
    	for index in range(len(self.queue)):
    		if self.queue[index][1] == url:
    			ind = index
    	self.condition.release()
    	return ind
    	
	'''update the score of the url link in the queue if its found when parsing other page. 
	It deletes that particular item in the queue. Updates the score of the page. And then
	add it again to the queue. 
	'''
    def updateQueue(self, index, score):
    	print index 
    	self.condition.acquire()
    	item = self.queue[index]
    	del self.queue[index]
    	item[0] += 0.5 * score
    	index = self.__calculateIndex(item, 0, len(self.queue))
    	self.queue.insert(index, item)
    	self.condition.notifyAll()
    	self.condition.release()
    	#print "Updated " + str(len(self.queue))
    	
''' Class to implement the functionalities of the dictionary data structure that stores 
key=value pair of url = [[linksFound], score, len, time]. The dictionary stores all the links
that have been parsed by the crawler. 

'''
class ParsedLinks():
	def __init__(self):
		self.lock = threading.Lock()
		self.parsedLinks = {}
	def addItem(self, url, linksFound, score, len, time):	#add an item into the dictionary after crawling
		self.lock.acquire()
		self.parsedLinks[url] = [linksFound, score, len, time]
		self.lock.release()
	def find(self, url): 	# find to check if item already exists.
		return self.parsedLinks.has_key(url)
	def display(self):	#display only the keys of the dictionary i.e. URLs.
		print self.parsedLinks.keys()
	def getKeys(self):	#return all the keys of the dictionary.
		return self.parsedLinks.keys()
	def getItem(self, key):	# return the number of linksFound, the score, size of the page, timestamp
		return len(self.parsedLinks[key][0]), self.parsedLinks[key][1], self.parsedLinks[key][2], self.parsedLinks[key][3] 

''' class to parse the HTML content of the page and extract all the links from the page.
'''
class Parser(htmllib.HTMLParser):
	def __init__(self, formatter):
		htmllib.HTMLParser.__init__(self, formatter) 
		self.links = []
	
	def start_frame(self, attrs):
		if len(attrs) > 0:
			for attr in attrs:
				if attr[0] == "src":
					self.links.append(attr[1])
	def start_a(self, attrs):
		if len(attrs) > 0:
			for attr in attrs:
				if attr[0] == "href" :         
					self.links.append(attr[1])
	def get_links(self):
		return self.links

''' writing the final dictionary contents and a few statistics to the file - CrawlerLog.txt
'''
def writeStatistics(parsedLinks):
	#print "Creating file"
	total_size = 0
	fileName = "CrawlerLog.txt"
	fileWriter = open(fileName, 'w')
	fileWriter.write("URL \t\t LinksSize \t\t Pagescore \t\t Pagelen \t\t timeWhenfeteched\n")
	for key in parsedLinks.getKeys():
		linksSize, score, len, time = parsedLinks.getItem(key)
		fileWriter.write(key + ' \t\t' + str(linksSize) + ' \t\t' + str(score) + ' \t\t' + str(len) + ' \t\t' + str(time) + '\n')
		total_size += len
	for key,value in errors:
		fileWriter.write("Errorcode" + str(key) + ' ' + str(value) + '\n')
	fileWriter.write('Total size of the pages that were downloaded is : ' + str(total_size))
	fileWriter.close()
		
'''Uses google search engine to find out the results for user query. 
The top 10 results are added to a list and that list is returned.
'''
def google_scrape(query):
    address = "http://www.google.com/search?q=%s&num=100&hl=en&start=0" % (urllib.quote_plus(query))
    request = urllib2.Request(address, None, {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11'})
    urlfile = urllib2.urlopen(request)
    page = urlfile.read()
    soup = BeautifulSoup(page)
    links = []
    count = 0
    li = soup.findAll('li', attrs={'class':'g'})
    while count < 10:
        sLink = li[count].find('a')
       # print sLink['href']
        links.append(sLink['href']) 
    	count += 1
    return links
''' Removing stop words from the search query entered by the user. 
Returns the changedQuery which contains only the important words.'''
def refineQuery(query):
	changedQuery = query
	for word in unimportantWords:
		if word in query:
			changedQuery = changedQuery.replace(word, "")
	return changedQuery
			
			
'''findScore provides the score/ priority to a particular page. 
The score of a page depends upon how many times a word from the changedQuery 
appears in the page and the score of the parent page. Score = no of words found pertaining 
to query/ no words in page.
'''
def findScore(page, query, parentScore):
	changedQuery = refineQuery(query)
	count = 0
	totalCount = 0
	for pagWord in page:
		totalCount += 1	
	for word in changedQuery:
		for pageWord in page:
			if pageWord == word:
				count += 1
	score = float(count)/totalCount + 0.5 * parentScore
	#print score
	return score		

''' normalize broken or incomplete links using urljoin(). url is the domain name for the links.
'''
def setLink(links, url):
	for i in range(len(links)):
		links[i] = urljoin(url, links[i])
		
''' implements the Robot exclusion protocol. 
checks if the robots.txt file is present and returns whether the page is crawlable.
If file (robots.txt) is not found then return True.
'''
def checkIfWebsiteCrawlable(url):
	try:
		rp = robotparser.RobotFileParser()
		url += "/robots.txt"
		rp.set_url(url)
		rp.read()
		return(rp.can_fetch("*",url))
	except IOError:
		pass
		#print "NO robots exclusion file found"
	return True

''' checks the mime type of the page to make sure that only correct pages are being crawled against the
 ignoredMimeTypeList. If mime is None then checks for the content type of the file using the info() method 
 of urllib.urlopen()'''
def checkCorrectPage(url):
    type = mimetypes.guess_type(url)
    if type == None:
    	response = urllib.urlopen(url).info()
    	strResponse = str(response)
    	ind1 = strResponse.find('Content-Type:')
    	ind2 = strResponse.find(' ', ind1)
    	ind3 = strResponse.find(';', ind1)
    	strResponse = strResponse[ind2:ind3].strip()
    	if strResponse not in ignoredMimeTypeList:
    		return True
    if type not in ignoredMimeTypeList:
        return True
    return False

# gather the required input from the user.
def getUserData():
    query = raw_input("Enter your search query\n")
    pages = raw_input("Enter the no of pages you want\n")
    return query, pages

# writing out the HTML content of the page into the file system.
def writeInFile(htmlText, pageNo):
    fileName = "Crawler output/HTMLPage" + str(pageNo)
    fileWriter = open(fileName, 'w')
    fileWriter.write(htmlText)
    fileWriter.close()

# reading the HTML content of the page. If the page can't be read due to specific errors then page is ignored.
def readHTML(url):
	try:
		page = urllib.urlopen(url)
		htmlText = page.read()
		return htmlText
	except IOError, errorcode:
		print errorcode
		if errors.has_key(errorcode):
			errors[errorcode] += 1
		else:
			errors[errorcode] = 1
	return None
	
'''read the HTML contents of the page and parse it to find all the links present on the page. 
Returns the HTML text and the links found on the page.
'''
def readPage(url):
	format = formatter.NullFormatter()
	htmlparser = Parser(format)
	htmlText = readHTML(url)
	if htmlText != None:
		htmlparser.feed(htmlText)
		links = htmlparser.get_links()	#get the links
		#print links
		setLink(links, url)	#normalize the links
		#print htmlText
		#print htmlparser.get_links()
		htmlparser.close()
		return htmlText, links	
	return None, None	#return None if the page is blank.
		
	
def main():
	parsedLinks = ParsedLinks()			#dictionary data structure.
	linksToParse = PriorityQueue()		#priority queue.
	query, pages = getUserData()		#user input
	changedQuery = refineQuery(query)	#changed / refined search query
	links = google_scrape(changedQuery) # top 10 links from Google.
	#print links
	os.mkdir("Crawler output")			#creating an output directory.
	for index in range(len(links)):		# for the top 10 links parse the HTMl content and return the score and links, add this to the priority queue.
		isCrawlable = checkIfWebsiteCrawlable(links[index])
		isCorrect = checkCorrectPage(links[index])
		#print isCrawlable 
		#print isCorrect
		if isCrawlable and isCorrect:
			page = readHTML(links[index])
			if page != None:
				score = findScore(page, changedQuery, 0)
				item = [score, links[index]]
				#print item
				linksToParse.enqueue(item)
	linksToParse.displayQueue()
	threads = []
	
	for i in range(int(pages)):			# creating threads for faster processing (crawling).
		threads.append(myThread(linksToParse, parsedLinks, changedQuery, pages))
		threads[i].daemon = True
		threads[i].start()
		
	while True:
		if pageC.getPageNum() == int(pages):	# termination condition is when we have crawled the number of pages input by the user.
			writeStatistics(parsedLinks)		# write the statistics in the 'Crawler Log' file.
			print errors
			break
			
main()
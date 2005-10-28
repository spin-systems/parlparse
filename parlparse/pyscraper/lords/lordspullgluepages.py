#! /usr/bin/python2.3
# vim:sw=8:ts=8:et:nowrap

import sys
import urllib
import urlparse
import re
import os.path
import xml.sax
import time
import string
import tempfile

import miscfuncs
toppath = miscfuncs.toppath
pwcmdirs = miscfuncs.pwcmdirs
tempfilename = miscfuncs.tempfilename

from miscfuncs import NextAlphaString, AlphaStringToOrder

# Pulls in all the debates, written answers, etc, glues them together, removes comments,
# and stores them on the disk

# we should put lordspages into cmpages as another directory, and move
# all patch files into a set of directories parallel to the html and xml containing directories


# index file which is created
pwlordsindex = os.path.join(toppath, "lordindex.xml")

# output directories (everything of one day in one file).
pwlordspages = os.path.join(pwcmdirs, "lordspages")


# this does the main loading and gluing of the initial day debate
# files from which everything else feeds forward

# gets the index file which we use to go through the pages
class LoadLordsIndex(xml.sax.handler.ContentHandler):
	def __init__(self, lpwcmindex):
		self.res = []
		if not os.path.isfile(lpwcmindex):
			return
		parser = xml.sax.make_parser()
		parser.setContentHandler(self)
		parser.parse(lpwcmindex)

	def startElement(self, name, attr):
		if name == "lordsdaydeb":
			ddr = (attr["date"], attr["url"], int(attr["type"]))
			if self.res and self.res[-1][0] == ddr[0]:
				if self.res[-1][2] > ddr[2]:
					return
				self.res.pop()
			self.res.append(ddr)

# extract the table of contents from an index page
def ExtractIndexContents(urlx):
	urx = urllib.urlopen(urlx)

	# find the contents label which is a reliable way to get to the first link in after the stack of intro
	stcont = '<a name="contents"></a>\s*$'
	while True:
		xline = urx.readline()
		if not xline:
			print '%s not found in %s' % (stcont, urlx)
			raise Exception, "cannot index"
		if re.match(stcont, xline):
			break

	# this gets all the lines down to the <hr> in the middle
	lklins = []
	while True:
		xline = urx.readline()
		if not xline:
			print '<hr> not found in %s' % urlx
			raise Exception, "cannot index"
		if re.match('<hr>\s*$', xline):
			break
		lklins.append(xline)
	lktex = string.join(lklins, '')

	# get the links
	#<p><a href="../text/40129w01.htm#40129w01_sbhd7"><H3><center>Olympic Games 2012: London Bid</center></H3>
	#</a></p>
	relkex = re.compile('<p><a href\s*=\s*"([^"]*?\.htm)#[^"]*"><h3><center>([^<]*)(?:</center>|</h3>)+\s*</a></p>(?i)')
	res = relkex.findall(lktex)
	if not res:
		print "no links found from day index page"
		raise Exception, "no links"
	return res


def GlueByNext(fout, urla, urlx):
	# put out the indexlink for comparison with the hansardindex file
	lt = time.gmtime()
	fout.write('<pagex url="%s" scrapedate="%s" scrapetime="%s"/>\n' % \
			(urlx, time.strftime('%Y-%m-%d', lt), time.strftime('%X', lt)))

	# loop which scrapes through all the pages following the nextlinks
	# knocking off the known links as we go in case a "next page" is missing.
	while urla:
		url = urla[0]
		ur = urllib.urlopen(url)
		sr = ur.read()
		ur.close();

		# write the marker telling us which page this comes from
		fout.write('<page url="' + url + '"/>\n')


		# split by sections
		hrsections = re.split('<hr>(?i)', sr)

		# this is the case for debates on 2003-03-13 page 30
		# http://www.publications.parliament.uk/pa/cm200203/cmhansrd/vo030313/debtext/30313-32.htm
		if len(hrsections) == 1:
			print len(hrsections)
			print ' page missing '
			print url
			fout.write('<UL><UL><UL></UL></UL></UL>\n')
			break


		# write the body of the text
		for i in range(1, len(hrsections) - 1):
			miscfuncs.WriteCleanText(fout, hrsections[i])

		# find the lead on with the footer
		footer = hrsections[-1]

		# the files are sectioned by the <hr> tag into header, body and footer.
		nextsectionlink = re.findall('<\s*a\s+href\s*=\s*"?(.*?)"?\s*>next section</a>(?i)', footer)
		if len(nextsectionlink) > 1:
			raise Exception, "More than one Next Section!!!"
		if not nextsectionlink:
			urla = urla[1:]
			if urla:
				print "Bridging the missing next section link at %s" % url
		else:
			url = urlparse.urljoin(url, nextsectionlink[0])
			# this link is known
			if (len(urla) > 1) and (urla[1] == url):
				urla = urla[1:]
			# unknown link, either there's a gap in the urla's or a mistake.
			else:
				for uo in urla:
					if uo == url:
						print string.join(urla, "\n")
						print "\n\n"
						print url
						print "\n\n"
						raise Exception, "Next Section misses out the urla list"
				urla[0] = url

	pass  #endwhile urla



###############
# main function
###############
def LordsPullGluePages(datefrom, dateto, bforcescrape):
	# make the output firectory
	if not os.path.isdir(pwlordspages):
		os.mkdir(pwlordspages)

	# load the index file previously made by createhansardindex
	clordsindex = LoadLordsIndex(pwlordsindex)

	# scan through the directory and make a mapping of all the copies for each
	lddaymap = { }
	for ldfile in os.listdir(pwlordspages):
		mnums = re.match("daylord(\d{4}-\d\d-\d\d)([a-z]*)\.html$", ldfile)
		if mnums:
			lddaymap.setdefault(mnums.group(1), []).append((AlphaStringToOrder(mnums.group(2)), mnums.group(2), ldfile))
		elif os.path.isfile(os.path.join(pwlordspages, ldfile)):
			print "not recognized file:", ldfile, " in ", pwlordspages

	# loop through the index of each lord line.
	for dnu in clordsindex.res:
		# implement date range
		if dnu[0] < datefrom or dnu[0] > dateto:
			continue

		# make the filename
		dgflatestalpha, dgflatest = "", None
		if dnu[0] in lddaymap:
			ldgf = max(lddaymap[dnu[0]])
			dgflatestalpha = ldgf[1]
			dgflatest = os.path.join(pwlordspages, ldgf[2])
		ldgfnext = 'daylord%s%s.html' % (dnu[0], NextAlphaString(dgflatestalpha))
		dgfnext = os.path.join(pwlordspages, ldgfnext)
		assert not dgflatest or os.path.isfile(dgflatest)
		assert not os.path.isfile(dgfnext)


		# hansard index page
		urlx = dnu[1]

		# if not force scrape then we may choose to scrape it anyway
		# where the header doesn't match
		if not bforcescrape and dgflatest:
			fpgx = open(dgflatest, "r")
			pgx = fpgx.readline()
			fpgx.close()
			if pgx:
				pgx = re.findall('<pagex url="([^"]*)"[^/]*/>', pgx)
				if pgx:
					if pgx[0] == urlx:
						continue

		# make the message
		print dnu[0], (dgflatest and 'RE-scraping' or 'scraping'), re.sub(".*?ldhansrd/", "", urlx)

		# The different sections are often all run together
		# with the title of written answers in the middle of a page.
		icont = ExtractIndexContents(urlx)
		# this gets the first link (the second [0][1] would be it's title.)
		urla = [ ]
		for iconti in icont:
			uo = urlparse.urljoin(urlx, iconti[0])
			if (not urla) or (urla[-1] != uo):
				urla.append(uo)

		# now we take out the local pointer and start the gluing
		# we could check that all our links above get cleared.
		dtemp = open(tempfilename, "w")
		GlueByNext(dtemp, urla, urlx)
		dtemp.close()

		# now we have to decide whether it's actually new and should be copied onto dgfnext.
		if dgflatest: # the removal of \r makes testing sizes unreliable -- : and os.path.getsize(tempfilename) == os.path.getsize(dgflatest):
			# load in as strings and check matching
			fdgflatest = open(dgflatest)
			sdgflatest = fdgflatest.readlines()
			fdgflatest.close()

			fdgfnext = open(tempfilename)
			sdgfnext = fdgfnext.readlines()
			fdgfnext.close()

			# first line contains the scrape date
			if sdgflatest[1:] == sdgfnext[1:]:
				print "  matched with:", dgflatest
				continue

		print "  writing:", dgfnext
		os.rename(tempfilename, dgfnext)




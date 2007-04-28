import os
import re
import sys
from unparse import ParsetoHTML
from optparse import OptionParser
from unscrape import ScrapeContentsPageFromStem, ScrapePDF, ConvertXML
from unmisc import unexception, IsNotQuiet, SetQuiet, SetCallScrape, undatadir, pdfdir, pdfxmldir, htmldir, xapdir
from nations import PrintNonnationOccurrances
from unindex import MiscIndexFiles
from xapdex import GoXapdex
from votedistances import WriteVoteDistances, WriteDocMeasurements

parser = OptionParser()
parser.set_usage("""

Parses and scrapes UN verbatim reports of General Assembly and Security Council
  scrape  do the downloads
  cxml    do the pdf conversion
  parse   do the parsing
  xapdex  call the xapian indexing system
  votedistances generate voting distances table for java applet
  measurements generate measurements of size of data
  index   generate miscelaneous index files

--stem selects what is processed.
  scrape --stem=S-[YEAR]-PV
""")


if not os.path.isdir(pdfdir):
    print "\nplease create the directory:", pdfdir
    sys.exit(0)
if not os.path.isdir(pdfxmldir):
    print "\nplease create the directory:", pdfxmldir
    sys.exit(0)

parser.add_option("--stem", dest="stem", metavar="stem", default="",
                  help="stem of documents to be parsed (eg A-59-PV)")
parser.add_option("--quiet",
                  action="store_true", dest="quiet", default=False,
                  help="low volume messages")
parser.add_option("--force-parse",
                  action="store_true", dest="forceparse", default=False,
                  help="Don't skip files when parsing")
parser.add_option("--force-cxml",
                  action="store_true", dest="forcecxml", default=False,
                  help="Don't skip files when converting xml")
parser.add_option("--edit",
                  action="store_true", dest="editparse", default=False,
                  help="Edit the file before parsing")
parser.add_option("--scrape-links",
                  action="store_true", dest="scrapelinks", default=False,
                  help="Causes cited documents to be scraped during parsing")
parser.add_option("--doc",
                  dest="scrapedoc", metavar="scrapedoc", default="",
                  help="Causes a single document to be scraped")
parser.add_option("--force-xap", action="store_true", dest="forcexap", default=False,
                  help="Erases existing database, and indexes all .html files")
parser.add_option("--limit", dest="limit", default=None, type="int",
                  help="Stop after processing this many files, used for debugging testing")
parser.add_option("--continue-on-error", action="store_true", dest="continueonerror", default=False,
                  help="Continues with next file when there is an error, rather than stopping")

(options, args) = parser.parse_args()

stem = re.sub("\.", "\.", options.stem)

#print options, args
SetQuiet(options.quiet)
SetCallScrape(options.scrapelinks)
bScrape = "scrape" in args
bConvertXML = "cxml" in args
bParse = "parse" in args
bXapdex = "xapdex" in args
bVoteDistances = "votedistances" in args
bMeasurements = "measurements" in args
bIndexfiles = "index" in args

if not (bScrape or bConvertXML or bParse or bVoteDistances or bXapdex or bIndexfiles or bMeasurements):
    parser.print_help()
    sys.exit(1)

# lack of stem means we do special daily update
if bScrape:
    if not options.stem and not options.scrapedoc:  # default case
        ScrapeContentsPageFromStem("A-61-PV")
        ScrapeContentsPageFromStem("S-2007-PV")
    if options.scrapedoc:
        ScrapePDF(options.scrapedoc, bforce=False)
    if options.stem:
        ScrapeContentsPageFromStem(options.stem)

if bConvertXML:
    if not stem:
        ConvertXML("S-PV-5", pdfdir, pdfxmldir, False)
        ConvertXML("A-61-PV", pdfdir, pdfxmldir, False)
    elif re.match("A-(?:49|[56]\d)-PV", stem):  # year 48 is not parsable
        ConvertXML(stem, pdfdir, pdfxmldir, options.forcecxml)
    elif re.match("S-PV", stem):  # make sure it can't do too many at once
        ConvertXML(stem, pdfdir, pdfxmldir, options.forcecxml)
    else:
        print "Stem should be set, eg --stem=A-49-PV"
        print "  (Can't parse 48, so won't do)"

if bParse:
    if not stem:
        ParsetoHTML("A-61-PV", pdfxmldir, htmldir, options.forceparse, options.editparse)
        ParsetoHTML("S-PV-5[6-9]", pdfxmldir, htmldir, options.forceparse, options.editparse)
    else:
        ParsetoHTML(stem, pdfxmldir, htmldir, options.forceparse, options.editparse)
    PrintNonnationOccurrances()

if bVoteDistances:
    f = "votetable.txt"
    print "Writing data to file:", f
    fout = open(f, "w")
    WriteVoteDistances(stem, htmldir, fout)
    fout.close()

if bMeasurements:
    f = os.path.join(undatadir, "docmeasurements.html")
    fsh = os.path.join(undatadir, "docmeasurementsshort.html")
    print "Writing measurements to files:", f, fsh
    fout = open(f, "w")
    foutshort = open(fsh, "w")
    WriteDocMeasurements(htmldir, pdfdir, fout, foutshort)
    fout.close()
    foutshort.close()

if bXapdex:
    GoXapdex(stem, options.forcexap, options.limit, options.continueonerror, htmldir, xapdir)

if bIndexfiles:  # just for making the big index.html pages used in preview
    MiscIndexFiles(htmldir)

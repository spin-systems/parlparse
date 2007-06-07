#!/usr/bin/python

import sys, os, stat, re
import datetime

from basicbits import WriteGenHTMLhead, EncodeHref
from basicbits import htmldir, pdfdir, pdfinfodir, pdfpreviewdir, pdfpreviewpagedir, basehref


def WritePDF(fpdf):
    print "Content-type: application/pdf\n"
    fin = open(fpdf)
    print fin.read()
    fin.close()

def SubParen(f):
    f = re.sub("\(", "\(", f)
    f = re.sub("\)", "\)", f)
    return f

def WritePDFpreviewpage(pdfinfo, npage, highlightrects, highlightedit):
    WriteGenHTMLhead("%s page %d" % (pdfinfo.desc, npage))
    code = pdfinfo.pdfc

    hmap = {"pagefunc":"pdfpage", "docid":code}
    print '<h3>Other pages</h3>'
    print '<p>'
    if npage != 1:
        hmap["page"] = npage - 1
        print '<a href="%s">Page %d</a>' % (EncodeHref(hmap), npage - 1)
    print '<a href="%s">Full doc</a>' % EncodeHref({"pagefunc":"document", "docid":code})
    if pdfinfo.pages == -1 or npage + 1 < pdfinfo.pages:
        hmap["page"] = npage + 1
        print '<a href="%s">Page %d</a>' % (EncodeHref(hmap), npage + 1)
    print '</p>'
    
    hmap["page"] = npage
    hmap["highlightrects"] = highlightrects
    hmap["highlightedit"] = False

    print '<h3>Links</h3>'
    ivl = '<a href="%s">Document %s</a>' % (EncodeHref(hmap), code)  # this is text for the pastable input box
    print '<p>URL: <input style="text" readonly value=\'%s\'></p>' % ivl
    
    ivw = [ '<ref>{{ UN document |code=%s' % pdfinfo.pdfc ]
    ivw.append(' |body=General Assembly |session=60')
    ivw.append(' |page=%d' % npage)
    if highlightrects:
        rs = [ ("rect_%d,%d_%d,%d" % highlightrect)  for highlightrect in highlightrects ]
        ivw.append(' |highlight=%s' % "/".join(rs))
    ivw.append(' |accessdate=1999-99-99 }}</ref>')
    print '<p>wiki: <input style="text" readonly value=\'%s\'></p>' % "".join(ivw)


    print '<h3>Editing highlight</h3>'
    if highlightrects:
        hmap["highlightrects"] = [ ]
        print '<p><a href="%s">no highlight</a>' % EncodeHref(hmap),
        if len(highlightrects) > 1:
            for ih in range(len(highlightrects)):
                hmap["highlightrects"] = highlightrects[:]
                del hmap["highlightrects"][ih]
                print '<a href="%s">withough highlight %d</a>' % (EncodeHref(hmap), ih),
        print '</p>'

        hmap["highlightrects"] = highlightrects

    if highlightedit:
        print '<script src="%s/cropper/lib/prototype.js" type="text/javascript"></script>' % basehref
        print '<script src="%s/cropper/lib/scriptaculous.js?load=builder,dragdrop" type="text/javascript"></script>' % basehref
        print '<script src="%s/cropper/cropper.js" type="text/javascript"></script>' % basehref
        print """<script type="text/javascript">
                    Event.observe(window, 'load',
                              function() { new Cropper.Img('pdfpageid', { onEndCrop: onEndCrop }); } );

                function onEndCrop( coords, dimensions )
                {
                    var achl = document.getElementById('consdhighlight');
                    var imgl = document.getElementById('pdfpageid');
                    lhref = achl.href.substring(0, achl.href.lastIndexOf('/') + 1);
                    ix1 = Math.ceil(coords.x1 * 1000 / imgl.width);
                    iy1 = Math.ceil(coords.y1 * 1000 / imgl.width);
                    ix2 = Math.ceil(coords.x2 * 1000 / imgl.width); 
                    iy2 = Math.ceil(coords.y2 * 1000 / imgl.width);
                    rs = "rect_" + ix1 + "," + iy1 + "_" + ix2 + "," + iy2; 
                    achl.href = lhref + rs; 
                };
                </script>"""

        print '<p>Click and drag a box to highlight the text you want.'
        hmap["highlightedit"] = False
        print '<a href="%s">leave editing mode</a>' % (EncodeHref(hmap))
        print '<a id="consdhighlight" href="%s/"><b>consolidate highlight</b></a>' % EncodeHref(hmap)
        print '<small>Thanks to <a href="http://www.defusion.org.uk/code/javascript-image-cropper-ui-using-prototype-scriptaculous/">Dave Spurr</a>.</small>'
        print '</p>'
    else:
        hmap["highlightedit"] = True
        print '<p><a href="%s"><b>add new highlight</b></a></p>' % EncodeHref(hmap)
    print '<p></p>'

    del hmap["highlightedit"]
    hmap["pagefunc"] = "pagepng"
    hmap["width"] = 800
    print '<div class="pdfpagediv"><img id="pdfpageid" src="%s"></div>' % EncodeHref(hmap)



def WritePDFpreview(basehref, pdfinfo):
    WriteGenHTMLhead('<div style="float:right; font-size:20; vertical-align:text-bottom;">%s</div> %s' % (pdfinfo.pdfc, pdfinfo.desc))
    
    code = pdfinfo.pdfc

    if pdfinfo.pvrefs:
        print '<h3>Meetings that refer to this document</h3>'
        print '<ul>'
        for pvrefk in sorted(pdfinfo.pvrefsing.keys()):
            mcode = pvrefk[1]
            hmap = { "pagefunc":"meeting", "docid":mcode, "highlightdoclink":code }
            hmap["gid"] = min(pdfinfo.pvrefsing[pvrefk])
            print '<li>%s <a href="%s">%s</a></li>' % (pvrefk[0], EncodeHref(hmap), mcode)
        print '</ul>'

    if pdfinfo.mgapv or pdfinfo.mscpv:
        print '<p>Return to <a href="%s">Parsed document</a></p>' % (EncodeHref({"pagefunc":"meeting", "docid":code}))
    
    print '<h3><a href="%s">native pdf</a></h3>' % EncodeHref({"pagefunc":"nativepdf", "docid":code})

    print '<h3>Link to pages</h3>'
    if pdfinfo.pages != -1:
        print '<p>',
        for n in range(pdfinfo.pages):
            print '<a href="%s">Page %d</a>' % (EncodeHref({"pagefunc":"pdfpage", "docid":code, "page":(n+1)}), n + 1),
        print '</p>'
    else:
        print '<p>We don\'t know how many pages.  '
        print '<a href="%s">Page 1</a></p>' % EncodeHref({"pagefunc":"pdfpage", "docid":code, "page":1})

    pdfpreviewf = os.path.join(pdfpreviewdir, code + ".jpg")
    if os.path.isfile(pdfpreviewf):
        print '<img src="../undata/pdfpreview/%s.jpg">' % code

    print '</body>'
    print '</html>'




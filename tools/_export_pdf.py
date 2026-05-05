import scribus, sys
infile = sys.argv[1]; outfile = sys.argv[2]
scribus.openDoc(infile)
pdf = scribus.PDFfile()
pdf.file = outfile
pdf.save()

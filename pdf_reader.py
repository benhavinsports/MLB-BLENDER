from parser_star import parse_pdf, pdf_text

def read_pdf(file_bytes):
    return parse_pdf(file_bytes)

def raw_pdf_text(file_bytes):
    return pdf_text(file_bytes)

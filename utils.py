from datetime import datetime
from dateutil import tz
import locale
import json
import re
import glob
import os

def dir_exist(path):
    return os.path.isdir(path)

def make_dir(path):
    if not dir_exist(path):
        try:
            os.mkdir(path)
        except OSError:
            print (f"Failed to create directory '{path}'")
        else:
            print(f"Creating folder '{path}'..")

def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"

def utc_to_local(utc_datetime):
    return utc_datetime.astimezone(tz.tzlocal())

def convert_date(string):
    if ' (' in string:
        string = string.split(' (')[0]
    try:
        date = datetime.strptime(string, '%a, %d %b %Y %H:%M:%S %z')
        tz_date = utc_to_local(date)
    except ValueError:
        date = datetime.strptime(string, '%d %b %Y %H:%M:%S %z')
        tz_date = utc_to_local(date)
    return tz_date

def string_to_date(string):
    return datetime.strptime(string, "%d/%m/%Y")

# def convert_money(string):
#     if '-' in string[-1]:
#         string = '-' + string[:-1]
#         print(string)
#     try:
#         if re.search("((-|)\d*\.\d*(\,\d{2}|))$", string):
#             locale.setlocale(locale.LC_ALL, 'es_CO.UTF8')
#             op_amount = locale.atof(string.strip('$'))
#             locale.setlocale(locale.LC_ALL, 'en_US.UTF8')
#         # elif re.search("\$\d*\,\d*(\.\d{2}|)", string):
#         elif re.search("(-|)\d*\,\d*(\.\d{2}|)", string):
#             locale.setlocale(locale.LC_ALL, 'en_US.UTF8')
#             op_amount = locale.atof(string.strip('$'))
#     except ValueError:
#         print(f"Could not convert {string} to money")
#     finally:
#         return op_amount

def convert_money(string):
    if '-' in string[-1]:
        string = '-' + string[:-1].strip('$')
    op_amount = None
    try:
        if string == '0.00':
            return locale.atof(string.strip('$'))
        elif re.match("(-|)\d*(\,|)\d*(\.\d{2}|)", string):
            locale.setlocale(locale.LC_ALL, 'en_US.UTF8')
            op_amount = locale.atof(string.strip('$'))
        else:
            print("didn't pass re.match")
    except ValueError:
        print(f"Could not convert {string} to money")
    # finally:
    if op_amount:
        return op_amount
    else:
        print(f"Could not convert {string} to money")

def string_to_datetime(string):
    if type(string) is str:
        return datetime.strptime(string, '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
    return string

def regexp_in_list(source, items_list, index=1):
    """Takes a source list or dictionary to compare against a list"""
    if isinstance(source, dict):
        for item in source.items():
            for match in items_list:
                if re.search(item[0], match.text, re.IGNORECASE):
                    return item[index]
    elif isinstance(source, list):
        for item in source:
            for match in items_list:
                if re.search(item, match.text, re.IGNORECASE):
                    return match
    return None

def is_num(string):
    try:
        negative_form = ''
        if re.search("(\.|)\d{2}-", string):
            negative_form = re.search("(\.|)\d{2}-", string).group()
        string = string.replace(negative_form, '').replace(',', '').replace('.', '')
        if string.isdigit():
            return True
    except AttributeError:
        return False
    else:
        return False

def list_pdfs():
    list_of_files = glob.glob('./data/*.pdf') # * means all if need specific format then *.csv
    if list_of_files:
        return list_of_files
    else:
        print("No PDF files found.")
        return None

def last_pdf():
    list_of_files = list_pdfs()
    if list_of_files is not None:
        latest_file = max(list_of_files, key=os.path.getctime)
        return latest_file

def dict_to_list(dic):
    if isinstance(dic, dict):
        return [item for item in dic.values()]
    elif isinstance(dic, list):
        return [list(item.values()) for item in dic]
    print(f"To convert dictionary to list, input must be dict, not {type(dic)}")
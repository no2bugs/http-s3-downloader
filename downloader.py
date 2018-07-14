#!/usr/bin/env python3


import requests
import sys, os, traceback
import re
import boto3, botocore
from multiprocessing import Pool
from functools import partial
import argparse
import time
from datetime import timedelta
from urllib.parse import urlparse, unquote_plus
from getpass import getpass


def check_python_version(v):
    v = str(v).split('.')
    try:
        if not 1 < int(v[0]) <= 3:
            raise ValueError('Error: You are requiring invalid Python version',v[0])
    except ValueError as e:
        print(e)
        sys.exit(1)
    if sys.version_info[0] != int(v[0]):
        print('This script requires Python version',v[0] + '+')
        print('You are using {0}.{1}.{2} {3}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2],sys.version_info[3]))
        sys.exit(1)


def request_content(url,time_out=60,debug=False):
    try:
        resp = requests.get(url,stream=True, # enabling stream to avoid memory overrun for large files
                            timeout=time_out, # timeout to throw error and avoid incomplete file downloads when lost connection
                            # Use Chrome's user-agent to appear as real browser to prevent being labeled as a bot
                            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'})

        if (100 <= resp.status_code < 600) and (resp.status_code != 200):
            raise ConnectionError('Error: Bad response code')
    except ConnectionError as e:
        if debug:
            exc_type, exc_value, exc_tb = sys.exc_info()
            tbe = traceback.TracebackException(exc_type, exc_value, exc_tb, )
            print(''.join(tbe.format()))
        print(e)
        print('Returned:', resp.status_code, resp.reason)
        return None
    except Exception as e:
        print('Error: Something went wrong\n', e)
        if debug:
            exc_type, exc_value, exc_tb = sys.exc_info()
            tbe = traceback.TracebackException(exc_type, exc_value, exc_tb, )
            print(''.join(tbe.format()))
        return None

    return resp


def convert_bytes(f_size):
    if f_size is None:
        print('File size:   ', 'Unknown')
        return None
    elif f_size < 1024:
        print('File size:   ', int(f_size), 'bytes')
    elif 1024 <= f_size <= 1048576:
        size = float(f_size) / 1024
        print('File size:   ', round(size, 2), 'Kilobytes')
    else:
        size = float(f_size) / 1048576
        print('File size:   ', round(size, 2), 'Megabytes')

    return f_size


def download_file(path,f_url,parallel=0,t_out=30,stack_trace=False,aws_a_key=None,aws_s_key=None):
    if parallel == 0:
        parallel = False

    path = path.rstrip('/')
    url = f_url
    parsed_url = urlparse(url)
    proto = parsed_url.scheme

    # clean up file name to be saved on disk - unqote and replace special chars with _
    f_name = f_url.split('/')[-1]
    parsed_f_name = unquote_plus(f_name)
    file_name = re.sub('[^a-zA-Z0-9-_.\n]', '_', parsed_f_name)

    file_path = path + '/' + file_name
    absolute_file_path = os.path.abspath(file_path)

    # this block handles http and https url downloads
    if proto in ['http','https']:
        response  = request_content(url,time_out=t_out,debug=stack_trace)
        if response is None:
            return url, 'FAILED'

        print(time.strftime("%d/%m/%Y %H:%M:%S"))
        print('Starting download of {0} from {1}\nFile Path:    {2}'.format(file_name, url, file_path))
        print('content type:',response.headers['content-type'])
        print('encoding:    ',response.encoding)

        file_size = convert_bytes(f_size=int(response.headers.get('content-length')))

        if not parallel:
            print('Downloading...')
        else:
            print('Downloading...\n')
        start_download = time.time()
        with open(file_path, 'wb') as f:
            try:
                if file_size is None:  # unable to chunk up data if unable to detect file size
                    f.write(response.content)
                else:
                    downloaded = 0
                    for data in response.iter_content(chunk_size=4096): # process data in chunks
                        downloaded += len(data)
                        f.write(data)
                        if not parallel: # enable progress bar if downloads are not running in parallel
                            progress = int(50 * downloaded / file_size)
                            percent = progress * 2
                            sys.stdout.write("\r[%s%s]%s" % ('=' * progress, ' ' * (50 - progress), str(percent) + '%'))
                            sys.stdout.flush()
            except Exception as e:
                print('\nSomething went wrong. Deleting incomplete file', file_path, '\nError:', e)
                if stack_trace:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    tbe = traceback.TracebackException(exc_type, exc_value, exc_tb,)
                    print(''.join(tbe.format()))
                os.remove(file_path)
                return url, 'FAILED'

        finish_download = time.time()
        t_diff = float(finish_download) - float(start_download)
        t_finish = timedelta(seconds=int(t_diff))

        print('\nFinished downloading {0} from {1}\nFile Path:     {2}\nDownload Time: {3}'.format(file_name,url,file_path,t_finish))
        print('Finish Date:  ', time.strftime("%d/%m/%Y %H:%M:%S"))
        print()

        return absolute_file_path, t_finish

    # this block handles S3 downloads
    elif proto == 's3':
        bucket_name = parsed_url.netloc
        key = f_name

        if aws_a_key and aws_s_key:
            print("Using provided AWS access credentials for downloading from S3")
            session = boto3.Session(
                aws_access_key_id=aws_a_key,
                aws_secret_access_key=aws_s_key,
            )
            s3 = session.resource('s3')
            s3_client = session.client('s3')
        else:
            s3 = boto3.resource('s3')
            s3_client = boto3.client('s3')

        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=key)
            size = response['ContentLength']
            c_type = response['ContentType']
            print(time.strftime("%d/%m/%Y %H:%M:%S"))
            print('Starting download of {0} from {1}\nFile Path:    {2}'.format(file_name, url, file_path))
            print('Content-type:', c_type)
            convert_bytes(f_size=size)
            print('Downloading...')
            start_download = time.time()
            s3.Bucket(bucket_name).download_file(key, file_path)
        except botocore.exceptions.NoCredentialsError:
            print('Error: Invalid or Missing Credentials for S3')
            print("Try running script with '--s3-credentials' and provide your AWS credentials")
            if stack_trace:
                exc_type, exc_value, exc_tb = sys.exc_info()
                tbe = traceback.TracebackException(exc_type, exc_value, exc_tb, )
                print(''.join(tbe.format()))
            print()
            return url, 'FAILED'
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print('FAILED to download', url, 'from S3')
                print("Object not found: 404\n",e)
                print()
                return url, 'FAILED'
            elif e.response['Error']['Code'] == "403":
                print('FAILED to download', url, 'from S3')
                print("Access Forbidden: 403\n",e)
                print()
                return url, 'FAILED'
            else:
                print('FAILED to download', url, 'from S3')
                print('Client Error')
                if stack_trace:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    tbe = traceback.TracebackException(exc_type, exc_value, exc_tb,)
                    print(''.join(tbe.format()))
                print('Error:', e)
                print()
                return url, 'FAILED'
        except Exception as error:
                print('FAILED to download', url, 'from S3')
                if stack_trace:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    tbe = traceback.TracebackException(exc_type, exc_value, exc_tb,)
                    print(''.join(tbe.format()))
                print('Error:', error)
                print()
                return url, 'FAILED'

        finish_download = time.time()
        t_diff = float(finish_download) - float(start_download)
        t_finish = timedelta(seconds=int(t_diff))

        print('\nFinished downloading {0} from {1}\nFile Path:     {2}\nDownload Time: {3}'.format(file_name,url,file_path,t_finish))
        print('Finish Date:  ', time.strftime("%d/%m/%Y %H:%M:%S"))
        print()

        return absolute_file_path, t_finish

    # this block handles unsupported protocols
    elif not proto:
        print('Error: Protocol not detected in "{0}" Please verify the URL'.format(url))
        print('Did you mean one of these?')
        for protocol in ['http://', 'https://', 's3://']:
            print('-',protocol + url)
        print()
        return url, 'FAILED'
    else:
        print('Error: Unsupported Protocol {0} in {1}'.format(proto,url))
        print('-','Supported Protocols: "http://" "https://" "s3://"')
        print()
        return url, 'FAILED'


def prompt_aws_creds(rev_creds=False): # handling this in a separate method to avoid re-prompting for multiple files
    while True:
        print("\nPlease provide AWS access credentials")
        try:
            if not rev_creds:
                aws_access_key = getpass('AWS ACCESS KEY (Hidden): ')
                aws_secret_key = getpass('AWS SECRET KEY (Hidden): ')
            else:
                aws_access_key = input('AWS ACCESS KEY: ')
                aws_secret_key = input('AWS SECRET KEY: ')

            if len(aws_access_key) == 0 or len(aws_secret_key) == 0:
                raise ValueError("Error: Values can't be empty")
            else:
                break
        except ValueError as e:
            print(e)

    return aws_access_key, aws_secret_key


if __name__ == "__main__":
    check_python_version('3')

    parser = argparse.ArgumentParser(description='Downloads a file or space/comma separated list of files from URL/s. Supports "http://", "https://" and "s3://"')
    parser.add_argument('-d', '--download',nargs='+', help='Provide single or multiple space/comma separated files to download (ex. ./downloader.py -d http://domain.com/file1 https://domain.com/file2 s3://key/file1)')
    parser.add_argument('-p', '--path', help='Provide path where to save downloaded file/s. Default is script\'s path',default='.')
    parser.add_argument('-c', '--concurrent',type=int, help='Set number of downloads to run in parallel. Default is one at a time',default=0)
    parser.add_argument('-t', '--timeout',type=int,help='Set inactive connection timeout for downloads (seconds). Default is 30 seconds', default=30)
    parser.add_argument('-b', '--debug', action='store_true',help='Enable debug mode to stacktrace errors. Default is False',default=False)
    parser.add_argument('-s', '--s3-credentials', action='store_true',help='Enable this to be prompted for S3 credentials. Default is Disabled', default=False)
    parser.add_argument('-r', '--reveal-credentials', action='store_true',help='Enable this to un-hide AWS credentials during input. Works together with "-s or --s3-credentials". Default is Disabled', default=False)
    args = parser.parse_args()

    if not args.download:
        parser.print_help()
        print("\n*** Error: Must pass URL/s for file/s to download '-d or --download file1 file2 file3 ...' ***")
        print("example: ./downloader.py -d http://domain.com/file1 https://domain.com/file2 s3://key/file1")
        print()
        sys.exit(1)

    if args.s3_credentials:
        AWS_ACCESS_KEY, AWS_SECRET_KEY = prompt_aws_creds(rev_creds=args.reveal_credentials)
    else:
        AWS_ACCESS_KEY, AWS_SECRET_KEY = None,None

    PARALLEL_DOWNLOADS = int(args.concurrent) # controls number of procs for multiprocessing

    # preserve order of download items from user input
    seen = set()
    FILE_URLS = [x for x in str(' '.join(args.download)).replace(',', ' ').split() if not (x in seen or seen.add(x))]

    FILE_SAVE_PATH = args.path

    if PARALLEL_DOWNLOADS > len(FILE_URLS):
        print('Concurrent downloads should not exceed number of files to download')
        sys.exit(1)

    if PARALLEL_DOWNLOADS > 1: # download files concurrently using multiprocessing
        print('\nRunning',PARALLEL_DOWNLOADS,'downloads in parallel\n')
        pool = Pool(PARALLEL_DOWNLOADS)
        downloads = pool.map(partial(download_file,
                                     FILE_SAVE_PATH,
                                     parallel=PARALLEL_DOWNLOADS,
                                     t_out=args.timeout,
                                     stack_trace=args.debug,
                                     aws_a_key=AWS_ACCESS_KEY,
                                     aws_s_key=AWS_SECRET_KEY),FILE_URLS)
        pool.close()
        pool.join()
        max_len = max(len(l[0]) for l in downloads)
        print('{0:^{padding}}   {1}'.format('FILE', 'DURATION', padding=max_len))
        print('{0:{padding}}   {1}'.format('-' * max_len, '-' * 8, padding=max_len))
        for f,t in downloads:
            print('{0:{padding}} : {1}'.format(f,t,padding=max_len))
        print()
    else: # download files one at a time
        downloads = []
        for i,item in enumerate(FILE_URLS,1):
            print('#',str(i))
            downloads.append(download_file(FILE_SAVE_PATH, item,
                                           t_out=args.timeout,
                                           stack_trace=args.debug,
                                           aws_a_key=AWS_ACCESS_KEY,
                                           aws_s_key=AWS_SECRET_KEY))
        max_len = max(len(l[0]) for l in downloads)
        print('{0:^{padding}}   {1}'.format('FILE', 'DURATION', padding=max_len))
        print('{0:{padding}}   {1}'.format('-' * max_len, '-' * 8, padding=max_len))
        for f,t in downloads:
            print('{0:{padding}} : {1}'.format(f,t,padding=max_len))
        print()

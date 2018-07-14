# HTTP/S and S3 File Downloader

**This script downloads a file or space/comma separated list of multiple files from provided URL/s.**

Supports the following protocols: 
* http:// and https://
* s3://

#### Features:
* Downloads files from any HTTP/S URL
* Downloads AWS S3 objects and allows passing AWS credentials when needed
* Leverages optional multiprocessing to download files in parallel
* Downloads files in chunks to reduce memory footprint
* Downloads multiple HTTP/S, S3 files with a single command

### Prerequisites:
* Python version => 3
#### External module dependencies:
1. requests
2. boto3
3. botocore

#### Getting Started:
*Execute setup.py to install dependencies*
`./setup.py install`


##### List all the options:
*Execute `--help` to display options*

```
shell#: python3 downloader.py --help
usage: downloader.py [-h] [-d DOWNLOAD [DOWNLOAD ...]] [-p PATH]
                             [-c CONCURRENT] [-t TIMEOUT] [-b] [-s] [-r]

Downloads a file or space/comma separated list of files from URL/s. Supports
"http://", "https://" and "s3://"

optional arguments:
  -h, --help            show this help message and exit
  -d DOWNLOAD [DOWNLOAD ...], --download DOWNLOAD [DOWNLOAD ...]
                        Provide single or multiple space/comma separated files
                        to download (ex. ./downloader.py -d
                        http://domain.com/file1 https://domain.com/file2
                        s3://key/file1)
  -p PATH, --path PATH  Provide path where to save downloaded file/s. Default
                        is script's path
  -c CONCURRENT, --concurrent CONCURRENT
                        Set number of downloads to run in parallel. Default is
                        one at a time
  -t TIMEOUT, --timeout TIMEOUT
                        Set inactive connection timeout for downloads
                        (seconds). Default is 30 seconds
  -b, --debug           Enable debug mode to stacktrace errors. Default is
                        False
  -s, --s3-credentials  Enable this to be prompted for S3 credentials. Default
                        is Disabled
  -r, --reveal-credentials
                        Enable this to un-hide AWS credentials during input.
                        Works together with "-s or --s3-credentials". Default
                        is Disabled
```

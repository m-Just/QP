# CusisPlus (dev)
## What is CusisPlus
A standalone software based on CUHK CUSIS to provide more convenient and friendly course enrollment experience for students, which supports the following features:  
1. Super-fast course searching and relevant course listing  
2. A much more user-friendly timetable  
3. Simultaneous multiple courses selection and instant timetable display  
4. Multiple backup course plan can be saved locally, and can be synchronized with CUSIS at anytime  
## Set up running environment
1. Install Python 2.7 (64-bit) from https://www.python.org/  
2. Install `PyQt4`(PyQwt‑5.2.1‑cp27‑cp27m‑win_amd64.whl) from http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyqt4  
3. Install package `scrapy`, `selenium` by command `pip install [package_name]`  
4. Download `PhantomJS` from http://phantomjs.org/ and put the executable under the project folder  
5. (optional) download `Chrome driver` from https://sites.google.com/a/chromium.org/chromedriver/ and put the executable under the project folder  
## Running the program
1. Go to project directory and then run command `python main.py`  
2. First time login may require some time, since the whole course catalog is to be downloaded  
## Report issues
1. Submit issues in this repository  
2. Contact mjust.lkc@gmail.com  

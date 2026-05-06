How to run this program

1. Make sure you have Python installed in your machine, at least version 3.13

    ![Python Downloads](https://www.python.org/downloads/)
    
2. It is recommended to use a virtual environment

        py -m venv .venv

   Start the venv

        .venv/Scripts/activate
   
4. Install dependencies

        pip install -r requirements.txt
   
6. Setup your Nextcloud server address and auth credentials in a .env
7. Run `iterate.py` script to loop the tests

        py iterate.py

8. Run `vis.py` script after the test to get a visualization

        py vis.py

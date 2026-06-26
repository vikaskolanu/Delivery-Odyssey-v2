source /Users/vikaskolanu/delivery_Odyssey_v3/venv/bin/activate
// this is for activating the virtual environment for this folder

python main.py
// for running the file 

open main.html 
// opens the map on the browser 

uvicorn api.server:app --reload
// this is to run the fastAPI backend

to verify the backend, we need to check the health at this page
http://127.0.0.1:8000/health
// we'll get something like  " optimizer : ready "

python -m http.server 5500
// this should be run, to have a connection with the fastAPI backend also 

http://localhost:5500/map.html
 // this is where we can see our visualisation


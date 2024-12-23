# UPISAS
2024 RAMSES Project 

# To run this project

navigate to the root directory of this project and run the following command:

`python3 ramses_run.py`

NOTE: If you are using an older version of python, please change python3 to just python. So you will instaed run: 

`python ramses_run.py`

Please create a .env file in UPISAS\ramses and replace the field according to the exampleEnv


# Docker containers started successfully
![alt text](<Screenshot (12).png>)

# Running MAPE-K Loop
![alt text](<Screenshot (13).png>)

# Failure detected: Adaptation actions executed successfully
![alt text](<Screenshot (10).png>)

# New instance added succesfuly after adaptation
![alt text](<Screenshot (15).png>)

### Guidelines to Run 
In a terminal, navigate to the parent folder of the project:

1. Start Docker containers for the system under test for the baseline strategy by the command

```
 python run.py
```

Wait for the container to be initialized and up for approx 5 minutes.

2. Go to the SEAMS artififact and run the REST_CLIENT and wait for the qos metrics.

3. To run the simulations, we have created a file named experiment_script.py, to get simulations for baseline run the file with the command 
```
 python experiment_script.py
```
and the same goes for our strategy which is in the file named ramses_run.py.

4. The scripts for our simulations are present in the folder named data_visualization. Running this will create csv files with the required qos data.



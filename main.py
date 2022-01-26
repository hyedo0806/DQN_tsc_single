from __future__ import absolute_import
from __future__ import print_function

import os
import datetime
#from shutil import copyfile
import numpy as np

#from training_practice import Simulation
#from base import Simulation
from edited_ver import Simulation

from memory import Memory
from model import TrainModel

from setting import *
from utils import import_train_configuration, set_train_path

if __name__ == "__main__":

    config = import_train_configuration(config_file='training_settings.ini')
    path = set_train_path(config['models_path_name'])

    Model = TrainModel(
        config['num_layers'],
        config['width_layers'],
        config['batch_size'],
        config['learning_rate'],
        input_dim=config['num_states'],
        output_dim=config['num_actions']
    )

    Memory = Memory(
        config['memory_size_max'],
        config['memory_size_min'],
        0.001, # epsilon_min
        0.999 # epsilon_decay
    )

    setting = setting()
    setting.veh_input()
    setting.road()
    setting.signal()


    Simulation = Simulation(
        Model,
        Memory,
        setting,
        config['gamma'],
        config['max_steps'],
        config['green_duration'],
        config['yellow_duration'],
        config['num_states'],
        config['num_actions'],
        config['training_epochs']
    )
    scores = []
    episode = 0

    timestamp_start = datetime.datetime.now()
    
    while episode < config['total_episodes']:
        for simRun in setting.Vissim.Net.SimulationRuns:
            setting.Vissim.Net.SimulationRuns.RemoveSimulationRun(simRun)

        print('\n----- Episode', str(episode + 1), 'of', str(config['total_episodes']))
        epsilon = 1.0 - (episode / config['total_episodes'])  # set the epsilon for this episode according to epsilon-greedy policy

        simulation_time, training_time, score = Simulation.run(epsilon, episode)  # run the simulation
        scores.append(score)

        print('Simulation time:', simulation_time, 's - Training time:', training_time, 's - Total:',
              round(simulation_time + training_time, 1), 's', ' || avg_queue  :  ', score)
        episode += 1

        #StopDelay, Stops, VehDelay, Vehs = Result.Delay()
        #maxQ, Qlen, QStops = Result.Queue_Length()
        #No_Veh, Speed, Acceleration, Length = Result.data_collection()
        #Travel_Time, No_Veh = Result.travel_time()

    print("score : ", scores)
    print("\n----- Start time:", timestamp_start)
    print("----- End time:", datetime.datetime.now())
    print("----- Session info saved at:", path)
    Model.save_model(path)


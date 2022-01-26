import traci
import numpy as np
import random
import timeit
import os

BASE = [470, 490, 350, 230, 260]
PHASE = ['00001100', '11000000', '00110000', '00100010', '00000011']
MIN_GREEN = [390, 460, 320, 200, 140]  ## yellow 3초 포함
MAX_GREEN = [700, 750, 550, 350, 400]
REMAIN = [1120, 660, 340, 140, 0]  ## 남아있는 현시들의 최소 제약조건 시간의 합

ACTION = [[0,29],[1,28],[2,27],[3,26],[4,25],[5,24],[6,23],[7,22],[8,21],[9,20],[10,19],[11,18],[12,17],[13,16],[14,15],[15,14],[16,13],[17,12],[18,11],[19,10],[20,9],[21,8],[22,7],[23,6],[24,5],[25,4],[26,3],[27,2],[28,1],[29,0]]

class Simulation:
    def __init__(self, Model, Memory, setting, gamma, max_steps, green_duration, yellow_duration, num_states,
                 num_actions, training_epochs):
        self._Model = Model
        self._Memory = Memory
        self._setting = setting

        self._max_steps = max_steps
        self.epsilon = 1.0
        self._num_states = num_states
        self._num_actions = num_actions
        self._state = [0 for i in range(self._num_states)]
        self._gamma = gamma
        self.batch_size = 10
        self.train_start = 20

        self.Max_Q = [0 for i in range(5)]

        self.store_duration = np.zeros(5)
        self._training_epochs = training_epochs

    def _choose_action(self, state, epsilon):

        if random.random() < epsilon:
            return random.randint(0, self._num_actions - 1)
        else:
            return np.argmax(self._Model.predict_one(state))

    def simulate(self, action, Vol_traffic, if_pre):
        ## action : ACTION의 element // Vol_traffic = [(a,b),(c,d,e)] // if_pre : T or F
        ## Vol_traffic => a+b = 1,  c+d+e = 1

        ## ========== set duration of each phase =======
        self.phase = []

        if if_pre: self.phase = BASE
        else :
            cnt=0
            for i in range(len(action)):
                for j in range(len(Vol_traffic[i])):
                    self.phase.append(round(Vol_traffic[i][j] * action[i])*10+MIN_GREEN[cnt])
                    cnt+=1

        for p in range(5):
            for i in range(8):
                if PHASE[p][i] == '0':
                    self._setting.SG[i].SetAttValue("SigState", "RED")
                else:
                    self._setting.SG[i].SetAttValue("SigState", "GREEN")
            for time_p in range(self.phase[p] - 30):
                self._setting.Vissim.Simulation.RunSingleStep()
                if time_p%10 == 9 :
                    self.TH_calculate()
                    self._get_Qtime()


            for i in range(8):
                if PHASE[p][i] == '1':
                    self._setting.SG[i].SetAttValue("SigState", "AMBER")

            for time_p in range(self.phase[p] - 30, self.phase[p]):
                self._setting.Vissim.Simulation.RunSingleStep()
                if time_p % 10 == 9:
                    self.TH_calculate()
                    self._get_Qtime()

    def TH_calculate(self):

        alloc = {'1': [1], '2': [1], '3': [2, 3], '4': [2], '5': [0], '6': [0], '7': [4], '8': [3, 4]}

        for dirc in alloc.keys():
            for i in self._setting.detector[dirc]:
                if i.AttValue('VehNo') > 0:
                    for num in range(len(alloc[dirc])):
                        self.TH[alloc[dirc][num]] += 1



    def traffic_volume(self):

        sub = self.TH[0]+self.TH[1]
        main = self.TH[2]+self.TH[3]+self.TH[4]
        temp_s, temp_m, rate = [], [], []
        for i in range(2): temp_s.append(self.TH[i]/sub)
        for i in range(3): temp_m.append(self.TH[i]/main)
        rate.append(temp_s)
        rate.append(temp_m)

        #rate = [(0.5,0.5),(0.3,0.4,0.3)]
        return rate   # [(a,b),(c,d,e)]

    def _get_Qtime(self):
        queue = [0 for i in range(5)]
        alloc = {'1':[1],'2':[1],'3':[2,3],'4':[2],'5':[0],'6':[0],'7':[4],'8':[3,4]}

        for dirc in alloc.keys():
            for i in self._setting.lane[dirc]:
                if not i.AttValue('MAX:VEHS\QTIME') == None:
                    for num in range(len(alloc[dirc])):
                        queue[alloc[dirc][num]] += i.AttValue('MAX:VEHS\QTIME')

        for i in range(5):
            self.Max_Q[i] = max(self.Max_Q[i], queue[i])

    def _get_state(self):
        state = []

        for i in self.Max_Q : state.append(i)
        for i in self.phase: state.append(i)

        state = np.reshape(state, [1, self._num_states])
        return state


    def all_red(self):
        for i in range(8):
            self._setting.SG[i].SetAttValue("SigState", "RED")
    def replay(self):
        if len(self._Memory._samples) < self.train_start:
            return

        minibatch = random.sample(self._Memory._samples, self.batch_size)
        state = np.zeros((self.batch_size, self._num_states))
        next_state = np.zeros((self.batch_size, self._num_states))
        action, reward, done = [], [], []

        for i in range(self.batch_size):
            state[i] = minibatch[i][0]
            action.append(minibatch[i][1])
            reward.append(minibatch[i][2])
            next_state[i] = minibatch[i][3]

        target = self._Model._model.predict(state)
        target_next = self._Model._model.predict(next_state)

        for i in range(self.batch_size):
            target[i][action[i]] = reward[i] + self._gamma * (np.amax(target_next[i]))

        self._Model._model.fit(state, target, batch_size=self.batch_size, verbose=0)
    def save(self, name):
        self._Model._model.save(name)

    def run(self, epsilon, episode):

        start_time = timeit.default_timer()
        self._step = 0
        score = 0
        scores = []
        self.TH = [0 for i in range(5)]

        current_state = [0 for i in range(self._num_states)]
        current_state = np.reshape(current_state, [1, self._num_states])

        self._setting.Vissim.Simulation.RunSingleStep()

        ### ====================offline(fixed time table로 1회)=============================================

        self.simulate(0,0,True)
        current_state = self._get_state()
        current_Qsum = sum(self.Max_Q)
        Vol_traffic = self.traffic_volume()

        print('offline state : ', current_state)

        self.TH = [0 for i in range(5)]
        self.Max_Q = [0 for i in range(5)]

        print("   end the Offline and start the Online")
        ### ===================== Offline finished =============================
        ### ===================== Online start =================================

        while self._step < self._max_steps:

            action = ACTION[self._choose_action(current_state, epsilon)]
            self.simulate(action, Vol_traffic, False)

            Vol_traffic = self.traffic_volume()
            next_Qsum = sum(self.Max_Q)
            next_state = self._get_state()

            self.TH = [0 for i in range(5)]
            self.Max_Q = [0 for i in range(5)]

            print('online state (',self._step,' th) : ', current_state)
            print('action : ', action)

            reward = -(next_Qsum - current_Qsum)
            score += reward
            scores.append(reward)

            self._Memory.add_sample((current_state, action, reward+self._step*0.01, next_state, self._step), epsilon)
            self.replay()

            current_state = next_state
            current_Qsum = next_Qsum
            self._step += 1

        print(scores)
        self._setting.Vissim.Simulation.Stop()
        simulation_time = round(timeit.default_timer() - start_time, 1)

        start_time = timeit.default_timer()
        training_time = round(timeit.default_timer() - start_time, 1)

        self.save("dqn.h5")
        return simulation_time, training_time, score


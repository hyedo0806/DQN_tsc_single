import pickle
import pandas as pd
import win32com.client as com
import os

BASE = [470, 490, 350, 220, 260]
MIN = [390, 460, 320, 200, 140]
MAX = [700, 750, 550, 350, 400]
PHASE = ['00001100','11000000','00110000','00100010','00000011']

class setting():
    def __init__(self):

        self.Vissim = com.gencache.EnsureDispatch("Vissim.Vissim")

        cwd = os.getcwd()

        Filename = os.path.join(cwd, 'temp.inpx')
        flag_read_additionally = False
        self.Vissim.LoadNet(Filename, flag_read_additionally)

        self.Vissim.Simulation.SetAttValue('SimSpeed', 1)

    def veh_input(self):
        with open('./input data/traffic_data', 'rb') as f:
            df = pickle.load(f)
            # print(df)
            ### *For test: consider only one day (24 hours)
        df = df.iloc[9:33]
        df = df.rename(dict(zip(list(df.index), list(range(1, len(df) + 1)))))
        ###

        # Define mappings

        # CCTV id 2 records traffic from West
        CCTV_DIR = {1: 'S', 2: 'W', 3: 'N', 4: 'E'}

        # direction to routing decision id mapping
        DIR_SVRD = {'N': 4, 'S': 3, 'E': 2, 'W': 1}

        # link id to vehicle input id
        DIR_VI = {'E': 1, 'N': 2, 'W': 3, 'S': 4}

        # link id to vehicle composition id
        DIR_VC = {'N': 1, 'E': 2, 'S': 3, 'W': 4}

        # For direction ordering
        dir_tuple = ('RIGHT_TRF_', 'GO_TRF_', 'LEFT_TRF_')

        for i, record in df.iterrows():
            trf_by_cctv = {num: sum([record[d + str(num)] for d in dir_tuple]) for num in range(1, 5)}
            # print(trf_by_cctv.items())
            for cctv_num, traffic in trf_by_cctv.items():
                dir = CCTV_DIR[cctv_num]
                vi_id = DIR_VI[dir]

                # Set total traffic volume for each time step
                if i > 1:
                    self.Vissim.Net.VehicleInputs.ItemByKey(vi_id).SetAttValue(f'Cont({i})', False)
                self.Vissim.Net.VehicleInputs.ItemByKey(vi_id).SetAttValue(f'Volume({i})', int(traffic))

                # Set Vehicle Routing Decision
                svrd_id = DIR_SVRD[dir]
                cctv_trf = [record[d + str(cctv_num)] for d in dir_tuple]
                total = sum(cctv_trf)
                # 1: right, 2: straight, 3: left
                for svr_id, trf in zip([1, 2, 3], cctv_trf):
                    self.Vissim.Net.VehicleRoutingDecisionsStatic.ItemByKey(svrd_id).VehRoutSta.ItemByKey(
                        svr_id).SetAttValue(
                        f'RelFlow({i})', trf / total)
            # print("Vehicle Input Done")

        # Set Vehicle Composition for each direction
        with open('./input data/vc_data', 'rb') as f:
            df2 = pickle.load(f)
        print(df2)
        vc_type = ['CAR', 'BUS', 'BIKE']
        vc_id = [100, 300, 610]
        vc_speed = [50, 40, 40]

        df2 = df2[vc_type].div(df2.sum(axis=1), axis=0)
        df2 = df2.rename(dict(zip(list(df2.index), list(range(1, len(df2) + 1)))))

        for cctv_num in range(1, 5):
            dir = CCTV_DIR[cctv_num]
            vc_id = DIR_VC[dir]
            Rel_Flows = self.Vissim.Net.VehicleCompositions.ItemByKey(vc_id).VehCompRelFlows.GetAll()
            for i, type in enumerate(vc_type):
                # Rel_Flows[i].SetAttValue('VehType',        vc_id[i]) # Changing the vehicle type -> type subscriptable 오류
                Rel_Flows[i].SetAttValue('DesSpeedDistr', vc_speed[i])  # Changing the desired speed distribution
                Rel_Flows[i].SetAttValue('RelFlow', df2.loc[cctv_num][type])  # Changing the relative flow
        print("Vehicle Composition Done")
        '''
        with open('./input data/data.pickle', 'rb') as f:
            df = pickle.load(f)
        df = df.rename(dict(zip(list(df.index), list(range(1, len(df) + 1)))))


        # CCTV id 2 records traffic from West
        CCTV_DIR = {1: 'S', 2: 'W', 3: 'N', 4: 'E'}

        # direction to routing decision id mapping
        DIR_SVRD = {'N': 4, 'S': 3, 'E': 2, 'W': 1}

        # link id to vehicle input id
        DIR_VI = {'E': 1, 'N': 2, 'W': 3, 'S': 4}

        # link id to vehicle composition id
        DIR_VC = {'N': 1, 'E': 2, 'S': 3, 'W': 4}

        # For direction ordering
        dir_tuple = ('RIGHT_TRF_', 'GO_TRF_', 'LEFT_TRF_')

        for i, record in df.iterrows():

            trf_by_cctv = {num: sum([int(record[d + str(num)]) for d in dir_tuple])
                           for num in range(1, 5)}

            for cctv_num, traffic in trf_by_cctv.items():
                dir = CCTV_DIR[cctv_num]
                vi_id = DIR_VI[dir]

                # Set total traffic volume for each time step
                if i > 1:
                    self.Vissim.Net.VehicleInputs.ItemByKey(vi_id).SetAttValue(f'Cont({i})', False)
                self.Vissim.Net.VehicleInputs.ItemByKey(vi_id).SetAttValue(f'Volume({i})', int(traffic))

                # Set Vehicle Routing Decision
                svrd_id = DIR_SVRD[dir]
                cctv_trf = [int(record[d + str(cctv_num)]) for d in dir_tuple]
                total = sum(cctv_trf)
                # 1: right, 2: straight, 3: left
                for svr_id, trf in zip([1, 2, 3], cctv_trf):
                    self.Vissim.Net.VehicleRoutingDecisionsStatic.ItemByKey(svrd_id).VehRoutSta.ItemByKey(svr_id).SetAttValue(
                        f'RelFlow({i})', trf / total)


        # Set Vehicle Composition for each direction
        with open('./input data/weight.pickle', 'rb') as f:
            df2 = pickle.load(f)
        #print(df2)
        vc_type = ['CAR', 'BUS', 'BIKE']
        vc_id = [100, 300, 610]
        vc_speed = [50, 40, 40]

        df2 = df2.rename(dict(zip(list(df2.index), list(range(1, len(df2) + 1)))))

        for cctv_num in range(1, 5):
            dir = CCTV_DIR[cctv_num]
            vc_id = DIR_VC[dir]
            Rel_Flows = self.Vissim.Net.VehicleCompositions.ItemByKey(vc_id).VehCompRelFlows.GetAll()
            for i, type in enumerate(vc_type):
                # Rel_Flows[i].SetAttValue('VehType',        vc_id[i]) # Changing the vehicle type -> type subscriptable 오류
                Rel_Flows[i].SetAttValue('DesSpeedDistr', vc_speed[i])  # Changing the desired speed distribution
                Rel_Flows[i].SetAttValue('RelFlow', df2.loc[cctv_num][type])  # Changing the relative flow
        '''
    def signal(self):
        self.SC_number = 1  # SC = SignalController
        self.SH = []
        self.SG = []
        ## ====== Signal Controller & Signal Head & Signal Group Setting ======
        # Set a signal controller program:
        self.SignalController = self.Vissim.Net.SignalControllers.ItemByKey(self.SC_number)
        for i in range(16):
            self.SH.append(self.Vissim.Net.SignalHeads.ItemByKey(i + 1).AttValue('SigState'))
        for i in range(8):
            self.SG.append(self.SignalController.SGs.ItemByKey(i + 1))

    def road(self):
        ## 00  01  02  03  04  05  06  07  10  12  14  16
        ## WOS WOL NOS NOL EOS EOL SOS SOL WI  NI  EI  SI
        '''self.lane = {}
        self.num_lane = 0
        for link in self.Vissim.Net.Links:
            #print(link.AttValue('No'))
            self.lane[link.AttValue('No')] = link.AttValue('Name')
            self.num_lane+=1
        '''
        Input = {'9-1': 1, '9-2': 1, '9-3': 2, '9-4': 2, '19-2': 3, '19-3': 3, '10025-2': 3, '10025-3': 3, '20-2': 3, '20-3': 3,
                 '19-4': 4, '19-5': 4, '10024': 4, '10025-4': 4, '20-4': 4, '2-2': 5, '2-3': 5, '1-2': 5, '1-3': 5,
                 '2-4': 6, '2-5': 6, '1-4': 6, '1-5': 6, '13-2': 7, '13-3': 7, '13-4': 7, '10013-2': 7,'10013-3': 7, '10013-4': 7,
                 '13-5': 8, '10030': 8}
        find = [9,19,20,2,1,13,10025,10024,10013,10030]

        self.lane = {'1' : [], '2':[],'3':[],'4':[],'5':[],'6':[],'7':[],'8':[]}

        for link in self.Vissim.Net.Links:
            if int(link.AttValue('No')) in find:
                for lane in link.Lanes.GetAll():
                    temp = str(link.AttValue('No')) + '-' + str(lane.AttValue('Index'))
                    if temp in Input : self.lane[str(Input[temp])].append(lane)

        Detector = self.Vissim.Net.Detectors.GetAll()
        print (Detector)
        self.detector = {'1' : [], '2':[],'3':[],'4':[],'5':[],'6':[],'7':[],'8':[]}
        for item in Detector:
            self.detector[item.AttValue('Name')].append(item)

        #print(self.detector)

        #print(self.lane)


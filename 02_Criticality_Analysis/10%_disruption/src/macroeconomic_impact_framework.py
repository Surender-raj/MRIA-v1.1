"""
Importing required packages and function files

"""


from input_loader import inputs_for_analysis, mria_inputs
from run_mria import mria_run
from pyomo.environ import value
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os



"""
Step 1: Inputs for the analysis

"""

# Input path 
# The path were all the input files are stored. The SUT tables are placed inside a sub-folder input_path/MRIO
input_path = os.path.join(os.path.dirname(os.getcwd()), 'data')


# Loading the inputs
nl_nuts= inputs_for_analysis(input_path)

# Loading the inputs of the MRIA model
# The variable DATA prepares the Supply and Use Table in a form that can be used directly within MRIA model

DATA, regions = mria_inputs(input_path)


# Parameters of MRIA models

# a switch parameter to allow imports (1 == allow, 0 == no disaster imports)
all_disimp = 1

# Parameter  to determine the steepness of distance function
beta = 0

# Collecting regions and sectors
regions = DATA.countries
sectors = DATA.sectors

regions.sort()
sectors.sort()

"""
Step 2: Loading the sectors to disrupt in a dictionary 

"""

dis_mat = pd.read_excel('Disruption_matrix.xlsx', index_col= [0])

dismat_dict = { 
    (region, sector): value 
    for sector, row in dis_mat.iterrows() 
    for region, value in row.items() 
    if value ==  1
}


"""

Step 3: Creating a distance dictionary to limit disatser imports
Here, it is a redundant since we donot take into the effecte of geographical distance
The parameter beta value is set to zero

"""


def create_distance_dict(nl_nuts, beta):
    nl_nuts_crs = nl_nuts.to_crs(epsg = 3857)
    nl_nuts_crs['centroid'] = nl_nuts_crs.centroid

    distance_dict = {}

    for i in range(len(regions)):
        for j in range(len(regions)):

            r1 = regions[i]
            r2 = regions[j]
            pair = (r1,r2)

            df1 = nl_nuts_crs[nl_nuts_crs['NUTS_ID'] == r1]
            df2 = nl_nuts_crs[nl_nuts_crs['NUTS_ID'] == r2]

            # Centroid
            centroid1 = df1['geometry'].centroid.iloc[0]  
            centroid2 = df2['geometry'].centroid.iloc[0]  

            # Distance in 100s of km
            distance_km = centroid1.distance(centroid2) / 100000
            inv_distance = 1/((distance_km+0.01)**beta)
            distance_dict[pair] = min(1,inv_distance)

    return distance_dict

distance_dict = create_distance_dict(nl_nuts, beta)

"""

Step 4: Disruption dictionary and model parameters

"""

dis_array = [0.1]

solvers = ['mosek']
results = []


for dis in range(len(dis_array)):
    for op in range(len(regions)):
        for ip in range(len(sectors)):

            dis_value = dis_array[dis]

            # op_factor
            op_factor = 1.025

            #Imp flex
            imp_flex = 1

            # Region and sector
            r = regions[op]
            s = sectors[ip]


            # Solver to use  (between mosek ; gams/conopt ;  and cplex)
            solvername = solvers[0]

            disr_dict_sup = {(r, s): 1- dis_value}
            disr_dict_dem = {}

            MRIA_RUN1, MRIA_RUN2 = mria_run(DATA, op_factor, all_disimp, imp_flex, disr_dict_sup, disr_dict_dem, distance_dict, solvername)


            def mria_todf(data):
                df = pd.DataFrame(list(data.items()), columns=['index', 'value'])
                df[['Index1', 'Index2']] = pd.DataFrame(df['index'].tolist(), index=df.index)
                df = df.drop(columns=['index'])
                df = df.set_index(['Index1', 'Index2'])
                return df


            def mria_todf1(data):
                df = pd.DataFrame(list(data.items()), columns=['index', 'value'])
                df[['Index1', 'Index2', 'Index3']] = pd.DataFrame(df['index'].tolist(), index=df.index)
                df = df.drop(columns=['index'])
                df = df.set_index(['Index1', 'Index2', 'Index3'])
                return df


            # Rationing

            Ddis = mria_todf(MRIA_RUN2.Ddis.get_values())
            Rat = Ddis.unstack(level = 0)
            Rat.to_excel(os.path.join('results', f'Rat_{r}_{s}_{dis_value}_{solvername}.xlsx'))

            results.append([dis_value, r, s, MRIA_RUN2.termination_condition, MRIA_RUN2.obj_value])

df = pd.DataFrame(results,  columns=['dis', 'R', 'S','termination', 'Objective'])
df.to_excel(f'results_compilation_{solvername}.xlsx')


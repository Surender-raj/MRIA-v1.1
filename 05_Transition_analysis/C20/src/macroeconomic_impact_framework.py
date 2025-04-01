"""
Importing required packages and function files

"""


from input_loader import inputs_for_analysis, mria_inputs
from run_mria import mria_run
from pyomo.environ import value
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

dis_array = [0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
op_array = [1 1.025]
ip_array =  [0, 1]



solvers = ['mosek']
results = []


for dis in range(len(dis_array)):
    for op in range(len(op_array)):
        
        dis_value = dis_array[dis]
        op_factor = op_array[op]
        imp_flex = ip_array[op]

        # Solver to use  (between mosek ; gams/conopt ;  and cplex)
        solvername = solvers[0]

        
        disr_dict_sup = {key: value - dis_value for key, value in dismat_dict.items()}
        disr_dict_dem = {}

        MRIA_RUN1, MRIA_RUN2, MRIA_RUN3, MRIA_RUN4, MRIA_RUN5 = mria_run(DATA, op_factor, all_disimp, imp_flex, disr_dict_sup, disr_dict_dem, distance_dict, solvername)


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


        # All outputs

        Xdis1 = mria_todf(MRIA_RUN1.X.get_values())
        Xdis1 = Xdis1.unstack(level = 0)
        Xdis1.to_excel(os.path.join('results', f'Xdis1_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))


        Xdis2 = mria_todf(MRIA_RUN2.Xdis.get_values())
        Xdis2 = Xdis2.unstack(level = 0)
        Xdis2.to_excel(os.path.join('results', f'Xdis2_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))


        Xdis3 = mria_todf(MRIA_RUN3.Xdis.get_values())
        Xdis3 = Xdis3.unstack(level = 0)
        Xdis3.to_excel(os.path.join('results', f'Xdis3_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))


        Xdis4 = mria_todf(MRIA_RUN4.Xdis.get_values())
        Xdis4 = Xdis4.unstack(level = 0)
        Xdis4.to_excel(os.path.join('results', f'Xdis4_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))


        Xdis5 = mria_todf(MRIA_RUN5.X.get_values())
        Xdis5 = Xdis5.unstack(level = 0)
        Xdis5.to_excel(os.path.join('results', f'Xdis5_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))


        # Rationing

        Ddis = mria_todf(MRIA_RUN3.Ddis.get_values())
        Rat = Ddis.unstack(level = 0)
        Rat.to_excel(os.path.join('results', f'Rat_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))


        # Disaster imports

        Dimp2 = mria_todf1(MRIA_RUN2.disimp.get_values())
        Dimp2.to_excel(os.path.join('results', f'Dimp2_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))

        Dimp3 = mria_todf1(MRIA_RUN3.disimp.get_values())
        Dimp3.to_excel(os.path.join('results', f'Dimp3_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))

        Dimp4 = mria_todf1(MRIA_RUN4.disimp.get_values())
        Dimp4.to_excel(os.path.join('results', f'Dimp4_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))

        # Xbase
        Xbase_ini = {(i, j): value(MRIA_RUN3.Xbase[i, j]) for i in MRIA_RUN1.m.r for j in MRIA_RUN1.m.S}
        Xbase = mria_todf(Xbase_ini)
        Xbase = Xbase.unstack(level = 0)
        Xbase.to_excel(os.path.join('results', f'Xbase_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))

        # Value Added inital

        VA_ini = {(i, j): value(DATA.ValueA[i, j, 'Imports']) for i in MRIA_RUN3.m.r for j in MRIA_RUN1.m.S}
        VA_df = mria_todf(VA_ini)
        VA_df = VA_df.unstack(level = 0)
        VA_df.to_excel(os.path.join('results', f'VA_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))


        # # Inefficiency calc

        def ineff_calculator(MRIA_RUN):

            supply_values_wimp = {(i, j): value(MRIA_RUN.product_supply[i, j]) for i in MRIA_RUN.m.r for j in MRIA_RUN.m.P}
            sup_wimp = mria_todf(supply_values_wimp)

            # Product demand
            dem_values_wimp = {(i, j): value(MRIA_RUN.product_demand[i, j]) for i in MRIA_RUN.m.r for j in MRIA_RUN1.m.P}
            dem_wimp = mria_todf(dem_values_wimp)
            
            inefficiency = sup_wimp - dem_wimp
            inefficiency = inefficiency.unstack(level = 0)
            return inefficiency

        ineff2 = ineff_calculator(MRIA_RUN2)
        ineff2.to_excel(os.path.join('results', f'ineff2_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))

        ineff3 = ineff_calculator(MRIA_RUN3)
        ineff3.to_excel(os.path.join('results', f'ineff3_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))

        ineff4 = ineff_calculator(MRIA_RUN4)
        ineff4.to_excel(os.path.join('results', f'ineff4_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))

        ineff5 = ineff_calculator(MRIA_RUN5)
        ineff5.to_excel(os.path.join('results', f'ineff5_{op_factor}_{imp_flex}_{dis_value}_{solvername}.xlsx'))

        results.append([dis_value, op_factor, imp_flex, MRIA_RUN3.num_thres, MRIA_RUN3.termination_condition, MRIA_RUN3.obj_value])

df = pd.DataFrame(results,  columns=['dis', 'op', 'ip', 'num_thres','termination', 'Objective'])
df.to_excel(f'results_compilation_{solvername}.xlsx')


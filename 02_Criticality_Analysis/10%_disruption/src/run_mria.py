# Importing packages and function files

from mria_new_SUT_base import MRIA_SUT as MRIAnew
from mria_new_SUT_min_ration import MRIA_SUT as MRIAration


def mria_run(DATA, op_factor, all_disimp, imp_flex, disr_dict_sup, disr_dict_dem, distance_dict, solvername):


    """ RUN MRIA base model - Objective: To correct minor inaccuracies in the model """
    MRIA_RUN1 = MRIAnew(DATA.name, DATA.countries, DATA.sectors, DATA.products)
    MRIA_RUN1.create_sets()
    MRIA_RUN1.create_alias()
    MRIA_RUN1.baseline_data(DATA)

    MRIA_RUN1.run_basemodel(solvername)
    new_Xbase = MRIA_RUN1.X.get_values()

    num_thres = [10**-30,10**-12, 10**-11, 10**-10, 10**-9, 10**-8 , 10**-7, 10**-6 , 0.0001, 0.001, 0.01 , 0.1, 1]

    solution = 'infeasible'
    itr = 0

    while solution != 'optimal' and itr < len(num_thres):
        
        """ RUN MRIA ration model - Objective: To minimise rationing """
        MRIA_RUN2 = MRIAration(DATA.name, DATA.countries, DATA.sectors, DATA.products)
        MRIA_RUN2.create_sets()
        MRIA_RUN2.create_alias()
        MRIA_RUN2.baseline_data(DATA, new_Xbase)
        MRIA_RUN2.create_disaster_data(disr_dict_sup, disr_dict_dem, op_factor, all_disimp,imp_flex, distance_dict, num_thres[itr])
        MRIA_RUN2.run_impactmodel(solvername)


        solution = MRIA_RUN2.termination_condition
        itr += 1

    
    return MRIA_RUN1, MRIA_RUN2




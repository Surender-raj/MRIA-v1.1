# Importing packages and function files

from mria_new_SUT_base import MRIA_SUT as MRIAnew
from mria_new_SUT_min_ration import MRIA_SUT as MRIAration
from mria_new_SUT_min_X import MRIA_SUT as MRIAminx
from mria_new_SUT_base_ration_inverse import MRIA_SUT as MRIAratdemand


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

        new_rat = MRIA_RUN2.Ddis.get_values()
        new_Xin = MRIA_RUN2.Xdis.get_values()
        new_imp = MRIA_RUN2.disimp.get_values()

        """ RUN MRIA minimise supply model - Objective: To minimise supply (i.e., sum of outputs and imports) """
        MRIA_RUN3 = MRIAminx(DATA.name, DATA.countries, DATA.sectors, DATA.products)
        MRIA_RUN3.create_sets()
        MRIA_RUN3.create_alias()
        MRIA_RUN3.baseline_data(DATA, new_Xbase)
        MRIA_RUN3.create_disaster_data(disr_dict_sup, disr_dict_dem, op_factor, all_disimp, imp_flex, distance_dict, new_rat, new_Xin, new_imp, num_thres[itr])
        MRIA_RUN3.run_impactmodel(solvername)

        solution = MRIA_RUN3.termination_condition
        itr += 1


    # MRIA RUN to determine X to satisfy rationing
    MRIA_RUN5 = MRIAratdemand(DATA.name, DATA.countries, DATA.sectors, DATA.products)
    MRIA_RUN5.create_sets()
    MRIA_RUN5.create_alias()
    MRIA_RUN5.baseline_data(DATA, new_rat)
    MRIA_RUN5.run_basemodel(solvername)
    
    return MRIA_RUN1, MRIA_RUN2, MRIA_RUN3,  MRIA_RUN5




# -*- coding: utf-8 -*-
"""MRIA Model

Purpose
-------

The Multiregional Impact Assessment (MRIA) Model allows for estimating a new post-disaster economic situation in equilibrium, given a set of disruptions.

References
----------

1) Koks, E. E., & Thissen, M. (2016). A multiregional impact assessment model for disaster analysis. Economic Systems Research, 28(4), 429-449.

"""
import os

import numpy as np
import pandas as pd
from pyomo.environ import (ConcreteModel, Constraint, Objective, Param, Set,
                           SetOf, Var, minimize, maximize, Expression)
from pyomo.opt import SolverFactory



class MRIA_SUT(object):
    """
    This is the class object 'MRIA' which is used to set up the modelling framework.
    
    We define the type of model, sets, set up the core variables and specify the
    constraints and objectives for different model setups.
    """
    
    def __init__(self, name, list_countries,list_sectors,list_products):
 
        """
        Creation of a Concrete Model, specify the countries and sectors
        to include.
        """
        self.name = name
        self.m = ConcreteModel()
        self.countries = list_countries
        self.total_countries = len(list_countries)
        self.sectors = list_sectors
        self.products = list_products
    
    def create_sets(self,FD_SET=['FinalD'],VA_SET=['VA']):

        """
        Creation of the various sets. First step in future-proofing by allowing
        for own specification of set inputs
        """
       
        self.m.S = Set(initialize=self.sectors, doc='sectors')
        self.m.P = Set(initialize=self.products, doc='sectors')
        self.m.row = Set(initialize=self.products, doc='products')
        self.m.col = Set(initialize=self.sectors+['FinalD'], doc='sectors and final demand')
        
        self.m.rROW = Set(initialize=self.countries,ordered=True, doc='regions including export')
        self.m.R = Set(initialize=self.countries,ordered=True, doc='regions')

        self.m.fdemand = Set(initialize=FD_SET, doc='Final Demand')

        self.m.VA = Set(initialize=VA_SET, doc='value added')

    def create_alias(self):
        """
        Set aliases
        """
        self.m.Rb   = SetOf(self.m.R)  # an alias of region R
        self.m.r   = SetOf(self.m.R)  # an alias of region R
        self.m.Sb   = SetOf(self.m.S)  # an alias of sector S


    def create_UseAbs(self,REG_USE):

        model = self.m

        def usetable_init(model,R,P,Rb,col):
            return REG_USE[R,P,Rb,col]
        
        model.UseAbs = Param(model.R,model.P,model.Rb,model.col,initialize=usetable_init,doc='Absolute use table')

        self.UseAbs = model.UseAbs

    def create_SupAbs(self,REG_SUP):
        model = self.m

        def suptable_init(model,R,S,Rb,P):
            return REG_SUP[R,S,Rb,P]
        
        model.SupAbs = Param(model.R,model.S,model.Rb,model.P,initialize=suptable_init,doc='Absolute sup table')

        self.SupAbs = model.SupAbs

        '''create Xbase'''
    def create_Xbase(self, xbase_dict):
        model = self.m

        def xbase_init(model, R, S):
                return xbase_dict[R, S]

        model.Xbase = Param(model.R,model.S,initialize=xbase_init)
        self.Xbase = model.Xbase
    

    def create_Sup(self):
        model = self.m
        def sup_init(model,R,S,P):

            if self.Xbase[R,S] == 0:
                return 0
            
            else:
                return sum(self.SupAbs[R,S,Rb,P] for Rb in model.Rb)/self.Xbase[R,S]
         
        model.Sup = Param(model.R,model.S,model.P,initialize=sup_init)
        self.Sup = model.Sup  


    def create_Use(self):
        model = self.m
        def use_init(model,Rb,P,R,S):

            if self.Xbase[R,S] == 0:
                return 0
            
            else:
                return self.UseAbs[Rb,P,R,S]/self.Xbase[R,S]
         
        model.Use = Param(model.Rb,model.P,model.R,model.S,initialize=use_init)
        self.Use = model.Use  


    def create_fd(self,REG_USE):
        
        model = self.m
        
        def findem_init(model,R,P):
            return sum(REG_USE[R,P,Rb,fdemand] for Rb in model.Rb for fdemand in model.fdemand)
        
        model.fd = Param(model.R,model.P,initialize=findem_init)
        
        self.fd = model.fd
    
    def create_ExpImp(self,ExpROW_in):

        model = self.m
        # Specify Export ROW
        def ExpROW_ini(m,R,P):
            return (ExpROW_in[R,P,'Exports'])
        
        model.ExpROW = Param(model.R, model.P, initialize=ExpROW_ini, doc='Exports to the rest of the world')               
 
        self.ExpROW = model.ExpROW

    """
    Set up baseline model
    """
 
    """ Create baseline dataset to use in model """
    def baseline_data(self,Table, xbase_dict):
   
        self.create_UseAbs(Table.Use)
        self.create_SupAbs(Table.Sup)
        self.create_Xbase(xbase_dict)
        self.create_Sup()
        self.create_Use()
        self.create_fd(Table.Use)
        self.create_ExpImp(Table.ExpROW)


    def create_sup_disrupt(self, disr_dict_sup):

        model = self.m

        def shock_init_sup(model, R, S):
            if (R, S) in list(disr_dict_sup.keys()):
                return disr_dict_sup[R, S]
            else:
                return 1
            
        model.sup_disrupt = Param(model.R, model.S, initialize=shock_init_sup,
                            doc='Total Production baseline')
        
        # Supply after disruption
        self.sup_disrupt = model.sup_disrupt
    
    def create_dem_disrupt(self, disr_dict_dem):

        model = self.m

        def shock_init_dem(model, R, P):
            if (R, P) in list(disr_dict_dem.keys()):
                return (1-disr_dict_dem[R, P])
            else:
                return 0
            
        model.dem_disrupt = Param(model.R, model.P, initialize=shock_init_dem,
                            doc='Total Production baseline')
        
        self.dem_disrupt = model.dem_disrupt
    
    def create_X_limits(self, op_factor, disr_dict_sup):

        model = self.m

        def x_init_lim(model, R, S):
            if (R, S) in list(disr_dict_sup.keys()):
                return(self.Xbase[R, S] * self.sup_disrupt[R, S])
            
            else:
                return(self.Xbase[R, S] * self.sup_disrupt[R, S]*op_factor)
            
        model.Xlim = Param(model.R, model.S, initialize= x_init_lim,
                            doc='Total Production baseline')
        
        self.Xlim = model.Xlim
    
    def create_dem_limits(self):

        model = self.m

        def dem_init_lim(model, R, P):
            return((self.fd[R, P] + self.ExpROW[R, P])* self.dem_disrupt[R, P])
            
        model.demlim = Param(model.R, model.P, initialize= dem_init_lim,
                            doc='Total Production baseline')
        
        self.demlim = model.demlim

    def create_Xdis(self):
        """
        Creation of the total production **X** variable.
        
        Parameters
            - *self* - **MRIA_IO** class object

            - Xbase - Total Production **X** parameter from the **MRIA** class object

        """

        model = self.m

        # Keeping it bounded to disaster inputs
        def X_bounds_dis(model, R, S):
            
            return (0.0, (self.Xlim[R,S]))
        
        def x_init_dis(model, R, S):
            return(( self.Xbase[R, S] * self.sup_disrupt[R,S] ))
        
        model.Xdis = Var(model.R, model.S, bounds=X_bounds_dis,
                    initialize=x_init_dis, doc='Total Production')


        self.Xdis = model.Xdis
    
    def create_Ddis(self):
        """
        Creation of the total production **X** variable.
        
        Parameters
            - *self* - **MRIA_IO** class object

            - Xbase - Total Production **X** parameter from the **MRIA** class object

        """

        model = self.m

        # Keeping it bounded to disaster inputs

        def D_bounds_dis(model, R, P):
            
            # the max condition was addeed to prevent lower bound . upper bound error. Some sectors have very low neagtive demand values.
            # some sectors had these values way less than 10^-13. Conopt fixed theses variables and issued warnings. To avoid any potential issues
            # the minimum tolerance in upper limit was set to 10^-12

            return (0, max(0, self.fd[R,P] + self.ExpROW[R,P] - self.demlim[R,P] ))   
        
        model.Ddis = Var(model.R, model.P, bounds=D_bounds_dis,
                      initialize= 0 , doc='Total Production')

        self.Ddis = model.Ddis
        
    def create_disimp_limits(self, all_disimp, imp_flex, distance_dict, num_thres):


        model = self.m

        def dis_imp_lim(model, Rb, R, P):
            # We assume disaster imports can happen only between regions. Disaster imports within same region equals zero

            if R == Rb:
                return 0

            else:

                if imp_flex * sum(self.Use[Rb,P,R,Sb] * self.Xbase[R,Sb] for Sb in model.Sb) *all_disimp * distance_dict[Rb,R] >= num_thres:
                    return imp_flex * sum(self.Use[Rb,P,R,Sb] * self.Xbase[R,Sb] for Sb in model.Sb) *all_disimp * distance_dict[Rb,R]
                
                else:

                    return 0
                    # The multiplication by Use matrix coeff ensure that there is alreay a trade link between the regions
                    # We assume it is not easy to create new trade channels right after the disaster
                    # The disimplim(Rb,R,P) equals the sum of inital use of Rb,P by all the sectors in R. 

            
                #return imp_flex * sum(self.Use[Rb,P,R,Sb] * self.Xbase[R,Sb] for Sb in model.Sb) *all_disimp * distance_dict[Rb,R]
                #return max(10**-4 , imp_flex * sum(self.Use[Rb,P,R,Sb] * self.Xbase[R,Sb] for Sb in model.Sb) *all_disimp * distance_dict[Rb,R])
            
        model.disimplim = Param(model.Rb, model.R, model.P, initialize= dis_imp_lim,
                            doc='Total Production baseline')
        
        self.disimplim = model.disimplim

    def create_dis_imports(self):
        """
        Creation of the total production **X** variable.
        
        Parameters
            - *self* - **MRIA_IO** class object

            - Xbase - Total Production **X** parameter from the **MRIA** class object

        """

        model = self.m

        
        def dis_imp_bounds(model, Rb, R, P):
            # some sectors had these values way less than 10^-13. Conopt fixed theses variables and issued warnings. To avoid any potential issues
            # the minimum tolerance in upper limit was set to 10^-12

            #return (0, max(10**-12, self.disimplim[Rb,R,P]))
            return (0, self.disimplim[Rb,R,P])

        model.disimp = Var(model.Rb, model.R, model.P, initialize = 0, bounds = dis_imp_bounds, doc='Trade')
        self.disimp = model.disimp
    
        

    def create_disaster_data(self, disr_dict_sup, disr_dict_dem, op_factor, all_disimp, imp_flex, distance_dict, num_thres):
        """
        Function to set up all the baseline variables for the MRIA model.
        
        Parameters
            - *self* - **MRIA_IO** class object
            - Table - the **io_basic** class object
            - disr_dict_sup - dictionary containing the reduction in production capacity
            - disr_dict_fd - dictionary containing the disruptions in final demand
    
        Outputs
            - all required parameters and variables for the **MRIA_IO** class and the **MRIA** model

        """

        self.create_sup_disrupt(disr_dict_sup)
        self.create_dem_disrupt(disr_dict_dem)
        self.create_X_limits(op_factor, disr_dict_sup)
        self.create_dem_limits()
        self.create_Xdis()
        self.create_Ddis()
        self.create_disimp_limits(all_disimp, imp_flex, distance_dict, num_thres)
        self.create_dis_imports()

    def run_impactmodel(self, solvername):
        """
        Run the baseline model of the MRIA model. This should return the baseline situation (i.e. no changes between input matrix and output matrix).
        
        Parameters
            - *self* - **MRIA_IO** class object
            - solver - Specify the solver to be used with Pyomo. The Default value is set to **None**. If set to **None**, the ipopt solver will be used

        Outputs
            - returns the output of an optimized **MRIA_IO** class and the **MRIA** model

        """
        model = self.m

        # Supply of a product
        
        def supply_expr(model,R,P):
            return (sum(self.Xdis[R, Sb]* self.Sup[R,Sb,P] for Sb in model.Sb) + sum(self.disimp[Rb,R,P] for Rb in model.Rb))

        model.product_supply = Expression(model.R, model.P, rule=supply_expr)
        self.product_supply = model.product_supply

        # Demand for a product

        def demand_expr(model,R,P):
            return  (sum(self.Use[R, P, Rb, Sb]*self.Xdis[Rb, Sb] for Rb in model.Rb
                        for Sb in model.Sb) + self.fd[R,P] 
                    + self.ExpROW[R, P] 
                    - self.demlim[R,P]
                    - self.Ddis[R,P]
                    + sum(self.disimp[R,Rb,P] for Rb in model.Rb)
                    )
        
        model.product_demand = Expression(model.R, model.P, rule=demand_expr)
        self.product_demand = model.product_demand

        def demSup(model, R, P):
            return (

                    # Supply of a product
                    self.product_supply[R,P]

                    # greater than or equal to

                    >=

                    # Demand for a product
                    self.product_demand[R,P]
            )

        model.demSup = Constraint(model.R, model.P, rule=demSup, doc='Satisfy demand')


        def objective_base(model):
            return sum(self.Ddis[R, P] for R in model.R for P in model.P) 
        
        model.objective = Objective(rule=objective_base, sense=minimize,
                                    doc='Define objective function')

        # Solving with mosek
        if solvername == 'mosek':
            solver = SolverFactory('mosek')
            results = solver.solve(model, tee=True)
            results.write()

        if solvername == 'gams':
            opt = SolverFactory('gams')
            io_options = {'solver': 'conopt', 'add_options':['GAMS_MODEL.OptFile = 1;'] } 
            results = opt.solve(model, keepfiles = True, tee= True,  io_options = io_options, tmpdir = 'C:/Users/sva100/GAMStemp')
            results.write()


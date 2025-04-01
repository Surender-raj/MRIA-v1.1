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
    def create_Xbase(self):
        model = self.m

        def xbase_init(model,R,S):
            return sum(self.SupAbs[Rb,S,R,P] for Rb in model.Rb for P in model.P)
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

    def create_X(self):
        """
        Creation of the total production **X** variable.
        
        Parameters
            - *self* - **MRIA_IO** class object

            - Xbase - Total Production **X** parameter from the **MRIA** class object

        """

        model = self.m

        # Keeping it unbounded
        def X_bounds(model, R, S):
            return (0.0, None) 

        def x_init(model, R, S):
            return(0)

        model.X = Var(model.R, model.S, bounds=X_bounds,
                      initialize=x_init, doc='Total Production')

        self.X = model.X

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

    def create_ratdemand(self, rat_dict):
        model = self.m

        def rat_init(model, R, P):
                return rat_dict[R, P]

        model.ratdem = Param(model.R,model.P,initialize=rat_init)
        self.ratdem = model.ratdem

    """
    Set up baseline model
    """
 
    """ Create baseline dataset to use in model """
    def baseline_data(self,Table, rat_dict):
   
        self.create_UseAbs(Table.Use)
        self.create_SupAbs(Table.Sup)
        self.create_Xbase()
        self.create_Sup()
        self.create_Use()
        self.create_X()
        self.create_fd(Table.Use)
        self.create_ExpImp(Table.ExpROW)
        self.create_ratdemand(rat_dict)
        
    def run_basemodel(self, solvername):
        """
        Run the baseline model of the MRIA model. This should return the baseline situation (i.e. no changes between input matrix and output matrix).
        
        Parameters
            - *self* - **MRIA_IO** class object
            - solver - Specify the solver to be used with Pyomo. The Default value is set to **None**. If set to **None**, the ipopt solver will be used

        Outputs
            - returns the output of an optimized **MRIA_IO** class and the **MRIA** model

        """
        model = self.m

        # Demand for a product
        def demand_expr(model,R,P):
            return  (sum(self.Use[R, P, Rb, Sb]*(self.X[Rb, Sb]) for Rb in model.Rb
                        for Sb in model.Sb) + self.ratdem[R,P]
                    )
        
        model.product_demand = Expression(model.R, model.P, rule=demand_expr)
        self.product_demand = model.product_demand


        # Supply of a product
        
        def supply_expr(model,R,P):
            return (sum(self.X[R, Sb]* self.Sup[R,Sb,P] for Sb in model.Sb))

        model.product_supply = Expression(model.R, model.P, rule=supply_expr)
        self.product_supply = model.product_supply


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

        # def objective_base(model):
        #     return sum((self.Xbase[R,S] - self.X[R,S])**2 for R in model.R for S in model.S)

        def objective_base(model):
            return sum (self.X[R, S] for R in model.R for S in model.S)

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
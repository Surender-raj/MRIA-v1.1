# -*- coding: utf-8 -*-
"""
Create the economic tables required to run the MRIA model.
"""
import numpy as np
import pandas as pd


class sut_basic(object):


    def __init__(self, name,filepath,list_countries):
        
        
        self.name = name
        self.file = filepath
        if list_countries is not None:
            self.countries = list_countries
            self.total_countries = len(list_countries)
        else:
            self.countries = []
            self.total_countries = 0



    def load_all_data(self):
        
        """
        LOAD DATA
        """
        self.Use_data = pd.read_excel(self.file,sheet_name="USE",index_col=[0,1],header=[0,1])
        self.Sup_data  = pd.read_excel(self.file,sheet_name="SUP",index_col=[0,1],header=[0,1])
        self.VA_data = pd.read_excel(self.file,sheet_name="VA",index_col=[0,1],header=[0])
        self.ExpROW_data = pd.read_excel(self.file,sheet_name="ExpROW",index_col=[0,1],header=[0])
        self.ImpROW_data = pd.read_excel(self.file,sheet_name="ImpROW",index_col=[0,1],header=[0])

        """
        Extract indices
        """
        self.countries = list(set(list(self.Use_data.index.get_level_values(0))))
        self.sectors = list(set(list(self.Sup_data.index.get_level_values(1))))
        self.products = list(set(list(self.Use_data.index.get_level_values(1))))
        self.FD_cat = ['FinalD']

    def prep_data(self):

        try: 
            self.FD_data is None
        except:
            self.load_all_data()
   
        """
        Return all the parts of the dataset to the class again
        """
        self.Use = {r + k: v for r, kv in self.Use_data.iterrows() for k,v in kv.to_dict().items()}
        self.Sup = {r + k: v for r, kv in self.Sup_data.iterrows() for k,v in kv.to_dict().items()}
        self.ValueA = {r + (k,): v for r, kv in self.VA_data.iterrows() for k,v in kv.to_dict().items()}
        self.ImpROW = {r + (k,): v for r, kv in self.ImpROW_data.iterrows() for k,v in kv.to_dict().items()}
        self.ExpROW = {r + (k,): v for r, kv in self.ExpROW_data.iterrows() for k,v in kv.to_dict().items()}
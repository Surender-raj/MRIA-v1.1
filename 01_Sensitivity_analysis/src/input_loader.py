"""
This function loads all the required inputs required for the macroeconomic impact analysis

    1. Hazard data: Flood map in .tif format
    2. Damage model: Models relating flood inundation depth with probability of functioning in .xlsx format
    3. Expsoure:
        a. Substations (Critical Infrastructure): in .shp format
        b. Sector specific sectors: agricultural, commercial and industrial sectors segretaed in. shp format
        c. Industrial sites: in .shp format
        d. NUTS2 boundaries: NUTS2 level regional boundaries in .shp format with a specific region for RoE
        e. Sectors list: .xlsx format file to inidcate the sectors and their appropriate damage model

"""

#### Importing required pacakages

from table import sut_basic
import geopandas as gpd
import os
import pandas as pd
import rioxarray as rio

def inputs_for_analysis(input_path):


    # shape file of NUTS2 level admin boundaries for NL
    nl_nuts = gpd.read_file(os.path.join(input_path, 'nl_nuts.shp'))
    return nl_nuts




def mria_inputs(input_path):

    # datapath to the inputs folder
    data_path = input_path

    # file path to SUT tables
    filepath = os.path.join(data_path,'MRIO', 'mria_nl_sut.xlsx')
    mria = pd.read_excel(filepath, sheet_name = 'SUP', header = [0,1], index_col = [0,1])
    regions_ineu = ((mria.index.get_level_values(0)).unique()).tolist()

    # Unique regions in the SUT table
    regions = regions_ineu


    # name of the table
    name = 'nl_sut'

    # Preparing the data in the MRIA model format
    DATA = sut_basic('nl_sut', filepath,regions)
    DATA.prep_data()
    data_source = 'nl_sut'

    return DATA, regions
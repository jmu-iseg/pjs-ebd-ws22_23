# Import Pandas, Numpy and MathPlot
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ------------------------
# Vorbereiten des DataSets
## Import 
pvOutput = pd.read_csv('pv_output_dummyData.csv')
basicConsumption = pd.read_csv('basicCounsumption_dummyData.csv')
managementConsumption = pd.read_csv('managementConsumption_dummyData.csv')
productionConsumption = pd.read_csv('productionConsumption_dummyData.csv')

## Zusammenführen der DataSets
from functools import reduce

frames = [pvOutput, basicConsumption, managementConsumption, productionConsumption]

df_merged = reduce(lambda  left,right: pd.merge(left,right,on=['dateTime'],how='outer'), frames)

df_merged.to_csv('sensor.csv')
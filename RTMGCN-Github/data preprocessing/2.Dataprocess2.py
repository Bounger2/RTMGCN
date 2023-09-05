#Split 5-minute intervals by time
import pandas as pd

filepath='data/xxxxx_train_aftertime.csv'
dataf=pd.read_csv(filepath,header=0,index_col=0)
time0=1406995200
date0='xxxxx'

for i in range(0,288):
    dataf1 = dataf[(dataf['4'] >= time0+300*i) & (dataf['4'] < time0+300*(i+1))]
    filepath='data/'+date0+'/'+str(i)+'-'+str(i+1)+'.csv'
    dataf1.to_csv(filepath)
    print('down',str(i))